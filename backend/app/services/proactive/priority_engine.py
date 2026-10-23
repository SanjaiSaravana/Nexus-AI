import re
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union
from app.models.task import Task
from app.models.goal import Goal

class PriorityEngine:
    """
    Priority Engine implementing multi-factor priority calculation:
    Priority = Urgency + Deadline + Goal relevance + Importance + Dependencies + Estimated effort
    Normalized strictly to [0.0, 1.0].
    """

    # Weights summing to 1.0 for balanced multi-factor scoring
    WEIGHT_URGENCY = 0.22
    WEIGHT_DEADLINE = 0.22
    WEIGHT_GOAL_RELEVANCE = 0.18
    WEIGHT_IMPORTANCE = 0.16
    WEIGHT_DEPENDENCIES = 0.12
    WEIGHT_ESTIMATED_EFFORT = 0.10

    def calculate_priority(
        self,
        task: Union[Task, Dict[str, Any]],
        active_goals: Optional[List[Goal]] = None,
        reference_date: Optional[date] = None,
        custom_factors: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculates normalized priority score [0.0 - 1.0] for a task.
        """
        breakdown = self.calculate_breakdown(
            task=task,
            active_goals=active_goals,
            reference_date=reference_date,
            custom_factors=custom_factors
        )
        return breakdown["normalized_score"]

    def calculate_breakdown(
        self,
        task: Union[Task, Dict[str, Any]],
        active_goals: Optional[List[Goal]] = None,
        reference_date: Optional[date] = None,
        custom_factors: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculates individual components and normalized composite priority score.
        """
        today = reference_date or date.today()
        custom = custom_factors or {}

        # 1. URGENCY (0.0 to 1.0)
        priority_val = getattr(task, "priority", None) if hasattr(task, "priority") else task.get("priority")
        priority_str = str(priority_val or "medium").lower()

        if "urgency" in custom:
            urgency_score = max(0.0, min(1.0, float(custom["urgency"])))
        elif priority_str == "urgent":
            urgency_score = 1.0
        elif priority_str == "high":
            urgency_score = 0.80
        elif priority_str == "medium":
            urgency_score = 0.50
        else:
            urgency_score = 0.20

        # 2. DEADLINE (0.0 to 1.0)
        due_date = getattr(task, "due_date", None) if hasattr(task, "due_date") else task.get("due_date")
        if isinstance(due_date, datetime):
            due_date = due_date.date()
        elif isinstance(due_date, str):
            try:
                due_date = date.fromisoformat(due_date.split("T")[0])
            except Exception:
                due_date = None

        if "deadline" in custom:
            deadline_score = max(0.0, min(1.0, float(custom["deadline"])))
        elif due_date is None:
            deadline_score = 0.15
        else:
            days_diff = (due_date - today).days
            if days_diff < 0:
                # Overdue
                deadline_score = 1.0
            elif days_diff == 0:
                # Due today
                deadline_score = 0.95
            elif days_diff == 1:
                # Due tomorrow
                deadline_score = 0.85
            elif days_diff <= 3:
                # Due within 3 days
                deadline_score = 0.70
            elif days_diff <= 7:
                # Due this week
                deadline_score = 0.50
            else:
                deadline_score = 0.30

        # 3. GOAL RELEVANCE (0.0 to 1.0)
        title = getattr(task, "title", None) if hasattr(task, "title") else task.get("title", "")
        desc = getattr(task, "description", None) if hasattr(task, "description") else task.get("description", "")
        text = f"{title} {desc}".lower()

        if "goal_relevance" in custom:
            goal_relevance_score = max(0.0, min(1.0, float(custom["goal_relevance"])))
        else:
            goal_relevance_score = 0.30
            if active_goals:
                for g in active_goals:
                    g_title = g.title.lower()
                    g_cat = g.category.lower()
                    # Check for direct word overlaps or keywords
                    words = [w for w in re.split(r'\W+', g_title) if len(w) > 3]
                    if any(w in text for w in words) or g_cat in text:
                        goal_relevance_score = 0.90
                        break
                    elif hasattr(task, "project_id") and getattr(task, "project_id", None):
                        goal_relevance_score = 0.65
            elif hasattr(task, "project_id") and getattr(task, "project_id", None):
                goal_relevance_score = 0.60

        # 4. IMPORTANCE (0.0 to 1.0)
        if "importance" in custom:
            importance_score = max(0.0, min(1.0, float(custom["importance"])))
        else:
            # Semantic keyword inspection
            high_value_keywords = [
                "interview", "screening", "security", "production", "launch",
                "client", "investor", "critical", "outage", "deploy", "architecture"
            ]
            if any(k in text for k in high_value_keywords):
                importance_score = 0.95
            elif priority_str in ["urgent", "high"]:
                importance_score = 0.80
            elif priority_str == "medium":
                importance_score = 0.50
            else:
                importance_score = 0.25

        # 5. DEPENDENCIES (0.0 to 1.0)
        if "dependencies" in custom:
            dependencies_score = max(0.0, min(1.0, float(custom["dependencies"])))
        else:
            # If task mentions unblocking, core architecture, or prerequisites
            if any(k in text for k in ["blocker", "prerequisite", "unblock", "core", "foundation", "setup"]):
                dependencies_score = 0.90
            elif getattr(task, "status", None) == "blocked":
                dependencies_score = 0.35
            else:
                dependencies_score = 0.50

        # 6. ESTIMATED EFFORT (0.0 to 1.0)
        if "estimated_effort" in custom:
            estimated_effort_score = max(0.0, min(1.0, float(custom["estimated_effort"])))
        else:
            # Quick wins and high-impact prep
            if any(k in text for k in ["quick", "review", "email", "check", "confirm", "skim"]):
                estimated_effort_score = 0.85
            elif any(k in text for k in ["deep-dive", "refactor", "overhaul", "architect", "rewrite"]):
                estimated_effort_score = 0.75  # Needs early scheduling
            else:
                estimated_effort_score = 0.55

        # COMPOSITE WEIGHTED SUM (Already naturally normalized between 0.0 and 1.0)
        weighted_sum = (
            self.WEIGHT_URGENCY * urgency_score +
            self.WEIGHT_DEADLINE * deadline_score +
            self.WEIGHT_GOAL_RELEVANCE * goal_relevance_score +
            self.WEIGHT_IMPORTANCE * importance_score +
            self.WEIGHT_DEPENDENCIES * dependencies_score +
            self.WEIGHT_ESTIMATED_EFFORT * estimated_effort_score
        )

        normalized_score = round(max(0.0, min(1.0, weighted_sum)), 3)

        return {
            "normalized_score": normalized_score,
            "priority_level": self.get_priority_level(normalized_score),
            "factors": {
                "urgency": round(urgency_score, 3),
                "deadline": round(deadline_score, 3),
                "goal_relevance": round(goal_relevance_score, 3),
                "importance": round(importance_score, 3),
                "dependencies": round(dependencies_score, 3),
                "estimated_effort": round(estimated_effort_score, 3)
            }
        }

    def get_priority_level(self, score: float) -> str:
        if score >= 0.80:
            return "urgent"
        elif score >= 0.65:
            return "high"
        elif score >= 0.45:
            return "medium"
        return "low"

priority_engine = PriorityEngine()
