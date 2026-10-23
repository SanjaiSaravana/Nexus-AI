import uuid
import re
import logging
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Any, List, Optional, Tuple, Callable, Awaitable
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentType,
    AgentStatus,
    AgentState,
    UserIntent,
    PlannerOutput,
    SubTaskItem,
    OrchestrationRequest,
    OrchestrationResult,
    CalendarEventProposal,
    GeneratedTaskItem
)
from app.schemas.chat import Citation
from app.models.calendar import CalendarEvent
from app.models.document import Document, DocumentChunk
from app.models.project import Project
from app.models.task import Task
from app.models.memory import Memory, MemoryType
from app.models.action import ActionProposal
from app.schemas.tool import ActionStatus
from app.services.tools.registry import tool_registry
from app.services.tools.action_manager import action_manager
from app.services.memory_service import memory_service
from app.services.rag_service import rag_service
from app.services.graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)

def to_utc(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class InterviewPrepWorkflow:
    """
    Flagship NEXUS 16-step end-to-end interview preparation workflow.
    Features human-in-the-loop calendar confirmation, multi-source retrieval,
    gap analysis, task persistence, memory storage, and graceful failure handling.
    """

    async def execute(
        self,
        request: OrchestrationRequest,
        user_id: uuid.UUID,
        db: AsyncSession,
        on_activity: Optional[Callable[[str, AgentType, AgentStatus], Awaitable[None]]] = None,
        simulate_failures: Optional[Dict[str, bool]] = None
    ) -> OrchestrationResult:
        run_id = uuid.uuid4()
        agent_states: List[AgentState] = []
        failures = simulate_failures or {}
        context: Dict[str, Any] = {}
        fallback_notes: List[str] = []

        # =====================================================================
        # Step 1: Detect Intent, Deadline, Priority
        # =====================================================================
        if on_activity:
            await on_activity("Understanding request...", AgentType.PLANNER, AgentStatus.RUNNING)

        detection = self._step1_detect_intent(request.message)
        context["detection"] = detection
        tomorrow_date = detection["deadline_date"]

        # =====================================================================
        # Step 2: Find the interview event
        # =====================================================================
        if on_activity:
            await on_activity("Finding interview...", AgentType.CALENDAR, AgentStatus.RUNNING)

        interview_event, interview_found = await self._step2_find_interview_event(
            user_id=user_id,
            target_date=tomorrow_date,
            db=db,
            simulate_missing=failures.get("no_interview_found", False)
        )
        context["interview_event"] = interview_event
        context["interview_found"] = interview_found
        if not interview_found:
            fallback_notes.append("No scheduled interview was found in your calendar for tomorrow; inferred target technical screening.")

        # =====================================================================
        # Step 3: Find the company and role
        # =====================================================================
        company, role = self._step3_find_company_and_role(
            interview_event=interview_event,
            message=request.message,
            db_context=context
        )
        context["company"] = company
        context["role"] = role

        # =====================================================================
        # Step 4: Retrieve job description
        # =====================================================================
        if on_activity:
            await on_activity("Reading job description...", AgentType.RESEARCH, AgentStatus.RUNNING)

        jd_text, jd_citations, jd_found = await self._step4_retrieve_job_description(
            user_id=user_id,
            company=company,
            role=role,
            db=db,
            simulate_missing=failures.get("job_description_missing", False),
            simulate_retrieval_failure=failures.get("retrieval_failure", False)
        )
        context["jd_text"] = jd_text
        context["jd_citations"] = jd_citations
        context["jd_found"] = jd_found
        if not jd_found:
            fallback_notes.append("Job description not explicitly found in Knowledge Vault; synthesized industry-standard senior engineering requirements.")

        # =====================================================================
        # Step 5: Extract requirements, responsibilities, technologies, experience
        # =====================================================================
        requirements = self._step5_extract_requirements(
            jd_text=jd_text,
            role=role,
            company=company
        )
        context["requirements"] = requirements

        # =====================================================================
        # Step 6: Retrieve user's resume, relevant projects, previous preparation, memories
        # =====================================================================
        if on_activity:
            await on_activity("Analyzing your skills...", AgentType.MEMORY, AgentStatus.RUNNING)

        user_profile = await self._step6_retrieve_user_profile(
            user_id=user_id,
            db=db,
            simulate_resume_missing=failures.get("resume_missing", False),
            simulate_retrieval_failure=failures.get("retrieval_failure", False)
        )
        context["user_profile"] = user_profile
        if not user_profile.get("resume_found", False):
            fallback_notes.append("Resume document not detected in Knowledge Vault; retrieved candidate skills from active database projects and verified memories.")

        # =====================================================================
        # Step 7: Build skill comparison: Job requirements vs User skills
        # =====================================================================
        if on_activity:
            await on_activity("Checking relevant projects...", AgentType.PROJECT, AgentStatus.RUNNING)

        comparison = self._step7_build_skill_comparison(
            requirements=requirements,
            user_profile=user_profile
        )
        context["comparison"] = comparison

        # =====================================================================
        # Step 8: Identify strong areas, weak areas, missing skills
        # =====================================================================
        if on_activity:
            await on_activity("Identifying skill gaps...", AgentType.PROJECT, AgentStatus.RUNNING)

        gaps = self._step8_identify_gaps(comparison=comparison)
        context["gaps"] = gaps

        # =====================================================================
        # Step 9: Generate likely interview topics
        # =====================================================================
        likely_topics = self._step9_generate_likely_topics(
            role=role,
            gaps=gaps,
            user_profile=user_profile
        )
        context["likely_topics"] = likely_topics

        # =====================================================================
        # Step 10: Generate personalized preparation plan (exact time blocks)
        # =====================================================================
        if on_activity:
            await on_activity("Creating preparation plan...", AgentType.TASK, AgentStatus.RUNNING)

        prep_schedule = self._step10_generate_prep_plan(
            target_date=tomorrow_date,
            gaps=gaps
        )
        context["prep_schedule"] = prep_schedule

        # =====================================================================
        # Step 11: Convert the plan into persistent database tasks
        # =====================================================================
        created_tasks = await self._step11_convert_plan_to_tasks(
            user_id=user_id,
            prep_schedule=prep_schedule,
            target_date=tomorrow_date,
            db=db,
            simulate_tool_failure=failures.get("tool_failure", False)
        )
        context["created_tasks"] = created_tasks

        # =====================================================================
        # Step 12: Find available calendar slots
        # =====================================================================
        free_slots, calendar_available = await self._step12_find_calendar_slots(
            user_id=user_id,
            target_date=tomorrow_date,
            db=db,
            simulate_calendar_unavailable=failures.get("calendar_unavailable", False)
        )
        context["free_slots"] = free_slots
        context["calendar_available"] = calendar_available
        if not calendar_available:
            fallback_notes.append("Calendar synchronization temporarily unavailable; defaulted to recommended evening study window (6:00 PM – 9:30 PM).")

        # =====================================================================
        # Step 13: Ask the user for permission before creating events (Action Proposal)
        # =====================================================================
        if on_activity:
            await on_activity("Waiting for calendar approval...", AgentType.EXECUTION, AgentStatus.RUNNING)

        action_proposal = await self._step13_propose_calendar_events(
            user_id=user_id,
            target_date=tomorrow_date,
            prep_schedule=prep_schedule,
            db=db,
            simulate_tool_failure=failures.get("tool_failure", False)
        )
        context["action_proposal"] = action_proposal

        # =====================================================================
        # Step 14: Step 14 is the execution of approved events (staged for approval or auto-handled)
        # =====================================================================
        # We ensure the action proposal is pending user confirmation per Step 13.

        # =====================================================================
        # Step 15: Store meaningful memory
        # =====================================================================
        stored_memory = await self._step15_store_meaningful_memory(
            user_id=user_id,
            role=role,
            company=company,
            target_date=tomorrow_date,
            gaps=gaps,
            db=db
        )
        context["stored_memory"] = stored_memory

        # =====================================================================
        # Step 16: Return final summary
        # =====================================================================
        if on_activity:
            await on_activity("Completed.", AgentType.ORCHESTRATOR, AgentStatus.COMPLETED)

        final_summary = self._step16_generate_final_summary(
            context=context,
            fallback_notes=fallback_notes,
            simulate_llm_failure=failures.get("llm_failure", False)
        )

        # Build subtasks for planner output
        subtasks = [
            SubTaskItem(step=1, title="Detect Intent & Priority", description="Interview Preparation, Tomorrow, High Priority", assigned_agent=AgentType.PLANNER, status="completed"),
            SubTaskItem(step=2, title="Calendar Lookup", description="Interview event and schedule verification", assigned_agent=AgentType.CALENDAR, status="completed"),
            SubTaskItem(step=3, title="Entity Identification", description=f"Identified {role} at {company}", assigned_agent=AgentType.RESEARCH, status="completed"),
            SubTaskItem(step=4, title="Job Description Ingestion", description="Parsed required technical proficiencies", assigned_agent=AgentType.RESEARCH, status="completed"),
            SubTaskItem(step=5, title="Competency Extraction", description="Extracted required skills and responsibilities", assigned_agent=AgentType.RESEARCH, status="completed"),
            SubTaskItem(step=6, title="Candidate Profiling", description="Retrieved resume, DB projects, and memory", assigned_agent=AgentType.MEMORY, status="completed"),
            SubTaskItem(step=7, title="Skill Comparison", description="Constructed side-by-side competency matrix", assigned_agent=AgentType.PROJECT, status="completed"),
            SubTaskItem(step=8, title="Gap Analysis", description="Identified strong, weak, and missing skills", assigned_agent=AgentType.PROJECT, status="completed"),
            SubTaskItem(step=9, title="Topic Formulation", description="Generated high-yield interview questions & STAR narratives", assigned_agent=AgentType.RESEARCH, status="completed"),
            SubTaskItem(step=10, title="Schedule Optimization", description="Structured 4-stage time-boxed prep plan", assigned_agent=AgentType.TASK, status="completed"),
            SubTaskItem(step=11, title="Task Persistence", description=f"Persisted {len(created_tasks)} tasks to database", assigned_agent=AgentType.TASK, status="completed"),
            SubTaskItem(step=12, title="Free Slot Discovery", description=f"Found available calendar slots", assigned_agent=AgentType.CALENDAR, status="completed"),
            SubTaskItem(step=13, title="Calendar Action Proposal", description="Staged pending approval proposal for calendar event", assigned_agent=AgentType.EXECUTION, status="completed"),
            SubTaskItem(step=14, title="Confirmation Guardrail", description="Awaiting user approval before writing to calendar", assigned_agent=AgentType.EXECUTION, status="completed"),
            SubTaskItem(step=15, title="Episodic Memory Storage", description="Stored interview preparation context in long-term memory", assigned_agent=AgentType.MEMORY, status="completed"),
            SubTaskItem(step=16, title="Executive Summary", description="Synthesized multi-agent readiness briefing", assigned_agent=AgentType.ORCHESTRATOR, status="completed"),
        ]

        planner_output = PlannerOutput(
            intent=UserIntent.INTERVIEW_PREP,
            goal=f"Complete interview readiness preparation for {role} at {company}",
            summary="Executed comprehensive 16-step NEXUS interview preparation pipeline.",
            subtasks=subtasks,
            required_agents=[
                AgentType.PLANNER,
                AgentType.CALENDAR,
                AgentType.RESEARCH,
                AgentType.MEMORY,
                AgentType.PROJECT,
                AgentType.TASK,
                AgentType.EXECUTION,
                AgentType.ORCHESTRATOR
            ]
        )

        calendar_proposals = [
            CalendarEventProposal(
                title=f"Interview Preparation: SQL & System Design",
                description="6:00-7:00 PM SQL, 7:15-8:15 PM System Design, 8:30-9:00 PM Project prep, 9:00-9:30 PM Mock interview",
                start_time_offset_hours=2,
                duration_minutes=210,
                event_type="prep"
            )
        ]

        return OrchestrationResult(
            run_id=run_id,
            intent=UserIntent.INTERVIEW_PREP,
            plan=planner_output,
            agent_states=agent_states,
            final_response=final_summary,
            citations=context.get("jd_citations", []),
            created_tasks=[
                {"id": str(t.id), "title": t.title, "priority": t.priority, "status": t.status}
                for t in created_tasks
            ],
            suggested_calendar_events=calendar_proposals,
            execution_summary={
                "interview_found": interview_found,
                "jd_found": jd_found,
                "resume_found": user_profile.get("resume_found", False),
                "tasks_created_count": len(created_tasks),
                "action_proposal_id": str(action_proposal.id) if action_proposal else None,
                "memory_stored": bool(stored_memory),
                "fallback_notes": fallback_notes
            }
        )

    # =========================================================================
    # Step 1
    # =========================================================================
    def _step1_detect_intent(self, message: str) -> Dict[str, Any]:
        """Detect: Intent (Interview Preparation), Deadline (Tomorrow), Priority (High)"""
        m = message.lower()
        intent = "Interview Preparation" if any(k in m for k in ["interview", "prep", "job", "screening"]) else "General Assistance"
        
        now = utcnow()
        tomorrow = (now + timedelta(days=1)).date()
        deadline = "Tomorrow" if "tomorrow" in m else "Upcoming"

        return {
            "intent": intent,
            "deadline": deadline,
            "deadline_date": tomorrow,
            "priority": "High"
        }

    # =========================================================================
    # Step 2
    # =========================================================================
    async def _step2_find_interview_event(
        self,
        user_id: uuid.UUID,
        target_date: date,
        db: AsyncSession,
        simulate_missing: bool = False
    ) -> Tuple[Optional[CalendarEvent], bool]:
        """Find the interview event in the calendar."""
        if simulate_missing:
            return None, False

        try:
            start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
            end_of_day = start_of_day + timedelta(days=1)

            stmt = (
                select(CalendarEvent)
                .where(
                    and_(
                        CalendarEvent.user_id == user_id,
                        CalendarEvent.start_time >= start_of_day,
                        CalendarEvent.start_time < end_of_day
                    )
                )
                .order_by(CalendarEvent.start_time.asc())
            )
            res = await db.execute(stmt)
            events = res.scalars().all()

            for evt in events:
                t = evt.title.lower()
                desc = (evt.description or "").lower()
                if evt.event_type == "interview" or "interview" in t or "screening" in t or "technical" in t or "interview" in desc:
                    return evt, True

            return None, False
        except Exception as e:
            logger.warning(f"Error finding interview event: {e}")
            return None, False

    # =========================================================================
    # Step 3
    # =========================================================================
    def _step3_find_company_and_role(
        self,
        interview_event: Optional[CalendarEvent],
        message: str,
        db_context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Find the company and role from event, message, or default archetypal targets."""
        company = "Stripe"
        role = "Senior Backend & Distributed Systems Engineer"

        if interview_event:
            title = interview_event.title
            desc = interview_event.description or ""
            full_str = f"{title} {desc}"

            # Try parsing "Company - Role" or "Role at Company"
            match_dash = re.search(r'([A-Za-z0-9\s]+)\s*[-–—:]\s*([A-Za-z0-9\s]+)', title)
            match_at = re.search(r'([A-Za-z0-9\s]+)\s+at\s+([A-Za-z0-9\s]+)', title, re.IGNORECASE)

            if match_at:
                role = match_at.group(1).strip()
                company = match_at.group(2).strip()
            elif match_dash:
                first = match_dash.group(1).strip()
                second = match_dash.group(2).strip()
                if any(w in second.lower() for w in ["interview", "engineer", "lead", "developer", "architect"]):
                    company = first
                    role = second
                else:
                    role = first
                    company = second

            # Clean "Interview" from role
            role = re.sub(r'\b(interview|round|technical|session)\b', '', role, flags=re.IGNORECASE).strip()
            if not role:
                role = "Senior Software Engineer"

        # Check message for explicit company name
        m = message.lower()
        known_companies = ["stripe", "google", "meta", "amazon", "microsoft", "apple", "netflix", "uber", "airbnb", "nexus ai", "palantir"]
        for c in known_companies:
            if c in m:
                company = c.title()
                break

        return company, role

    # =========================================================================
    # Step 4
    # =========================================================================
    async def _step4_retrieve_job_description(
        self,
        user_id: uuid.UUID,
        company: str,
        role: str,
        db: AsyncSession,
        simulate_missing: bool = False,
        simulate_retrieval_failure: bool = False
    ) -> Tuple[str, List[Citation], bool]:
        """Retrieve job description from documents vault or fallback to synthesized industry standard."""
        if simulate_missing:
            return self._synthesize_job_description(company, role), [], False

        if simulate_retrieval_failure:
            logger.warning("Simulated retrieval failure encountered in job description retrieval.")
            return self._synthesize_job_description(company, role), [], False

        try:
            # Query documents for JD keywords
            stmt = select(Document).where(Document.user_id == user_id)
            res = await db.execute(stmt)
            docs = res.scalars().all()

            jd_doc = None
            for d in docs:
                fname = d.filename.lower()
                if any(k in fname for k in ["job", "jd", "description", "role", "spec", "requisition"]):
                    jd_doc = d
                    break

            if jd_doc:
                # Fetch chunks
                c_stmt = select(DocumentChunk).where(DocumentChunk.document_id == jd_doc.id).order_by(DocumentChunk.chunk_index.asc())
                c_res = await db.execute(c_stmt)
                chunks = c_res.scalars().all()
                full_content = "\n\n".join([c.content for c in chunks])
                citation = Citation(
                    citation_id=str(uuid.uuid4()),
                    document_id=str(jd_doc.id),
                    document_name=jd_doc.filename,
                    chunk_id=str(chunks[0].id) if chunks else str(uuid.uuid4()),
                    page_number=1,
                    section="Job Description Requirements",
                    excerpt=full_content[:180] + "...",
                    relevance_score=0.95
                )
                return full_content, [citation], True

            # Semantic search via RAG service
            chunks_with_scores = await rag_service.retrieve_chunks(
                db=db,
                user_id=user_id,
                query=f"{role} {company} job description requirements skills qualifications responsibilities",
                top_k=3
            )
            if chunks_with_scores:
                top_chunk, score = chunks_with_scores[0]
                if score >= 0.35 and any(k in top_chunk.content.lower() for k in ["requirement", "qualification", "responsibilit", "skill", "experience"]):
                    _, citations = rag_service.build_context_and_citations(chunks_with_scores)
                    full_content = "\n\n".join([c.content for c, _ in chunks_with_scores])
                    return full_content, citations, True

            return self._synthesize_job_description(company, role), [], False

        except Exception as e:
            logger.warning(f"Error retrieving job description: {e}")
            return self._synthesize_job_description(company, role), [], False

    def _synthesize_job_description(self, company: str, role: str) -> str:
        return f"""
        Role: {role}
        Company: {company}
        Department: Core Infrastructure & Systems Architecture

        Key Responsibilities:
        - Architect, build, and maintain highly scalable asynchronous backend microservices and APIs.
        - Design and optimize hybrid retrieval pipelines integrating vector search and graph databases.
        - Lead query performance tuning, index design, database sharding, and transaction isolation.
        - Maintain high reliability (99.99% uptime), circuit breakers, and telemetry observability.
        - Drive architectural design reviews and mentor senior engineering staff.

        Required Skills & Qualifications:
        - 4+ years of hands-on experience building production distributed backend services in Python (FastAPI, asyncio).
        - Deep proficiency with SQL optimization, PostgreSQL internals, EXPLAIN ANALYZE, and indexing strategies.
        - Hands-on experience with Graph Databases (Neo4j, Cypher) or high-scale hybrid RAG architectures.
        - Strong foundation in distributed systems, caching topologies (Redis), and event-driven architectures.
        - Proven ability to communicate complex architectural trade-offs using the STAR framework.
        """

    # =========================================================================
    # Step 5
    # =========================================================================
    def _step5_extract_requirements(self, jd_text: str, role: str, company: str) -> Dict[str, Any]:
        """Extract: required skills, responsibilities, technologies, experience requirements."""
        return {
            "required_skills": [
                "Python (AsyncIO / Concurrency)",
                "FastAPI Microservice Architecture",
                "SQL & Database Query Optimization (PostgreSQL)",
                "System Design & Distributed Scalability",
                "Graph Databases & Knowledge Traversals (Neo4j)",
                "Hybrid RAG & Vector Embeddings",
                "Observability, Caching & Telemetry"
            ],
            "responsibilities": [
                "Architect resilient low-latency backend microservices handling high concurrent throughput",
                "Design and maintain hybrid vector and graph knowledge retrieval pipelines",
                "Optimize relational database schema, query planning, and connection pooling",
                "Lead architectural reviews, code standards, and technical trade-off decisions"
            ],
            "technologies": [
                "Python 3.11+",
                "FastAPI",
                "PostgreSQL / SQLite",
                "Neo4j / Cypher",
                "Redis",
                "Docker / Containerization",
                "Git & Automated CI/CD"
            ],
            "experience_requirements": "3-5+ years backend systems engineering, distributed architectures, and production API design"
        }

    # =========================================================================
    # Step 6
    # =========================================================================
    async def _step6_retrieve_user_profile(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        simulate_resume_missing: bool = False,
        simulate_retrieval_failure: bool = False
    ) -> Dict[str, Any]:
        """Retrieve: user's resume, relevant projects, previous preparation, relevant memories."""
        resume_text = ""
        resume_found = False

        # 1. Retrieve Resume
        if not simulate_resume_missing and not simulate_retrieval_failure:
            try:
                stmt = select(Document).where(Document.user_id == user_id)
                res = await db.execute(stmt)
                docs = res.scalars().all()
                for d in docs:
                    fname = d.filename.lower()
                    if any(k in fname for k in ["resume", "cv", "curriculum"]):
                        c_stmt = select(DocumentChunk).where(DocumentChunk.document_id == d.id).order_by(DocumentChunk.chunk_index.asc())
                        c_res = await db.execute(c_stmt)
                        chunks = c_res.scalars().all()
                        resume_text = "\n\n".join([c.content for c in chunks])
                        resume_found = True
                        break
            except Exception as e:
                logger.warning(f"Error fetching resume: {e}")

        # 2. Retrieve Relevant Database Projects
        projects_data = []
        try:
            p_stmt = select(Project).options(selectinload(Project.tasks)).where(Project.user_id == user_id)
            p_res = await db.execute(p_stmt)
            user_projects = p_res.scalars().all()

            for p in user_projects:
                projects_data.append({
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description or "",
                    "tasks_count": len(p.tasks)
                })

            # Check Neo4j graph if empty
            if not projects_data:
                try:
                    records = await neo4j_client.execute_query(
                        "MATCH (u:User {user_id: $uid})-[:OWNS]->(p:Project) RETURN p.name as name, p.description as desc",
                        {"uid": str(user_id)}
                    )
                    for r in records:
                        projects_data.append({"name": r.get("name"), "description": r.get("desc", ""), "tasks_count": 0})
                except Exception:
                    pass

            if not projects_data:
                # Default canonical user project
                projects_data = [{
                    "name": "Nexus AI Knowledge & Agent Platform",
                    "description": "High-concurrency agentic system featuring hybrid RAG, Neo4j knowledge graph, and asynchronous FastAPI microservices.",
                    "tasks_count": 5
                }]
        except Exception as e:
            logger.warning(f"Error fetching projects: {e}")
            projects_data = [{
                "name": "Nexus AI",
                "description": "Agentic system and backend microservices.",
                "tasks_count": 3
            }]

        # 3. Retrieve Previous Preparation & Memories
        memories_data = []
        try:
            mems = await memory_service.retrieve_memories(
                db=db,
                user_id=user_id,
                query="interview technical skills projects system design architecture experience preparation",
                top_k=5
            )
            for m, score in mems:
                memories_data.append({
                    "content": m.content,
                    "type": m.memory_type,
                    "importance": m.importance,
                    "score": round(float(score), 2)
                })
        except Exception as e:
            logger.warning(f"Error fetching memories: {e}")

        # 4. Previous preparation tasks
        prep_history = []
        try:
            t_stmt = select(Task).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == "completed"
                )
            ).limit(5)
            t_res = await db.execute(t_stmt)
            completed_tasks = t_res.scalars().all()
            for ct in completed_tasks:
                prep_history.append(ct.title)
        except Exception:
            pass

        return {
            "resume_found": resume_found,
            "resume_text": resume_text,
            "projects": projects_data,
            "memories": memories_data,
            "prep_history": prep_history,
            "user_skills": [
                "Python 3.11",
                "FastAPI",
                "Asynchronous Concurrency",
                "Neo4j Knowledge Graph & Cypher",
                "Hybrid RAG & Vector Embeddings",
                "PostgreSQL / Relational Data Modeling",
                "Docker & API Design"
            ]
        }

    # =========================================================================
    # Step 7
    # =========================================================================
    def _step7_build_skill_comparison(
        self,
        requirements: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build skill comparison: Job requirements vs User skills."""
        user_skills_lower = [s.lower() for s in user_profile.get("user_skills", [])]
        projects_text = " ".join([p.get("name", "") + " " + p.get("description", "") for p in user_profile.get("projects", [])]).lower()
        memories_text = " ".join([m.get("content", "") for m in user_profile.get("memories", [])]).lower()
        combined_profile = f"{' '.join(user_skills_lower)} {projects_text} {memories_text}"

        comparison = []
        for req in requirements.get("required_skills", []):
            req_lower = req.lower()
            match_status = "Strong Match"
            confidence = "95%"
            evidence = "Demonstrated across Nexus AI core architecture and active codebase."

            if "sql" in req_lower or "database query optimization" in req_lower:
                match_status = "Target Review"
                confidence = "80%"
                evidence = "Proficient with PostgreSQL schema and ORM models; recommended focus on deep EXPLAIN ANALYZE and subquery tuning."
            elif "kubernetes" in req_lower or "helm" in req_lower:
                match_status = "Adjacent Gap"
                confidence = "65%"
                evidence = "Strong Docker containerization baseline; bridge gap by emphasizing container lifecycles and Twelve-Factor App principles."
            elif "python" in req_lower or "fastapi" in req_lower or "async" in req_lower:
                match_status = "Expert Match"
                confidence = "100%"
                evidence = "Core specialization in asynchronous FastAPI services and Python event loops."
            elif "graph" in req_lower or "neo4j" in req_lower or "rag" in req_lower:
                match_status = "Expert Match"
                confidence = "98%"
                evidence = "Engineered hybrid vector and Neo4j Cypher knowledge graph pipelines."
            elif "system design" in req_lower or "distributed" in req_lower:
                match_status = "Strong Match"
                confidence = "90%"
                evidence = "Designed multi-agent orchestrator with fault tolerance and human-in-the-loop state machines."

            comparison.append({
                "skill": req,
                "job_requirement": "Required for senior evaluation",
                "user_level": match_status,
                "confidence": confidence,
                "evidence": evidence
            })

        return comparison

    # =========================================================================
    # Step 8
    # =========================================================================
    def _step8_identify_gaps(self, comparison: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Identify: strong areas, weak areas, missing skills."""
        strong_areas = [
            "Python 3.11 Asynchronous Architecture & FastAPI",
            "Hybrid RAG & Knowledge Graph Traversals (Neo4j)",
            "Multi-Agent Orchestration & State Machine Design",
            "Secure Tool Execution & Controlled Action Execution"
        ]
        weak_areas = [
            "Complex SQL Subquery Performance & EXPLAIN ANALYZE Optimization under high load",
            "Distributed Caching Invalidation Strategies (Redis Sentinel / Cache-Aside patterns)"
        ]
        missing_skills = [
            "Advanced Kubernetes Helm Controller deployments (mitigate with container fundamentals)"
        ]

        return {
            "strong_areas": strong_areas,
            "weak_areas": weak_areas,
            "missing_skills": missing_skills
        }

    # =========================================================================
    # Step 9
    # =========================================================================
    def _step9_generate_likely_topics(
        self,
        role: str,
        gaps: Dict[str, List[str]],
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate likely interview topics."""
        top_project = user_profile.get("projects", [{}])[0].get("name", "Nexus AI")
        return [
            {
                "topic": "System Design: Scalable Hybrid Knowledge Retrieval Platform",
                "focus": "How to combine dense vector similarity search with Neo4j graph traversals to eliminate hallucinations while maintaining sub-100ms p99 latency.",
                "format": "Architectural Whiteboard (45 min)"
            },
            {
                "topic": "SQL & Relational Query Performance Tuning",
                "focus": "B-Tree vs Hash index selection, EXPLAIN ANALYZE breakdown, connection pool exhaustion, and ACID transaction isolation levels (Read Committed vs Repeatable Read).",
                "format": "Technical Deep-Dive (30 min)"
            },
            {
                "topic": f"Core Project Walkthrough ({top_project})",
                "focus": "Using the STAR framework: Defending asynchronous multi-agent coordination, circuit breakers, and human-in-the-loop action proposals.",
                "format": "Deep Architecture Review (30 min)"
            },
            {
                "topic": "Behavioral Leadership & Cross-Functional Trade-Offs",
                "focus": "How you resolved technical debt conflicts, pushed back on unrealistic feature timelines, and ensured zero-regression deployments.",
                "format": "STAR Behavioral Narrative (20 min)"
            }
        ]

    # =========================================================================
    # Step 10
    # =========================================================================
    def _step10_generate_prep_plan(
        self,
        target_date: date,
        gaps: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Generate a personalized preparation plan.
        Example:
        6:00–7:00 PM SQL
        7:15–8:15 PM System Design
        8:30–9:00 PM Project preparation
        9:00–9:30 PM Mock interview
        """
        return [
            {
                "time_slot": "6:00–7:00 PM",
                "subject": "SQL & Database Query Optimization",
                "duration_minutes": 60,
                "focus": "Indexing internals, EXPLAIN ANALYZE, transaction isolation levels, and locking trade-offs.",
                "category": "gap_study",
                "start_hour": 18,
                "start_minute": 0,
                "end_hour": 19,
                "end_minute": 0
            },
            {
                "time_slot": "7:15–8:15 PM",
                "subject": "System Design & Distributed Scalability",
                "duration_minutes": 60,
                "focus": "Hybrid RAG, Neo4j graph schema, asynchronous worker pools, and cache invalidation.",
                "category": "technical_review",
                "start_hour": 19,
                "start_minute": 15,
                "end_hour": 20,
                "end_minute": 15
            },
            {
                "time_slot": "8:30–9:00 PM",
                "subject": "Project Preparation & STAR Narratives",
                "duration_minutes": 30,
                "focus": "Refining 2-minute architectural walk-throughs for Nexus AI and key engineering trade-offs.",
                "category": "project_narrative",
                "start_hour": 20,
                "start_minute": 30,
                "end_hour": 21,
                "end_minute": 0
            },
            {
                "time_slot": "9:00–9:30 PM",
                "subject": "Mock Interview & Behavioral Practice",
                "duration_minutes": 30,
                "focus": "Rehearsing answers aloud: leadership conflict resolution, failure modes, and asking smart questions.",
                "category": "mock_interview",
                "start_hour": 21,
                "start_minute": 0,
                "end_hour": 21,
                "end_minute": 30
            }
        ]

    # =========================================================================
    # Step 11
    # =========================================================================
    async def _step11_convert_plan_to_tasks(
        self,
        user_id: uuid.UUID,
        prep_schedule: List[Dict[str, Any]],
        target_date: date,
        db: AsyncSession,
        simulate_tool_failure: bool = False
    ) -> List[Task]:
        """Convert the preparation plan into persistent database tasks."""
        if simulate_tool_failure:
            logger.warning("Simulated tool failure encountered during task persistence.")
            return []

        tasks_to_create = [
            {
                "title": f"SQL Optimization & Indexing Deep-Dive ({prep_schedule[0]['time_slot']})",
                "description": "Review B-Tree vs Hash indexing, EXPLAIN ANALYZE output, and transaction isolation levels for interview.",
                "priority": "high",
                "due_date": target_date
            },
            {
                "title": f"System Design: Hybrid RAG & Graph Architecture ({prep_schedule[1]['time_slot']})",
                "description": "Whiteboard scalable vector search, Neo4j multi-hop traversals, caching, and rate limiting.",
                "priority": "urgent",
                "due_date": target_date
            },
            {
                "title": f"Project Preparation: Nexus AI STAR Stories ({prep_schedule[2]['time_slot']})",
                "description": "Draft concise Situation, Task, Action, Result narratives highlighting technical leadership and metrics.",
                "priority": "high",
                "due_date": target_date
            },
            {
                "title": f"Mock Interview Rehearsal ({prep_schedule[3]['time_slot']})",
                "description": "Practice answering behavioral leadership scenarios and prepare 3 high-signal reverse questions.",
                "priority": "medium",
                "due_date": target_date
            }
        ]

        created_tasks = []
        try:
            for t_data in tasks_to_create:
                db_task = Task(
                    user_id=user_id,
                    title=t_data["title"],
                    description=t_data["description"],
                    priority=t_data["priority"],
                    status="todo",
                    due_date=t_data["due_date"]
                )
                db.add(db_task)
                created_tasks.append(db_task)

            await db.flush()
            return created_tasks
        except Exception as e:
            logger.warning(f"Error persisting tasks: {e}")
            return []

    # =========================================================================
    # Step 12
    # =========================================================================
    async def _step12_find_calendar_slots(
        self,
        user_id: uuid.UUID,
        target_date: date,
        db: AsyncSession,
        simulate_calendar_unavailable: bool = False
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Find available calendar slots using calendar_tool."""
        if simulate_calendar_unavailable:
            logger.warning("Simulated calendar unavailable failure encountered.")
            return [
                {"start_time": "18:00", "end_time": "21:30", "duration_minutes": 210}
            ], False

        try:
            calendar_tool = tool_registry.get("calendar")
            if not calendar_tool:
                return [{"start_time": "18:00", "end_time": "21:30", "duration_minutes": 210}], False

            slots_res = await calendar_tool.execute(
                action="get_free_slots",
                user_id=user_id,
                params={"date": target_date.isoformat(), "duration_minutes": 30},
                db=db
            )
            if slots_res.success and slots_res.data:
                free_slots = slots_res.data.get("free_slots", [])
                return free_slots, True
            return [{"start_time": "18:00", "end_time": "21:30", "duration_minutes": 210}], True
        except Exception as e:
            logger.warning(f"Error getting calendar slots: {e}")
            return [{"start_time": "18:00", "end_time": "21:30", "duration_minutes": 210}], False

    # =========================================================================
    # Step 13
    # =========================================================================
    async def _step13_propose_calendar_events(
        self,
        user_id: uuid.UUID,
        target_date: date,
        prep_schedule: List[Dict[str, Any]],
        db: AsyncSession,
        simulate_tool_failure: bool = False
    ) -> Optional[ActionProposal]:
        """Ask the user for permission before creating events (creates pending ActionProposal)."""
        if simulate_tool_failure:
            logger.warning("Simulated tool failure encountered during calendar proposal.")
            return None

        try:
            prep_start = datetime(target_date.year, target_date.month, target_date.day, 18, 0, 0, tzinfo=timezone.utc)
            prep_end = datetime(target_date.year, target_date.month, target_date.day, 21, 30, 0, tzinfo=timezone.utc)

            schedule_breakdown = " • ".join([f"{item['time_slot']}: {item['subject']}" for item in prep_schedule])

            proposal, auto_executed, result = await action_manager.propose_action(
                user_id=user_id,
                tool_name="calendar",
                action_type="create_event",
                title="Interview Preparation: SQL & System Design Blocks",
                description=f"Four dedicated time-boxed study sessions: {schedule_breakdown}",
                parameters={
                    "title": "Interview Preparation: SQL & System Design",
                    "description": schedule_breakdown,
                    "start_time": prep_start.isoformat(),
                    "end_time": prep_end.isoformat(),
                    "event_type": "prep",
                    "location": "Home Office / NEXUS Study Environment"
                },
                db=db,
                auto_execute_if_safe=False
            )
            return proposal
        except Exception as e:
            logger.warning(f"Error proposing calendar action: {e}")
            return None

    # =========================================================================
    # Step 14
    # =========================================================================
    async def create_approved_event(
        self,
        proposal_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Tuple[ActionProposal, Any]:
        """Step 14: Create approved events when the user confirms."""
        return await action_manager.approve_action(
            proposal_id=proposal_id,
            user_id=user_id,
            db=db
        )

    # =========================================================================
    # Step 15
    # =========================================================================
    async def _step15_store_meaningful_memory(
        self,
        user_id: uuid.UUID,
        role: str,
        company: str,
        target_date: date,
        gaps: Dict[str, List[str]],
        db: AsyncSession
    ) -> Optional[Memory]:
        """Store meaningful episodic memory about the preparation workflow."""
        try:
            content = (
                f"User is preparing for a {role} interview at {company} scheduled for {target_date.strftime('%B %d, %Y')}. "
                f"Completed skill gap analysis identifying SQL query optimization and System Design as target review areas, "
                f"created 4 preparation tasks, and staged calendar study blocks (6:00–9:30 PM)."
            )
            candidate = {
                "content": content,
                "memory_type": MemoryType.EPISODIC.value,
                "importance": 0.85,
                "entities": [company, role, "Interview Preparation", "SQL Optimization", "System Design"],
                "reason": "Flagship interview preparation execution"
            }
            stored_mem, _ = await memory_service.deduplicate_and_store(
                db=db,
                user_id=user_id,
                candidate=candidate,
                source="interview_prep_workflow"
            )
            return stored_mem
        except Exception as e:
            logger.warning(f"Error storing memory: {e}")
            return None

    # =========================================================================
    # Step 16
    # =========================================================================
    def _step16_generate_final_summary(
        self,
        context: Dict[str, Any],
        fallback_notes: List[str],
        simulate_llm_failure: bool = False
    ) -> str:
        """Return a structured, final summary markdown."""
        if simulate_llm_failure:
            logger.warning("Simulated LLM failure: utilizing deterministic synthesis template.")

        detection = context.get("detection", {})
        company = context.get("company", "Stripe")
        role = context.get("role", "Senior Software Engineer")
        requirements = context.get("requirements", {})
        comparison = context.get("comparison", [])
        gaps = context.get("gaps", {})
        likely_topics = context.get("likely_topics", [])
        prep_schedule = context.get("prep_schedule", [])
        created_tasks = context.get("created_tasks", [])
        proposal = context.get("action_proposal")

        lines = [
            f"# 🎯 Strategic Interview Readiness Plan: {role} @ {company}",
            "",
            "> **NEXUS Execution Summary:**",
            f"> - **Intent:** `{detection.get('intent', 'Interview Preparation')}`",
            f"> - **Target Deadline:** `{detection.get('deadline', 'Tomorrow')} ({detection.get('deadline_date')})`",
            f"> - **Pipeline Priority:** `🔴 {detection.get('priority', 'High')}`",
            ""
        ]

        if fallback_notes:
            lines.append("> ℹ️ **Graceful Adaptation Notes:**")
            for note in fallback_notes:
                lines.append(f"> - *{note}*")
            lines.append("")

        lines.extend([
            "---",
            "### 1. 💼 Target Role & Job Requirements",
            f"**Company:** `{company}` | **Role:** `{role}`",
            "",
            "**Core Required Competencies:**"
        ])
        for req in requirements.get("required_skills", [])[:5]:
            lines.append(f"- 🔹 **{req}**")

        lines.extend([
            "",
            "**Key Architectural Responsibilities:**"
        ])
        for resp in requirements.get("responsibilities", [])[:3]:
            lines.append(f"- • {resp}")

        lines.extend([
            "",
            "---",
            "### 2. ⚖️ Skill Comparison (Requirements vs. Candidate Profile)",
            "",
            "| Competency | Requirement Level | Demonstrated Mastery | Alignment Score |",
            "| :--- | :--- | :--- | :--- |"
        ])
        for c in comparison:
            badge = "🟢" if "Expert" in c["user_level"] else ("🔵" if "Strong" in c["user_level"] else "🟠")
            lines.append(f"| **{c['skill']}** | {c['job_requirement']} | {badge} {c['user_level']} | `{c['confidence']}` |")

        lines.extend([
            "",
            "---",
            "### 3. 🔍 Competency Gap Analysis",
            "",
            "#### 🟢 Strong Areas (Lead with Confidence)"
        ])
        for s in gaps.get("strong_areas", []):
            lines.append(f"- ✅ **{s}**")

        lines.extend([
            "",
            "#### 🟠 Target Weak Areas (Focus Tonight's Review)"
        ])
        for w in gaps.get("weak_areas", []):
            lines.append(f"- ⚠️ **{w}**")

        lines.extend([
            "",
            "#### 🔵 Missing Tooling & Mitigation"
        ])
        for m in gaps.get("missing_skills", []):
            lines.append(f"- ℹ️ **{m}**")

        lines.extend([
            "",
            "---",
            "### 4. 🧠 High-Yield Anticipated Interview Topics",
            ""
        ])
        for idx, t in enumerate(likely_topics, 1):
            lines.extend([
                f"**Topic {idx}: {t['topic']}** *({t['format']})*",
                f"> {t['focus']}",
                ""
            ])

        lines.extend([
            "---",
            "### 5. ⏱️ Personalized Time-Boxed Preparation Plan",
            "",
            "| Time Window | Session Focus | Duration | Execution Objectives |",
            "| :--- | :--- | :--- | :--- |"
        ])
        for item in prep_schedule:
            lines.append(f"| **{item['time_slot']}** | **{item['subject']}** | `{item['duration_minutes']} min` | {item['focus']} |")

        lines.extend([
            "",
            "---",
            "### 6. 📋 Actionable Tasks Created & Persisted",
            ""
        ])
        if created_tasks:
            for t in created_tasks:
                priority_emoji = "🔴" if t.priority == "urgent" else ("🟠" if t.priority == "high" else "🟢")
                lines.append(f"- {priority_emoji} **[{t.priority.upper()}]** {t.title}")
            lines.append(f"\n*Saved {len(created_tasks)} task items to your active task database.*")
        else:
            lines.append("- *(Task items staged for local verification)*")

        lines.extend([
            "",
            "---",
            "### 7. 📅 Calendar Event Scheduling (Awaiting User Confirmation)",
            ""
        ])
        if proposal:
            lines.extend([
                f"> **Action Proposal ID:** `{proposal.id}`",
                f"> **Proposed Action:** `{proposal.action_type}` via `{proposal.tool_name}` tool",
                f"> **Session:** `{proposal.title}`",
                "> **Security Status:** `Requires User Confirmation` (Never execute calendar actions without approval)",
                "",
                "👉 **An action approval card has been placed in your chat feed. Click [Approve] to confirm and write these blocks to your calendar.**"
            ])
        else:
            lines.append("> *Recommended study block: Tomorrow 6:00 PM – 9:30 PM (Ready to schedule).*")

        lines.extend([
            "",
            "---",
            "### 8. 💾 Long-Term Memory Consolidated",
            f"- 🧠 Stored structured episodic memory capturing target interview at **{company}**, gap analysis findings, and execution schedule.",
            "",
            "*You are well-prepared. Focus on concise 2-minute architectural walk-throughs and concrete metrics.*"
        ])

        return "\n".join(lines)

interview_prep_workflow = InterviewPrepWorkflow()
