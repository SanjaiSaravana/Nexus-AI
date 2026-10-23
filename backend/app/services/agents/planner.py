import re
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentType,
    UserIntent,
    SubTaskItem,
    PlannerOutput
)
from app.services.agents.base import BaseAgent

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type=AgentType.PLANNER,
            name="Planner Agent",
            description="Decomposes user requests into structured, executable multi-agent subtasks.",
            activity_message="Planning..."
        )

    def detect_intent(self, message: str) -> UserIntent:
        m = message.lower().strip()
        # 1. Interview Preparation (highest priority agent flow)
        if any(w in m for w in ["interview", "prepare me", "job interview", "hiring", "interviewer", "screening"]):
            return UserIntent.INTERVIEW_PREP

        # 2. Direct factual questions are research queries (e.g. "What is...", "Where is...", "Find...")
        if re.search(r"^(what|who|where|when|why|how much|how many|is there|are there|does|do|can you find|tell me)\b", m):
            return UserIntent.RESEARCH_QUERY

        # 3. Project Planning (requires planning or roadmap intent)
        if any(w in m for w in [
            "project roadmap", "roadmap", "plan project", "project plan",
            "execution plan", "plan a project", "build a roadmap", "develop a roadmap",
            "system design roadmap", "architecture roadmap"
        ]) or (("project" in m or "architecture" in m) and ("plan" in m or "roadmap" in m or "strategy" in m)):
            return UserIntent.PROJECT_PLANNING

        # 4. Task Generation
        if any(w in m for w in ["create task", "generate task", "todo list", "action item", "checklist"]):
            return UserIntent.TASK_GENERATION

        # 5. General research keywords
        if any(w in m for w in ["find", "search", "document", "pdf", "resume", "extract", "knowledge"]):
            return UserIntent.RESEARCH_QUERY

        return UserIntent.GENERAL_ASSISTANCE

    async def _process(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        message = input_data.get("message", "").strip()
        intent = self.detect_intent(message)

        if intent == UserIntent.INTERVIEW_PREP:
            goal = "Prepare comprehensive interview strategy, technical review, and action plan"
            subtasks = [
                SubTaskItem(
                    step=1,
                    title="Find interview details",
                    description="Extract company, role, scheduled timing, and interview format from user query and calendar context.",
                    assigned_agent=AgentType.CALENDAR
                ),
                SubTaskItem(
                    step=2,
                    title="Find job description",
                    description="Search knowledge vault and uploaded documents for target job description and company details.",
                    assigned_agent=AgentType.RESEARCH
                ),
                SubTaskItem(
                    step=3,
                    title="Extract requirements",
                    description="Extract core technical, behavioral, and architectural competencies required for the position.",
                    assigned_agent=AgentType.RESEARCH
                ),
                SubTaskItem(
                    step=4,
                    title="Analyze user skills",
                    description="Recall verified technical skills, experiences, and past performance from user memory and knowledge graph.",
                    assigned_agent=AgentType.MEMORY
                ),
                SubTaskItem(
                    step=5,
                    title="Find relevant projects",
                    description="Identify the most compelling user projects demonstrating mastery of the required technologies.",
                    assigned_agent=AgentType.PROJECT
                ),
                SubTaskItem(
                    step=6,
                    title="Identify gaps",
                    description="Analyze discrepancies between required competencies and user background to anticipate tough interview questions.",
                    assigned_agent=AgentType.PROJECT
                ),
                SubTaskItem(
                    step=7,
                    title="Generate topics",
                    description="Synthesize high-yield study topics, STAR methodology talking points, and targeted system design concepts.",
                    assigned_agent=AgentType.RESEARCH
                ),
                SubTaskItem(
                    step=8,
                    title="Generate preparation plan",
                    description="Create concrete time-boxed study tasks and interview milestones for rapid preparation.",
                    assigned_agent=AgentType.TASK
                )
            ]
            required_agents = [
                AgentType.CALENDAR,
                AgentType.RESEARCH,
                AgentType.MEMORY,
                AgentType.PROJECT,
                AgentType.TASK,
                AgentType.EXECUTION
            ]
            summary = "Constructed 8-step structured interview readiness plan spanning document research, memory retrieval, project matching, and task generation."

        elif intent == UserIntent.PROJECT_PLANNING:
            goal = f"Formulate end-to-end project execution roadmap for: {message[:60]}"
            subtasks = [
                SubTaskItem(
                    step=1,
                    title="Analyze Project Scope",
                    description="Evaluate project technical specifications and requirements against user capabilities.",
                    assigned_agent=AgentType.PROJECT
                ),
                SubTaskItem(
                    step=2,
                    title="Retrieve Relevant Knowledge",
                    description="Search documentation and graph for architectural precedents and existing libraries.",
                    assigned_agent=AgentType.RESEARCH
                ),
                SubTaskItem(
                    step=3,
                    title="Recall User Preferences",
                    description="Retrieve user conventions, language choices, and development preferences from memory.",
                    assigned_agent=AgentType.MEMORY
                ),
                SubTaskItem(
                    step=4,
                    title="Construct Actionable Tasks",
                    description="Decompose project phases into actionable work units with milestones and deadlines.",
                    assigned_agent=AgentType.TASK
                )
            ]
            required_agents = [AgentType.PROJECT, AgentType.RESEARCH, AgentType.MEMORY, AgentType.TASK]
            summary = "Constructed project decomposition and task breakdown plan."

        elif intent == UserIntent.TASK_GENERATION:
            goal = "Convert user objectives into scheduled actionable tasks"
            subtasks = [
                SubTaskItem(
                    step=1,
                    title="Evaluate Current Workload",
                    description="Analyze active user projects and existing tasks to prevent scheduling conflicts.",
                    assigned_agent=AgentType.PROJECT
                ),
                SubTaskItem(
                    step=2,
                    title="Generate Task Items",
                    description="Generate prioritized task specifications with titles, descriptions, and categories.",
                    assigned_agent=AgentType.TASK
                ),
                SubTaskItem(
                    step=3,
                    title="Execute Task Persistence",
                    description="Persist newly formulated tasks to the database.",
                    assigned_agent=AgentType.EXECUTION
                )
            ]
            required_agents = [AgentType.PROJECT, AgentType.TASK, AgentType.EXECUTION]
            summary = "Formulated task generation and persistence plan."

        elif intent == UserIntent.RESEARCH_QUERY:
            goal = "Execute cross-modal research across documents, graph, and memories"
            subtasks = [
                SubTaskItem(
                    step=1,
                    title="Semantic Document & Graph Search",
                    description="Query RAG vector index and Neo4j knowledge graph for relevant factual citations.",
                    assigned_agent=AgentType.RESEARCH
                ),
                SubTaskItem(
                    step=2,
                    title="Recall Personal Context",
                    description="Retrieve user-specific memories and preferences related to the research query.",
                    assigned_agent=AgentType.MEMORY
                )
            ]
            required_agents = [AgentType.RESEARCH, AgentType.MEMORY]
            summary = "Formulated multi-source research retrieval plan."

        else:
            goal = "Assist user with general query using contextual reasoning"
            subtasks = [
                SubTaskItem(
                    step=1,
                    title="Gather Context",
                    description="Check memories and knowledge sources for relevant background information.",
                    assigned_agent=AgentType.RESEARCH
                ),
                SubTaskItem(
                    step=2,
                    title="Check User Memory",
                    description="Retrieve user profile and memory nuances.",
                    assigned_agent=AgentType.MEMORY
                )
            ]
            required_agents = [AgentType.RESEARCH, AgentType.MEMORY]
            summary = "General assistance decomposition."

        plan = PlannerOutput(
            intent=intent,
            goal=goal,
            summary=summary,
            subtasks=subtasks,
            required_agents=required_agents
        )
        return plan.model_dump()

    async def _fallback(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID,
        error: Exception
    ) -> Optional[Dict[str, Any]]:
        # Fallback safe plan
        subtasks = [
            SubTaskItem(
                step=1,
                title="Retrieve Information",
                description="Search documents and knowledge base for relevant context.",
                assigned_agent=AgentType.RESEARCH
            ),
            SubTaskItem(
                step=2,
                title="Formulate Plan",
                description="Create prioritized steps for user request.",
                assigned_agent=AgentType.TASK
            )
        ]
        fallback_plan = PlannerOutput(
            intent=UserIntent.GENERAL_ASSISTANCE,
            goal="Provide assistance with fallback multi-agent plan",
            summary="Default fallback execution plan.",
            subtasks=subtasks,
            required_agents=[AgentType.RESEARCH, AgentType.TASK]
        )
        return fallback_plan.model_dump()

planner_agent = PlannerAgent()
