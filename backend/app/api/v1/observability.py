"""
Observability & Tracing API Endpoints:
Provides distributed trace waterfall inspection and real-time system metrics.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.deps import get_current_user
from app.models.user import User
from app.observability.tracer import tracer
from app.observability.metrics import system_metrics

router = APIRouter()

@router.get("/traces")
async def list_traces(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Returns list of recent execution traces.
    """
    return tracer.list_traces(limit=limit, status_filter=status)

@router.get("/traces/{trace_id}")
async def get_trace_details(
    trace_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Returns full waterfall span tree for a specific trace:
    User request -> Intent -> Retrieval -> Agent -> Tool -> LLM -> Final response.
    """
    trace_data = tracer.get_trace(trace_id)
    if not trace_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace '{trace_id}' not found."
        )
    return trace_data

@router.post("/traces/demo")
async def trigger_demo_trace(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generates an end-to-end trace:
    User request -> Intent -> Retrieval -> Agent -> Tool -> LLM -> Final response.
    """
    trace = tracer.create_pipeline_trace(
        user_prompt="I have an interview tomorrow. Help me prepare.",
        intent_name="interview_preparation",
        retrieval_query="Google Staff Software Engineer Job Description requirements and resume skills",
        retrieved_count=6,
        agent_name="Multi-Agent Orchestrator",
        tool_name="calendar_tool",
        tool_action="get_free_slots",
        llm_model="gpt-4o",
        final_answer="Created a customized 4-stage interview preparation plan with SQL, System Design, STAR narratives, and Mock Rehearsal.",
        user_id=str(current_user.id)
    )
    return trace.to_dict()

@router.get("/metrics")
async def get_system_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Returns aggregated real-time system metrics:
    - Latency (avg, p50, p95, p99)
    - Token usage (prompt, completion, total)
    - Retrieval latency
    - Tool latency breakdown
    - Errors and error rate
    - Model usage
    - Estimated cost in USD
    """
    return system_metrics.get_summary()
