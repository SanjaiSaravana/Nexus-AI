import uuid
import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.chat import Conversation, ChatMessage
from app.schemas.chat import (
    ChatQueryRequest,
    ChatQueryResponse,
    ConversationResponse,
    ConversationDetailResponse,
    ChatMessageResponse
)
from app.services.rag_service import rag_service
from app.services.memory_service import memory_service
from app.services.graph.graph_service import graph_service
from app.schemas.agent import OrchestrationRequest, UserIntent, AgentType, AgentStatus
from app.services.agents.planner import planner_agent
from app.services.agents.orchestrator import orchestrator

router = APIRouter()

@router.post("/query", response_model=ChatQueryResponse)
async def query_rag(
    request: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute standard RAG question answering pipeline with memory integration and persist chat history."""
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    # 1. Retrieve or Create Conversation
    conversation_id = request.conversation_id
    if conversation_id:
        c_stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        c_res = await db.execute(c_stmt)
        conv = c_res.scalar_one_or_none()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        title_snippet = request.message.strip()[:40]
        conv = Conversation(
            user_id=current_user.id,
            title=title_snippet if len(request.message) <= 40 else f"{title_snippet}..."
        )
        db.add(conv)
        await db.flush()
        conversation_id = conv.id

    # 2. Persist User Message & Extract Memories
    user_msg = ChatMessage(
        conversation_id=conversation_id,
        user_id=current_user.id,
        role="user",
        content=request.message.strip(),
        citations=[]
    )
    db.add(user_msg)
    await db.flush()

    # Extract & consolidate memories from user message
    await memory_service.process_conversation_message(
        db=db,
        user_id=current_user.id,
        message=request.message,
        conversation_id=conversation_id
    )

    # 3. Detect intent and determine if multi-agent orchestration is requested
    detected_intent = planner_agent.detect_intent(request.message)
    if detected_intent == UserIntent.INTERVIEW_PREP:
        from app.services.workflows.interview_prep import interview_prep_workflow
        orch_res = await interview_prep_workflow.execute(
            request=OrchestrationRequest(
                message=request.message,
                conversation_id=conversation_id,
                document_ids=request.document_ids,
                auto_execute_tasks=False
            ),
            user_id=current_user.id,
            db=db
        )
        answer = orch_res.final_response
        final_citations = orch_res.citations
    elif detected_intent in [UserIntent.PROJECT_PLANNING, UserIntent.TASK_GENERATION]:
        orch_res = await orchestrator.orchestrate(
            request=OrchestrationRequest(
                message=request.message,
                conversation_id=conversation_id,
                document_ids=request.document_ids,
                auto_execute_tasks=False
            ),
            user_id=current_user.id,
            db=db
        )
        answer = orch_res.final_response
        final_citations = orch_res.citations
    else:
        # 3. Retrieve Relevant User Memories
        retrieved_mems_with_scores = await memory_service.retrieve_memories(
            db=db,
            user_id=current_user.id,
            query=request.message,
            top_k=3
        )
        relevant_memories = [m for m, _ in retrieved_mems_with_scores]

        # 3.5 Retrieve Relevant Knowledge Graph Subgraph (Hybrid RAG + Graph)
        graph_context = await graph_service.get_rag_context(
            user_id=current_user.id,
            query=request.message
        )

        # 4. RAG Retrieval & Context Construction
        chunks_with_scores = await rag_service.retrieve_chunks(
            db=db,
            user_id=current_user.id,
            query=request.message,
            document_ids=request.document_ids,
            top_k=request.top_k or 5
        )

        context, citations = rag_service.build_context_and_citations(chunks_with_scores, graph_context=graph_context)

        # 5. Generate Answer (using documents, memories, and knowledge graph)
        answer, final_citations = await rag_service.generate_response(
            query=request.message,
            context=context,
            citations=citations,
            memories=relevant_memories,
            graph_context=graph_context
        )

    # 6. Persist Assistant Message
    asst_msg = ChatMessage(
        conversation_id=conversation_id,
        user_id=current_user.id,
        role="assistant",
        content=answer,
        citations=[c.model_dump() for c in final_citations]
    )
    db.add(asst_msg)
    await db.commit()
    await db.refresh(asst_msg)

    return ChatQueryResponse(
        conversation_id=conversation_id,
        message_id=asst_msg.id,
        answer=answer,
        citations=final_citations
    )

@router.post("/stream")
async def stream_rag(
    request: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Server-Sent Events (SSE) streaming endpoint with memory integration."""
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    # Resolve or create conversation
    conversation_id = request.conversation_id
    if conversation_id:
        c_stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        c_res = await db.execute(c_stmt)
        conv = c_res.scalar_one_or_none()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        title_snippet = request.message.strip()[:40]
        conv = Conversation(
            user_id=current_user.id,
            title=title_snippet if len(request.message) <= 40 else f"{title_snippet}..."
        )
        db.add(conv)
        await db.flush()
        conversation_id = conv.id

    # Persist user message & extract memories
    user_msg = ChatMessage(
        conversation_id=conversation_id,
        user_id=current_user.id,
        role="user",
        content=request.message.strip(),
        citations=[]
    )
    db.add(user_msg)

    await memory_service.process_conversation_message(
        db=db,
        user_id=current_user.id,
        message=request.message,
        conversation_id=conversation_id
    )
    await db.commit()

    # Retrieve relevant memories & knowledge graph context
    retrieved_mems_with_scores = await memory_service.retrieve_memories(
        db=db,
        user_id=current_user.id,
        query=request.message,
        top_k=3
    )
    relevant_memories = [m for m, _ in retrieved_mems_with_scores]

    graph_context = await graph_service.get_rag_context(
        user_id=current_user.id,
        query=request.message
    )

    detected_intent = planner_agent.detect_intent(request.message)

    async def event_generator():
        yield f"data: {json.dumps({'type': 'init', 'conversation_id': str(conversation_id)})}\n\n"

        full_content = []
        final_citations = []

        if detected_intent in [UserIntent.INTERVIEW_PREP, UserIntent.PROJECT_PLANNING, UserIntent.TASK_GENERATION]:
            # Multi-agent streaming pipeline
            activity_queue = asyncio.Queue()

            async def on_activity_callback(msg: str, agent_type: AgentType, status: AgentStatus):
                await activity_queue.put({"type": "activity", "agent": agent_type.value, "message": msg})

            async def run_orchestration():
                try:
                    if detected_intent == UserIntent.INTERVIEW_PREP:
                        from app.services.workflows.interview_prep import interview_prep_workflow
                        res = await interview_prep_workflow.execute(
                            request=OrchestrationRequest(
                                message=request.message,
                                conversation_id=conversation_id,
                                document_ids=request.document_ids,
                                auto_execute_tasks=False
                            ),
                            user_id=current_user.id,
                            db=db,
                            on_activity=on_activity_callback
                        )
                    else:
                        res = await orchestrator.orchestrate(
                            request=OrchestrationRequest(
                                message=request.message,
                                conversation_id=conversation_id,
                                document_ids=request.document_ids,
                                auto_execute_tasks=False
                            ),
                            user_id=current_user.id,
                            db=db,
                            on_activity=on_activity_callback
                        )
                    await activity_queue.put({"type": "__orchestration_done__", "result": res})
                except Exception as exc:
                    await activity_queue.put({"type": "__orchestration_error__", "error": str(exc)})

            orch_task = asyncio.create_task(run_orchestration())

            # Drain activities as they arrive
            orch_result = None
            while True:
                item = await activity_queue.get()
                if item["type"] == "__orchestration_done__":
                    orch_result = item["result"]
                    break
                elif item["type"] == "__orchestration_error__":
                    break
                else:
                    yield f"data: {json.dumps(item)}\n\n"

            if orch_result:
                full_text = orch_result.final_response
                # Stream out the synthesized markdown smoothly
                words = full_text.split(" ")
                for i in range(0, len(words), 3):
                    chunk = " ".join(words[i:i+3]) + (" " if i + 3 < len(words) else "")
                    full_content.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.015)

                final_citations = [c.model_dump() for c in orch_result.citations]
                yield f"data: {json.dumps({'type': 'citations', 'citations': final_citations})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            else:
                fallback_msg = "I encountered an issue coordinating the agents. Please try again."
                yield f"data: {json.dumps({'type': 'token', 'content': fallback_msg})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        else:
            # Standard RAG retrieval with high-level activity indicators
            yield f"data: {json.dumps({'type': 'activity', 'agent': 'research', 'message': 'Retrieving information...' })}\n\n"
            yield f"data: {json.dumps({'type': 'activity', 'agent': 'memory', 'message': 'Checking memory...' })}\n\n"

            async for event in rag_service.stream_rag_response(
                db=db,
                user_id=current_user.id,
                query=request.message,
                document_ids=request.document_ids,
                top_k=request.top_k or 5,
                memories=relevant_memories,
                graph_context=graph_context
            ):
                if event["type"] == "token":
                    full_content.append(event["content"])
                    yield f"data: {json.dumps(event)}\n\n"
                elif event["type"] == "citations":
                    final_citations = event["citations"]
                    yield f"data: {json.dumps(event)}\n\n"
                elif event["type"] == "done":
                    yield f"data: {json.dumps(event)}\n\n"

        # Save assistant message to database
        try:
            complete_answer = "".join(full_content)
            asst_msg = ChatMessage(
                conversation_id=conversation_id,
                user_id=current_user.id,
                role="assistant",
                content=complete_answer,
                citations=final_citations
            )
            db.add(asst_msg)
            await db.commit()
        except Exception:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all user conversations with message count."""
    stmt = (
        select(Conversation, func.count(ChatMessage.id).label("message_count"))
        .outerjoin(ChatMessage, Conversation.id == ChatMessage.conversation_id)
        .where(Conversation.user_id == current_user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    convs = []
    for conv, count in rows:
        convs.append(ConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=count
        ))
    return convs

@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation with full message history."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return ConversationDetailResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages),
        messages=conv.messages
    )

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all its messages."""
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    await db.delete(conv)
    await db.commit()
    return None
