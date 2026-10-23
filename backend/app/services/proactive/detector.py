import uuid
import re
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.calendar import CalendarEvent
from app.models.document import Document
from app.models.goal import Goal
from app.models.project import Project
from app.services.proactive.priority_engine import priority_engine

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

class ProactiveDetector:
    """
    Detection engine identifying 8 proactive intelligence situations:
    1. preparation_gaps (interview tomorrow + JD exists + no prep task)
    2. upcoming_deadlines
    3. interviews
    4. unfinished_high_priority_tasks
    5. conflicting_events
    6. overdue_tasks
    7. inactive_goals
    8. important_upcoming_events
    """

    async def detect_all(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        reference_date: Optional[date] = None,
        muted_categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        muted = set(muted_categories or [])
        today = reference_date or date.today()
        now_utc = utcnow()

        # Fetch foundational user data once for efficiency
        tasks_stmt = select(Task).where(Task.user_id == user_id)
        tasks_res = await db.execute(tasks_stmt)
        all_tasks = tasks_res.scalars().all()

        goals_stmt = select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
        goals_res = await db.execute(goals_stmt)
        active_goals = goals_res.scalars().all()

        events_stmt = (
            select(CalendarEvent)
            .where(CalendarEvent.user_id == user_id)
            .order_by(CalendarEvent.start_time.asc())
        )
        events_res = await db.execute(events_stmt)
        all_events = events_res.scalars().all()

        docs_stmt = select(Document).where(Document.user_id == user_id)
        docs_res = await db.execute(docs_stmt)
        all_docs = docs_res.scalars().all()

        recommendations: List[Dict[str, Any]] = []

        # 1. PREPARATION GAPS (Flagship scenario: Interview tomorrow + JD exists + no prep task)
        if "preparation_gap" not in muted:
            prep_recs = self._detect_preparation_gaps(
                user_id=user_id,
                events=all_events,
                docs=all_docs,
                tasks=all_tasks,
                goals=active_goals,
                today=today,
                now_utc=now_utc
            )
            recommendations.extend(prep_recs)

        # 2. CONFLICTING EVENTS
        if "conflicting_events" not in muted:
            conflict_recs = self._detect_conflicting_events(
                user_id=user_id,
                events=all_events,
                goals=active_goals,
                now_utc=now_utc
            )
            recommendations.extend(conflict_recs)

        # 3. OVERDUE TASKS
        if "overdue_task" not in muted:
            overdue_recs = self._detect_overdue_tasks(
                user_id=user_id,
                tasks=all_tasks,
                goals=active_goals,
                today=today
            )
            recommendations.extend(overdue_recs)

        # 4. UPCOMING DEADLINES
        if "upcoming_deadline" not in muted:
            deadline_recs = self._detect_upcoming_deadlines(
                user_id=user_id,
                tasks=all_tasks,
                goals=active_goals,
                today=today
            )
            recommendations.extend(deadline_recs)

        # 5. UNFINISHED HIGH PRIORITY TASKS
        if "unfinished_high_priority" not in muted:
            high_pri_recs = self._detect_unfinished_high_priority(
                user_id=user_id,
                tasks=all_tasks,
                goals=active_goals,
                today=today
            )
            recommendations.extend(high_pri_recs)

        # 6. INACTIVE GOALS
        if "inactive_goal" not in muted:
            goal_recs = self._detect_inactive_goals(
                user_id=user_id,
                goals=active_goals,
                tasks=all_tasks,
                today=today
            )
            recommendations.extend(goal_recs)

        # 7. INTERVIEWS
        if "interview" not in muted:
            interview_recs = self._detect_interviews(
                user_id=user_id,
                events=all_events,
                goals=active_goals,
                now_utc=now_utc
            )
            recommendations.extend(interview_recs)

        # 8. IMPORTANT UPCOMING EVENTS
        if "important_event" not in muted:
            event_recs = self._detect_important_upcoming_events(
                user_id=user_id,
                events=all_events,
                goals=active_goals,
                now_utc=now_utc
            )
            recommendations.extend(event_recs)

        # Sort recommendations by priority score descending
        recommendations.sort(key=lambda r: r["priority_score"], reverse=True)
        return recommendations

    # =========================================================================
    # 1. Preparation Gaps
    # =========================================================================
    def _detect_preparation_gaps(
        self,
        user_id: uuid.UUID,
        events: List[CalendarEvent],
        docs: List[Document],
        tasks: List[Task],
        goals: List[Goal],
        today: date,
        now_utc: datetime
    ) -> List[Dict[str, Any]]:
        """
        Detects if calendar has an interview tomorrow, job description exists in documents,
        but no interview preparation task exists.
        """
        recs = []
        tomorrow = today + timedelta(days=1)

        # Find interview scheduled for tomorrow (or within next 48h)
        interview_event = None
        for evt in events:
            evt_start = to_utc(evt.start_time)
            is_tomorrow = evt_start.date() == tomorrow
            is_interview = (
                evt.event_type == "interview" or
                any(k in evt.title.lower() for k in ["interview", "screening", "technical round"]) or
                any(k in (evt.description or "").lower() for k in ["interview", "screening"])
            )
            if is_interview and (is_tomorrow or (now_utc <= evt_start <= now_utc + timedelta(hours=48))):
                interview_event = evt
                break

        if not interview_event:
            return recs

        # Check if job description exists in documents
        jd_doc = None
        for d in docs:
            fname = d.filename.lower()
            if any(k in fname for k in ["job", "jd", "description", "role", "spec", "requisition"]):
                jd_doc = d
                break

        # Check if user already has an interview preparation task
        has_prep_task = False
        for t in tasks:
            if t.status != "completed":
                t_title = t.title.lower()
                t_desc = (t.description or "").lower()
                if any(k in t_title or k in t_desc for k in ["interview prep", "interview preparation", "mock interview", "star story"]):
                    has_prep_task = True
                    break

        if not has_prep_task and jd_doc is not None:
            # Exact specification case!
            score_data = priority_engine.calculate_breakdown(
                task={
                    "title": f"Interview Preparation for {interview_event.title}",
                    "description": "Urgent prep gap: interview tomorrow without scheduled preparation tasks.",
                    "priority": "urgent",
                    "due_date": tomorrow
                },
                active_goals=goals
            )
            priority_score = max(0.95, score_data["normalized_score"])

            related_goal = None
            for g in goals:
                if any(k in g.title.lower() for k in ["career", "job", "interview", "engineer", "hire"]):
                    related_goal = g.title
                    break

            start_str = to_utc(interview_event.start_time).strftime("%b %d at %I:%M %p")

            recs.append({
                "category": "preparation_gap",
                "title": "Interview Tomorrow: Missing Preparation Plan",
                "recommendation": "Your interview is tomorrow and you don't currently have an interview preparation task. I found the job description and relevant projects. Would you like me to create a preparation plan?",
                "reason": f"Detected interview '{interview_event.title}' scheduled for {start_str} with matching job description '{jd_doc.filename}' in your Knowledge Vault, but no active preparation task.",
                "priority_score": priority_score,
                "priority_level": "urgent",
                "related_goal": related_goal or "Career Advancement",
                "related_deadline": f"Tomorrow ({start_str})",
                "action_type": "create_preparation_plan",
                "action_payload": {
                    "message": "I have an interview tomorrow. Help me prepare.",
                    "interview_event_id": str(interview_event.id),
                    "document_id": str(jd_doc.id)
                }
            })

        return recs

    # =========================================================================
    # 2. Conflicting Events
    # =========================================================================
    def _detect_conflicting_events(
        self,
        user_id: uuid.UUID,
        events: List[CalendarEvent],
        goals: List[Goal],
        now_utc: datetime
    ) -> List[Dict[str, Any]]:
        """Detects overlapping calendar events."""
        recs = []
        future_events = [e for e in events if to_utc(e.end_time) >= now_utc]

        for i in range(len(future_events)):
            e1 = future_events[i]
            st1 = to_utc(e1.start_time)
            et1 = to_utc(e1.end_time)

            for j in range(i + 1, len(future_events)):
                e2 = future_events[j]
                st2 = to_utc(e2.start_time)
                et2 = to_utc(e2.end_time)

                # Overlap condition
                if st1 < et2 and et1 > st2:
                    overlap_mins = int((min(et1, et2) - max(st1, st2)).total_seconds() / 60)
                    time_str = st1.strftime("%b %d, %I:%M %p")
                    recs.append({
                        "category": "conflicting_events",
                        "title": f"Calendar Conflict: '{e1.title}' & '{e2.title}'",
                        "recommendation": f"You have overlapping calendar events on {time_str} with {overlap_mins} minutes of conflict. Would you like me to suggest an alternate free slot?",
                        "reason": f"Event '{e1.title}' ({st1.strftime('%I:%M %p')}–{et1.strftime('%I:%M %p')}) overlaps with '{e2.title}' ({st2.strftime('%I:%M %p')}–{et2.strftime('%I:%M %p')}).",
                        "priority_score": 0.88,
                        "priority_level": "urgent",
                        "related_goal": None,
                        "related_deadline": time_str,
                        "action_type": "resolve_calendar_conflict",
                        "action_payload": {
                            "event_1_id": str(e1.id),
                            "event_2_id": str(e2.id)
                        }
                    })
                    break  # report one pair per event

        return recs

    # =========================================================================
    # 3. Overdue Tasks
    # =========================================================================
    def _detect_overdue_tasks(
        self,
        user_id: uuid.UUID,
        tasks: List[Task],
        goals: List[Goal],
        today: date
    ) -> List[Dict[str, Any]]:
        """Detects tasks past their due date that remain uncompleted."""
        recs = []
        overdue_list = [
            t for t in tasks 
            if t.due_date and t.due_date < today and t.status != "completed"
        ]

        # Prioritize top overdue tasks
        for t in overdue_list[:3]:
            score_data = priority_engine.calculate_breakdown(task=t, active_goals=goals, reference_date=today)
            days_late = (today - t.due_date).days
            recs.append({
                "category": "overdue_task",
                "title": f"Overdue Task: {t.title}",
                "recommendation": f"Task '{t.title}' is {days_late} day(s) overdue. Would you like to reschedule it or mark it complete?",
                "reason": f"Due on {t.due_date.strftime('%b %d')}, but status is currently '{t.status}'.",
                "priority_score": max(0.85, score_data["normalized_score"]),
                "priority_level": "urgent" if t.priority in ["urgent", "high"] else "high",
                "related_goal": self._find_related_goal_title(t, goals),
                "related_deadline": t.due_date.isoformat(),
                "action_type": "reschedule_or_complete_task",
                "action_payload": {
                    "task_id": str(t.id),
                    "task_title": t.title
                }
            })

        return recs

    # =========================================================================
    # 4. Upcoming Deadlines
    # =========================================================================
    def _detect_upcoming_deadlines(
        self,
        user_id: uuid.UUID,
        tasks: List[Task],
        goals: List[Goal],
        today: date
    ) -> List[Dict[str, Any]]:
        """Detects high-impact tasks due within 48-72 hours."""
        recs = []
        imminent_threshold = today + timedelta(days=2)

        imminent = [
            t for t in tasks
            if t.due_date and today <= t.due_date <= imminent_threshold and t.status != "completed"
        ]

        for t in imminent[:2]:
            score_data = priority_engine.calculate_breakdown(task=t, active_goals=goals, reference_date=today)
            due_label = "today" if t.due_date == today else ("tomorrow" if t.due_date == today + timedelta(days=1) else f"on {t.due_date.strftime('%b %d')}")
            recs.append({
                "category": "upcoming_deadline",
                "title": f"Upcoming Deadline: {t.title}",
                "recommendation": f"Task '{t.title}' is due {due_label}. Reserve a dedicated focus block to finish it.",
                "reason": f"High priority task approaching deadline on {t.due_date.isoformat()}.",
                "priority_score": score_data["normalized_score"],
                "priority_level": score_data["priority_level"],
                "related_goal": self._find_related_goal_title(t, goals),
                "related_deadline": t.due_date.isoformat(),
                "action_type": "schedule_focus_block",
                "action_payload": {
                    "task_id": str(t.id),
                    "task_title": t.title
                }
            })

        return recs

    # =========================================================================
    # 5. Unfinished High-Priority Tasks
    # =========================================================================
    def _detect_unfinished_high_priority(
        self,
        user_id: uuid.UUID,
        tasks: List[Task],
        goals: List[Goal],
        today: date
    ) -> List[Dict[str, Any]]:
        """Detects tasks marked urgent or high that have made no progress."""
        recs = []
        high_pri = [
            t for t in tasks
            if t.priority in ["urgent", "high"] and t.status in ["todo", "blocked"]
        ]

        for t in high_pri[:2]:
            score_data = priority_engine.calculate_breakdown(task=t, active_goals=goals, reference_date=today)
            recs.append({
                "category": "unfinished_high_priority",
                "title": f"High Priority Attention: {t.title}",
                "recommendation": f"You have an unstarted {t.priority.upper()} priority task: '{t.title}'. Would you like me to break it into smaller subtasks?",
                "reason": f"Task has priority '{t.priority}' but remains in '{t.status}' status.",
                "priority_score": score_data["normalized_score"],
                "priority_level": score_data["priority_level"],
                "related_goal": self._find_related_goal_title(t, goals),
                "related_deadline": str(t.due_date) if t.due_date else None,
                "action_type": "decompose_task",
                "action_payload": {
                    "task_id": str(t.id),
                    "task_title": t.title
                }
            })

        return recs

    # =========================================================================
    # 6. Inactive Goals
    # =========================================================================
    def _detect_inactive_goals(
        self,
        user_id: uuid.UUID,
        goals: List[Goal],
        tasks: List[Task],
        today: date
    ) -> List[Dict[str, Any]]:
        """Detects active goals that have 0% progress or no recent task progress."""
        recs = []
        for g in goals:
            if g.progress_pct == 0:
                recs.append({
                    "category": "inactive_goal",
                    "title": f"Inactive Goal: {g.title}",
                    "recommendation": f"Goal '{g.title}' currently has 0% progress. Would you like me to generate actionable milestone tasks to kickstart it?",
                    "reason": f"Active goal registered under category '{g.category}' with zero logged milestones.",
                    "priority_score": 0.62,
                    "priority_level": "medium",
                    "related_goal": g.title,
                    "related_deadline": str(g.target_date) if g.target_date else None,
                    "action_type": "generate_goal_milestones",
                    "action_payload": {
                        "goal_id": str(g.id),
                        "goal_title": g.title
                    }
                })
                break  # alert on one inactive goal to prevent clutter

        return recs

    # =========================================================================
    # 7. Interviews
    # =========================================================================
    def _detect_interviews(
        self,
        user_id: uuid.UUID,
        events: List[CalendarEvent],
        goals: List[Goal],
        now_utc: datetime
    ) -> List[Dict[str, Any]]:
        """Detects interviews in the next 7 days that are not already flagged by prep gaps."""
        recs = []
        for evt in events:
            st = to_utc(evt.start_time)
            if now_utc <= st <= now_utc + timedelta(days=7):
                if evt.event_type == "interview" or "interview" in evt.title.lower():
                    time_str = st.strftime("%A, %b %d at %I:%M %p")
                    recs.append({
                        "category": "interview",
                        "title": f"Scheduled Interview: {evt.title}",
                        "recommendation": f"You have an upcoming interview on {time_str}. Review your project talking points and STAR narratives.",
                        "reason": f"Event '{evt.title}' scheduled for {time_str}.",
                        "priority_score": 0.85,
                        "priority_level": "high",
                        "related_goal": "Career Advancement",
                        "related_deadline": time_str,
                        "action_type": "review_interview_materials",
                        "action_payload": {
                            "event_id": str(evt.id),
                            "event_title": evt.title
                        }
                    })
                    break

        return recs

    # =========================================================================
    # 8. Important Upcoming Events
    # =========================================================================
    def _detect_important_upcoming_events(
        self,
        user_id: uuid.UUID,
        events: List[CalendarEvent],
        goals: List[Goal],
        now_utc: datetime
    ) -> List[Dict[str, Any]]:
        """Detects upcoming important meetings, deadlines, or evaluations in next 24-48 hours."""
        recs = []
        for evt in events:
            st = to_utc(evt.start_time)
            if now_utc <= st <= now_utc + timedelta(hours=48):
                if evt.event_type in ["meeting", "deadline"] or any(k in evt.title.lower() for k in ["review", "deadline", "demo", "client"]):
                    time_str = st.strftime("%b %d at %I:%M %p")
                    recs.append({
                        "category": "important_event",
                        "title": f"Important Event: {evt.title}",
                        "recommendation": f"Upcoming event '{evt.title}' is scheduled for {time_str}. Ensure all preparation notes are reviewed.",
                        "reason": f"High-salience calendar event occurring in the next 48 hours.",
                        "priority_score": 0.72,
                        "priority_level": "medium",
                        "related_goal": None,
                        "related_deadline": time_str,
                        "action_type": "view_event_details",
                        "action_payload": {
                            "event_id": str(evt.id),
                            "event_title": evt.title
                        }
                    })
                    break

        return recs

    def _find_related_goal_title(self, task: Task, goals: List[Goal]) -> Optional[str]:
        if not goals:
            return None
        text = f"{task.title} {task.description or ''}".lower()
        for g in goals:
            words = [w for w in re.split(r'\W+', g.title.lower()) if len(w) > 3]
            if any(w in text for w in words):
                return g.title
        return None

proactive_detector = ProactiveDetector()
