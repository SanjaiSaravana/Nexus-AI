import re
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentType,
    ProjectMatch,
    ProjectAnalysisOutput
)
from app.models.project import Project
from app.models.task import Task
from app.models.goal import Goal
from app.services.agents.base import BaseAgent
from app.services.graph.neo4j_client import neo4j_client

class ProjectAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type=AgentType.PROJECT,
            name="Project Agent",
            description="Analyzes user projects and matches them to skills, job requirements, active goals, and tasks.",
            activity_message="Analyzing projects..."
        )

    async def _process(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        message = input_data.get("message") or context.get("message", "")

        # 1. Fetch User Projects with Tasks
        proj_stmt = (
            select(Project)
            .options(selectinload(Project.tasks))
            .where(Project.user_id == user_id)
        )
        proj_res = await db.execute(proj_stmt)
        user_projects = proj_res.scalars().all()

        # 2. Fetch User Goals
        goal_stmt = select(Goal).where(Goal.user_id == user_id)
        goal_res = await db.execute(goal_stmt)
        user_goals = goal_res.scalars().all()

        # 3. Fetch Graph technologies used by user's projects
        graph_techs_by_project: Dict[str, List[str]] = {}
        try:
            cypher = """
            MATCH (u:User {user_id: $user_id})-[:OWNS]->(p:Project)
            OPTIONAL MATCH (p)-[:USES]->(t:Technology)
            RETURN p.name as project_name, collect(t.name) as technologies
            """
            records = await neo4j_client.execute_query(cypher, {"user_id": str(user_id)})
            for rec in records:
                p_name = rec.get("project_name")
                techs = [t for t in rec.get("technologies", []) if t]
                if p_name:
                    graph_techs_by_project[p_name.lower()] = techs
        except Exception:
            pass

        # 4. Extract required skills/technologies from message & research context
        research_context = context.get("research", {})
        facts = research_context.get("facts", [])
        combined_text = f"{message} " + " ".join([f.get("fact", "") for f in facts])
        
        target_skills = [
            "python", "fastapi", "react", "typescript", "neo4j", "docker", 
            "postgresql", "sqlite", "rag", "knowledge graph", "graphql", 
            "kubernetes", "system design", "distributed systems", "redis", "tailwind"
        ]
        found_target_skills = [s for s in target_skills if re.search(rf"\b{re.escape(s)}\b", combined_text, re.IGNORECASE)]
        if not found_target_skills:
            found_target_skills = ["python", "fastapi", "rag", "knowledge graph"]

        # 5. Evaluate and match projects
        matched_projects: List[ProjectMatch] = []
        user_demonstrated_skills = set()

        for proj in user_projects:
            proj_desc = (proj.description or "").lower()
            proj_name = proj.name.lower()
            graph_techs = graph_techs_by_project.get(proj_name, [])

            # Match skills
            matched_for_proj = []
            for skill in target_skills:
                if (
                    re.search(rf"\b{re.escape(skill)}\b", proj_desc) or 
                    re.search(rf"\b{re.escape(skill)}\b", proj_name) or
                    any(skill.lower() == gt.lower() for gt in graph_techs)
                ):
                    matched_for_proj.append(skill.title())
                    user_demonstrated_skills.add(skill.lower())

            # Associated tasks & goals
            task_titles = [t.title for t in proj.tasks]
            aligned_goals = [g.title for g in user_goals if any(w in g.title.lower() for w in proj_name.split())]

            overlap = len([s for s in matched_for_proj if s.lower() in found_target_skills])
            relevance = min(1.0, 0.4 + (overlap * 0.2))

            notes = []
            if matched_for_proj:
                notes.append(f"Demonstrates {', '.join(matched_for_proj[:4])}.")
            if task_titles:
                notes.append(f"Contains {len(task_titles)} execution tasks ({task_titles[0]}).")
            if aligned_goals:
                notes.append(f"Supports goal '{aligned_goals[0]}'.")

            matched_projects.append(
                ProjectMatch(
                    project_id=str(proj.id),
                    project_name=proj.name,
                    description=proj.description or "Active personal project",
                    matched_skills=matched_for_proj,
                    relevance_score=round(relevance, 2),
                    alignment_notes=" ".join(notes) or "Aligned with software architecture."
                )
            )

        # Sort matched projects by relevance
        matched_projects.sort(key=lambda p: p.relevance_score, reverse=True)

        # If user has no registered projects in DB, provide current workspace project as exemplar
        if not matched_projects:
            matched_projects.append(
                ProjectMatch(
                    project_id="workspace-nexus-ai",
                    project_name="Nexus AI Platform",
                    description="Personal AI Assistant & Multi-Agent Architecture featuring Graph RAG and Long-Term Memory.",
                    matched_skills=["Python", "FastAPI", "Neo4j", "React", "TypeScript", "RAG"],
                    relevance_score=0.98,
                    alignment_notes="High alignment with backend systems, AI architecture, and multi-agent orchestration."
                )
            )
            for s in ["python", "fastapi", "neo4j", "rag"]:
                user_demonstrated_skills.add(s)

        # 6. Identify Gaps
        identified_gaps = []
        for req in found_target_skills:
            if req not in user_demonstrated_skills:
                identified_gaps.append(f"Direct project evidence for '{req.title()}' is limited in existing repositories.")

        if not identified_gaps:
            identified_gaps.append("High coverage across core competencies; review distributed systems trade-offs.")

        # 7. Recommended Focus Areas
        recommended_focus = [
            "Articulate the architectural trade-offs of Hybrid Vector + Graph RAG in Nexus AI.",
            "Explain how tenant isolation and entity deduplication are maintained at scale.",
            "Prepare concrete metrics on query latency and memory retention accuracy."
        ]

        summary = f"Analyzed {len(matched_projects)} projects, identified {len(identified_gaps)} potential competency gap(s), and generated {len(recommended_focus)} focus areas."

        output = ProjectAnalysisOutput(
            matched_projects=matched_projects,
            identified_gaps=identified_gaps,
            recommended_focus=recommended_focus,
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
        output = ProjectAnalysisOutput(
            matched_projects=[
                ProjectMatch(
                    project_id="fallback-proj",
                    project_name="Core Development Portfolio",
                    description="General software engineering and AI projects.",
                    matched_skills=["Python", "FastAPI", "RAG"],
                    relevance_score=0.8,
                    alignment_notes="Fallback portfolio matching."
                )
            ],
            identified_gaps=["Verify deep technical questions on concurrency and scaling."],
            recommended_focus=["Review key architectural decisions in recent software projects."],
            summary="Fallback project analysis completed."
        )
        return output.model_dump()

project_agent = ProjectAgent()
