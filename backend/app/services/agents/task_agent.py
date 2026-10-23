import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentType,
    UserIntent,
    GeneratedTaskItem,
    TaskPlanOutput
)
from app.services.agents.base import BaseAgent

class TaskAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type=AgentType.TASK,
            name="Task Agent",
            description="Converts multi-agent plans and preparation topics into concrete actionable tasks.",
            activity_message="Creating plan..."
        )

    async def _process(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        plan_dict = context.get("plan", {})
        intent_val = plan_dict.get("intent", UserIntent.INTERVIEW_PREP)
        project_dict = context.get("project", {})
        matched_projs = project_dict.get("matched_projects", [])
        top_project_name = matched_projs[0].get("project_name", "Nexus AI") if matched_projs else "Core Architecture"

        tasks: List[GeneratedTaskItem] = []

        if intent_val == UserIntent.INTERVIEW_PREP or "interview" in str(input_data).lower():
            tasks = [
                GeneratedTaskItem(
                    title="STAR Story Preparation for Top Projects",
                    description=f"Draft concrete STAR narratives highlighting technical trade-offs, architecture decisions, and results for {top_project_name}.",
                    priority="urgent",
                    due_date_offset_days=0,
                    category="interview_prep"
                ),
                GeneratedTaskItem(
                    title="Review System Design & Hybrid RAG Architecture",
                    description="Study distributed caching, vector indexing, graph schema traversals, and anti-hallucination guardrails.",
                    priority="high",
                    due_date_offset_days=0,
                    category="technical_review"
                ),
                GeneratedTaskItem(
                    title="Target Identified Competency Gaps",
                    description="Review concurrency primitives, database partitioning, and telemetry metrics.",
                    priority="high",
                    due_date_offset_days=0,
                    category="gap_study"
                ),
                GeneratedTaskItem(
                    title="Conduct 30-Minute Mock Interview Session",
                    description="Practice delivering concise 2-minute project overviews and answer behavioral leadership questions aloud.",
                    priority="medium",
                    due_date_offset_days=1,
                    category="mock_session"
                ),
                GeneratedTaskItem(
                    title="Prepare High-Signal Questions for Interviewer",
                    description="Formulate 3 strategic questions regarding team engineering culture, technical debt, and 12-month roadmap.",
                    priority="low",
                    due_date_offset_days=1,
                    category="logistics"
                )
            ]
        elif intent_val == UserIntent.PROJECT_PLANNING:
            tasks = [
                GeneratedTaskItem(
                    title="Finalize Architectural Specification",
                    description="Document component diagrams, API schemas, and data flow pipelines.",
                    priority="urgent",
                    due_date_offset_days=1,
                    category="architecture"
                ),
                GeneratedTaskItem(
                    title="Setup Automated Test Suite & CI Harness",
                    description="Implement unit and integration tests covering core workflows and failure fallbacks.",
                    priority="high",
                    due_date_offset_days=2,
                    category="testing"
                ),
                GeneratedTaskItem(
                    title="Implement Core Service Layer",
                    description="Code models, database migrations, and service handlers.",
                    priority="high",
                    due_date_offset_days=4,
                    category="development"
                )
            ]
        else:
            tasks = [
                GeneratedTaskItem(
                    title="Action Item: Initial Review",
                    description="Complete preliminary review of discussion points.",
                    priority="medium",
                    due_date_offset_days=1,
                    category="general"
                ),
                GeneratedTaskItem(
                    title="Action Item: Follow-up Execution",
                    description="Execute action items according to schedule.",
                    priority="low",
                    due_date_offset_days=2,
                    category="general"
                )
            ]

        summary = f"Converted execution plan into {len(tasks)} prioritized task items."
        output = TaskPlanOutput(
            tasks=tasks,
            created_count=len(tasks),
            summary=summary
        )
        return output.model_dump()

    async def _fallback(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID,
        error: Exception
    ) -> Optional[Dict[str, Any]]:
        fallback_tasks = [
            GeneratedTaskItem(
                title="Prepare High-Priority Review Items",
                description="Review core concepts and complete interview preparation.",
                priority="high",
                due_date_offset_days=0,
                category="fallback_task"
            )
        ]
        output = TaskPlanOutput(
            tasks=fallback_tasks,
            created_count=1,
            summary="Constructed 1 fallback task item."
        )
        return output.model_dump()

task_agent = TaskAgent()
