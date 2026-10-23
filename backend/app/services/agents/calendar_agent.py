import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentType,
    CalendarEventProposal,
    CalendarAgentOutput
)
from app.services.agents.base import BaseAgent

class CalendarAgent(BaseAgent):
    """Calendar Agent Interface responsible for calendar events, interview schedules, deadlines, and time allocation."""
    def __init__(self):
        super().__init__(
            agent_type=AgentType.CALENDAR,
            name="Calendar Agent",
            description="Interface for calendar events, interview schedules, deadlines, and study block allocation.",
            activity_message="Coordinating schedule..."
        )

    async def _process(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        message = input_data.get("message") or context.get("message", "").lower()

        events: List[CalendarEventProposal] = []

        if "tomorrow" in message or "interview" in message:
            events = [
                CalendarEventProposal(
                    title="Deep-Dive Prep: Architecture & STAR Narratives",
                    description="Focused study block: Review Nexus AI architecture, Neo4j graph traversals, and STAR story details.",
                    start_time_offset_hours=2,
                    duration_minutes=60,
                    event_type="study_block"
                ),
                CalendarEventProposal(
                    title="Self Mock Screening & Behavioral Practice",
                    description="Rehearsal block: Practice answering behavioral and conflict-resolution questions aloud.",
                    start_time_offset_hours=5,
                    duration_minutes=45,
                    event_type="mock_session"
                ),
                CalendarEventProposal(
                    title="Final Warm-Up & High-Yield Concept Review",
                    description="Pre-interview review: Skim system design trade-offs, metrics, and questions for interviewer.",
                    start_time_offset_hours=20,
                    duration_minutes=30,
                    event_type="study_block"
                ),
                CalendarEventProposal(
                    title="Target Technical Interview Session",
                    description="Interview event placeholder: Candidate technical evaluation and architectural Q&A.",
                    start_time_offset_hours=22,
                    duration_minutes=60,
                    event_type="interview"
                )
            ]
            schedule_summary = "Constructed 4-stage time-boxed prep schedule culminating in tomorrow's interview."
        else:
            events = [
                CalendarEventProposal(
                    title="Focused Work Session: Project Milestones",
                    description="Dedicated execution block for active tasks and objectives.",
                    start_time_offset_hours=2,
                    duration_minutes=60,
                    event_type="study_block"
                )
            ]
            schedule_summary = "Proposed 1 focused calendar work session."

        output = CalendarAgentOutput(
            events=events,
            schedule_summary=schedule_summary
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
        output = CalendarAgentOutput(
            events=[
                CalendarEventProposal(
                    title="Preparation Time Block",
                    description="General prep and review time slot.",
                    start_time_offset_hours=2,
                    duration_minutes=45,
                    event_type="study_block"
                )
            ],
            schedule_summary="Fallback calendar block proposed."
        )
        return output.model_dump()

calendar_agent = CalendarAgent()
