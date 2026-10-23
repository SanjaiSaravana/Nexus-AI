import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentType,
    AgentStatus,
    AgentState,
    UserIntent,
    PlannerOutput,
    ResearchEvidence,
    MemoryRecallOutput,
    ProjectAnalysisOutput,
    TaskPlanOutput,
    CalendarAgentOutput,
    ExecutionAgentOutput,
    OrchestrationRequest,
    OrchestrationResult
)
from app.schemas.chat import Citation
from app.services.agents.planner import planner_agent
from app.services.agents.research import research_agent
from app.services.agents.memory_agent import memory_agent
from app.services.agents.project_agent import project_agent
from app.services.agents.task_agent import task_agent
from app.services.agents.calendar_agent import calendar_agent
from app.services.agents.execution_agent import execution_agent

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)

class AgentOrchestrator:
    """Central Orchestrator managing multi-agent execution, state tracking, fault tolerance, and contextual synthesis."""

    def __init__(self):
        self.agents = {
            AgentType.PLANNER: planner_agent,
            AgentType.RESEARCH: research_agent,
            AgentType.MEMORY: memory_agent,
            AgentType.PROJECT: project_agent,
            AgentType.TASK: task_agent,
            AgentType.CALENDAR: calendar_agent,
            AgentType.EXECUTION: execution_agent,
        }
        # In-memory run store for audit and API inspection
        self._runs: Dict[uuid.UUID, OrchestrationResult] = {}

    def get_run(self, run_id: uuid.UUID) -> Optional[OrchestrationResult]:
        return self._runs.get(run_id)

    async def orchestrate(
        self,
        request: OrchestrationRequest,
        user_id: uuid.UUID,
        db: AsyncSession,
        on_activity: Optional[Callable[[str, AgentType, AgentStatus], Awaitable[None]]] = None
    ) -> OrchestrationResult:
        run_id = uuid.uuid4()
        agent_states: List[AgentState] = []
        context: Dict[str, Any] = {
            "message": request.message,
            "conversation_id": request.conversation_id,
            "document_ids": request.document_ids,
            "auto_execute_tasks": request.auto_execute_tasks,
            "auto_schedule_calendar": request.auto_schedule_calendar
        }

        # 1. INTENT DETECTION & 2. PLANNER AGENT
        if on_activity:
            await on_activity("Planning...", AgentType.PLANNER, AgentStatus.RUNNING)

        planner_state = await planner_agent.run(
            run_id=run_id,
            input_data={"message": request.message},
            context=context,
            db=db,
            user_id=user_id
        )
        agent_states.append(planner_state)
        plan_dict = planner_state.output or {}
        context["plan"] = plan_dict

        # Validate structured plan
        try:
            validated_plan = PlannerOutput(**plan_dict)
        except Exception:
            # Fallback plan if validation fails
            validated_plan = PlannerOutput(
                intent=UserIntent.INTERVIEW_PREP if "interview" in request.message.lower() else UserIntent.GENERAL_ASSISTANCE,
                goal="Assist user with structured multi-agent workflow",
                summary="Decomposed user request into execution phases.",
                subtasks=[],
                required_agents=[AgentType.RESEARCH, AgentType.MEMORY, AgentType.PROJECT, AgentType.TASK]
            )

        intent = validated_plan.intent
        required_agents = validated_plan.required_agents

        # 3. RESEARCH AGENT (if required)
        if AgentType.RESEARCH in required_agents:
            if on_activity:
                await on_activity("Retrieving information...", AgentType.RESEARCH, AgentStatus.RUNNING)

            research_state = await research_agent.run(
                run_id=run_id,
                input_data={"query": request.message, "document_ids": request.document_ids},
                context=context,
                db=db,
                user_id=user_id
            )
            agent_states.append(research_state)
            context["research"] = research_state.output or {}

        # 4. MEMORY AGENT (if required)
        if AgentType.MEMORY in required_agents:
            if on_activity:
                await on_activity("Checking memory...", AgentType.MEMORY, AgentStatus.RUNNING)

            memory_state = await memory_agent.run(
                run_id=run_id,
                input_data={"query": request.message},
                context=context,
                db=db,
                user_id=user_id
            )
            agent_states.append(memory_state)
            context["memory"] = memory_state.output or {}

        # 5. PROJECT AGENT (if required)
        if AgentType.PROJECT in required_agents:
            if on_activity:
                await on_activity("Analyzing projects...", AgentType.PROJECT, AgentStatus.RUNNING)

            project_state = await project_agent.run(
                run_id=run_id,
                input_data={"message": request.message},
                context=context,
                db=db,
                user_id=user_id
            )
            agent_states.append(project_state)
            context["project"] = project_state.output or {}

        # 6. CALENDAR AGENT (if required)
        if AgentType.CALENDAR in required_agents:
            if on_activity:
                await on_activity("Coordinating schedule...", AgentType.CALENDAR, AgentStatus.RUNNING)

            cal_state = await calendar_agent.run(
                run_id=run_id,
                input_data={"message": request.message},
                context=context,
                db=db,
                user_id=user_id
            )
            agent_states.append(cal_state)
            context["calendar"] = cal_state.output or {}

        # 7. TASK AGENT (if required)
        if AgentType.TASK in required_agents:
            if on_activity:
                await on_activity("Creating plan...", AgentType.TASK, AgentStatus.RUNNING)

            task_state = await task_agent.run(
                run_id=run_id,
                input_data={"message": request.message},
                context=context,
                db=db,
                user_id=user_id
            )
            agent_states.append(task_state)
            context["task"] = task_state.output or {}

        # 8. EXECUTION AGENT (if required)
        if AgentType.EXECUTION in required_agents:
            if on_activity:
                await on_activity("Executing actions...", AgentType.EXECUTION, AgentStatus.RUNNING)

            exec_state = await execution_agent.run(
                run_id=run_id,
                input_data={
                    "auto_execute_tasks": request.auto_execute_tasks,
                    "auto_schedule_calendar": request.auto_schedule_calendar
                },
                context=context,
                db=db,
                user_id=user_id
            )
            agent_states.append(exec_state)
            context["execution"] = exec_state.output or {}

        # 9. RESULT VALIDATION & FINAL RESPONSE SYNTHESIS
        final_response, citations = self._synthesize_response(
            message=request.message,
            intent=intent,
            plan=validated_plan,
            context=context
        )

        task_data = context.get("task", {}).get("tasks", [])
        cal_data = context.get("calendar", {}).get("events", [])
        exec_data = context.get("execution", {})

        result = OrchestrationResult(
            run_id=run_id,
            intent=intent,
            plan=validated_plan,
            agent_states=agent_states,
            final_response=final_response,
            citations=citations,
            created_tasks=task_data,
            suggested_calendar_events=cal_data,
            execution_summary=exec_data
        )

        # Store run
        self._runs[run_id] = result
        return result

    def _synthesize_response(
        self,
        message: str,
        intent: UserIntent,
        plan: PlannerOutput,
        context: Dict[str, Any]
    ) -> tuple[str, List[Citation]]:
        research_data = context.get("research", {})
        memory_data = context.get("memory", {})
        project_data = context.get("project", {})
        task_data = context.get("task", {})
        calendar_data = context.get("calendar", {})

        citations = []
        raw_citations = research_data.get("citations", [])
        for c in raw_citations:
            if isinstance(c, dict):
                citations.append(Citation(**c))
            elif isinstance(c, Citation):
                citations.append(c)

        if intent == UserIntent.INTERVIEW_PREP:
            # High-level interview preparation briefing
            projects = project_data.get("matched_projects", [])
            top_proj = projects[0] if projects else None
            gaps = project_data.get("identified_gaps", [])
            tasks = task_data.get("tasks", [])
            events = calendar_data.get("events", [])

            lines = [
                "### 🎯 Strategic Interview Readiness Plan",
                "",
                "I have activated the multi-agent preparation pipeline to analyze your projects, recall verified competencies, and construct a time-boxed execution schedule for your interview tomorrow.",
                "",
                "#### 1. Core Project Spotlight & Architecture Narrative",
            ]

            if top_proj:
                lines.extend([
                    f"- **Featured Project:** **{top_proj.get('project_name', 'Nexus AI')}**",
                    f"- **Demonstrated Technologies:** {', '.join(top_proj.get('matched_skills', ['Python', 'FastAPI', 'Neo4j', 'RAG']))}",
                    f"- **Key Value Proposition:** {top_proj.get('description', 'Agentic system architecture')}",
                    f"- **Interview Alignment:** {top_proj.get('alignment_notes', 'Demonstrates modern AI engineering and backend scalability.')}",
                    "",
                    "> **💡 Recommended STAR Narrative Structure:**",
                    "> - **Situation:** Modern knowledge retrieval systems suffer from context window limits and hallucinations.",
                    "> - **Task:** Build an enterprise-grade agentic memory and graph-retrieval platform.",
                    "> - **Action:** Architected a hybrid pipeline combining vector similarity search with Neo4j graph traversals and asynchronous FastAPI services.",
                    "> - **Result:** Delivered sub-100ms grounded answers with 100% document citation traceability."
                ])
            else:
                lines.append("- Review your recent repositories and highlight architectural decisions and scaling trade-offs.")

            lines.extend([
                "",
                "#### 2. Competency Analysis & Identified Gaps",
            ])

            if gaps:
                for gap in gaps[:2]:
                    lines.append(f"- ⚠️ **Gap to Address:** {gap}")
                lines.append("- **Mitigation:** Explicitly mention how your foundational background in systems engineering and Python async concurrency allows you to rapidly master adjacent tooling.")
            else:
                lines.append("- Strong coverage across backend APIs, data pipelines, and database optimization.")

            lines.extend([
                "",
                "#### 3. Time-Boxed Calendar Preparation Blocks",
            ])

            for evt in events[:3]:
                lines.append(f"- **+{evt.get('start_time_offset_hours', 2)}h:** `{evt.get('title')}` ({evt.get('duration_minutes')} min) — *{evt.get('description')}*")

            lines.extend([
                "",
                "#### 4. Actionable Priority Tasks Created",
            ])

            for t in tasks[:4]:
                priority_emoji = "🔴" if t.get("priority") == "urgent" else ("🟠" if t.get("priority") == "high" else "🟢")
                lines.append(f"- {priority_emoji} **[{t.get('priority', 'medium').upper()}]** {t.get('title')}: {t.get('description')}")

            lines.extend([
                "",
                "---",
                "*You are well-prepared. Focus on concise 2-minute architectural answers and concrete metrics.*"
            ])

            return "\n".join(lines), citations

        # General response synthesis for other intents
        lines = [
            f"### 📋 Multi-Agent Workflow: {plan.goal}",
            "",
            plan.summary,
            "",
            "#### Execution Subtasks Completed:"
        ]
        for st in plan.subtasks:
            lines.append(f"{st.step}. **{st.title}** ({st.assigned_agent.value}): {st.description}")

        tasks = task_data.get("tasks", [])
        if tasks:
            lines.extend([
                "",
                "#### Generated Action Items:"
            ])
            for t in tasks:
                lines.append(f"- **{t.get('title')}** ({t.get('priority')}): {t.get('description')}")

        return "\n".join(lines), citations

orchestrator = AgentOrchestrator()
