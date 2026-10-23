from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.goal import Goal
from app.schemas.project import ProjectResponse
from app.schemas.task import TaskResponse
from app.schemas.goal import GoalResponse
from app.schemas.dashboard import DashboardOverview, DashboardStats

router = APIRouter()

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    today = date.today()
    next_week = today + timedelta(days=7)

    # All user tasks
    tasks_stmt = select(Task).where(Task.user_id == current_user.id)
    tasks_res = await db.execute(tasks_stmt)
    all_tasks = tasks_res.scalars().all()

    total_tasks = len(all_tasks)
    completed_tasks = sum(1 for t in all_tasks if t.status == "completed")
    in_progress_tasks = sum(1 for t in all_tasks if t.status == "in_progress")
    pending_tasks = sum(1 for t in all_tasks if t.status in ("todo", "in_progress", "blocked"))
    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    # Today's tasks (due today or uncompleted and created today or due on or before today)
    todays_tasks = [t for t in all_tasks if t.due_date == today and t.status != "completed"]
    # If no tasks explicitly due today, show up to 5 non-completed tasks prioritized
    if not todays_tasks:
        todays_tasks = [t for t in all_tasks if t.status != "completed"][:5]

    # Upcoming tasks (due between tomorrow and next week)
    upcoming_tasks = [
        t for t in all_tasks 
        if t.due_date and t.due_date > today and t.due_date <= next_week and t.status != "completed"
    ]
    upcoming_tasks.sort(key=lambda t: t.due_date)

    # Active projects
    proj_stmt = select(Project).where(
        Project.user_id == current_user.id,
        Project.status == "active"
    ).order_by(Project.created_at.desc()).limit(6)
    proj_res = await db.execute(proj_stmt)
    active_projects = proj_res.scalars().all()

    # Active projects count
    active_projects_count = len(active_projects)

    # Goals
    goal_stmt = select(Goal).where(
        Goal.user_id == current_user.id,
        Goal.status == "active"
    ).order_by(Goal.created_at.desc())
    goal_res = await db.execute(goal_stmt)
    active_goals = goal_res.scalars().all()

    active_goals_count = len(active_goals)
    avg_goal_progress = (
        round(sum(g.progress_pct for g in active_goals) / active_goals_count, 1)
        if active_goals_count > 0 else 0.0
    )

    stats = DashboardStats(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        completion_rate=completion_rate,
        active_projects_count=active_projects_count,
        active_goals_count=active_goals_count,
        average_goal_progress=avg_goal_progress
    )

    # Proactive AI Recommendations
    from app.services.proactive.service import proactive_service
    from app.schemas.recommendation import RecommendationResponse

    active_recs = await proactive_service.get_active_recommendations(user_id=current_user.id, db=db)
    if not active_recs:
        active_recs = await proactive_service.generate_recommendations(user_id=current_user.id, db=db)

    return DashboardOverview(
        stats=stats,
        todays_tasks=[TaskResponse.model_validate(t) for t in todays_tasks[:6]],
        upcoming_tasks=[TaskResponse.model_validate(t) for t in upcoming_tasks[:6]],
        active_projects=[ProjectResponse.model_validate(p) for p in active_projects],
        active_goals=[GoalResponse.model_validate(g) for g in active_goals],
        ai_recommendations=[RecommendationResponse.model_validate(r) for r in active_recs]
    )
