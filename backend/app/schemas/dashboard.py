from typing import List, Dict
from pydantic import BaseModel
from app.schemas.task import TaskResponse
from app.schemas.project import ProjectResponse
from app.schemas.goal import GoalResponse
from app.schemas.recommendation import RecommendationResponse

class DashboardStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completion_rate: float
    active_projects_count: int
    active_goals_count: int
    average_goal_progress: float

class DashboardOverview(BaseModel):
    stats: DashboardStats
    todays_tasks: List[TaskResponse]
    upcoming_tasks: List[TaskResponse]
    active_projects: List[ProjectResponse]
    active_goals: List[GoalResponse]
    ai_recommendations: List[RecommendationResponse] = []
