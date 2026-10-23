import uuid
import logging
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import AIRecommendation, ProactivePreferences
from app.services.proactive.detector import proactive_detector
from app.services.workflows.interview_prep import interview_prep_workflow
from app.schemas.agent import OrchestrationRequest

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)

class ProactiveService:
    """
    Coordinates detection, anti-spam rate limiting, preferences,
    persistence, dismissal, and action execution.
    """

    async def get_preferences(self, user_id: uuid.UUID, db: AsyncSession) -> ProactivePreferences:
        stmt = select(ProactivePreferences).where(ProactivePreferences.user_id == user_id)
        res = await db.execute(stmt)
        prefs = res.scalar_one_or_none()

        if not prefs:
            prefs = ProactivePreferences(
                user_id=user_id,
                enabled=True,
                frequency="daily",
                max_daily_recommendations=5,
                muted_categories=[]
            )
            db.add(prefs)
            await db.flush()

        return prefs

    async def update_preferences(
        self,
        user_id: uuid.UUID,
        updates: Dict[str, Any],
        db: AsyncSession
    ) -> ProactivePreferences:
        prefs = await self.get_preferences(user_id=user_id, db=db)

        if "enabled" in updates and updates["enabled"] is not None:
            prefs.enabled = bool(updates["enabled"])
        if "frequency" in updates and updates["frequency"] is not None:
            prefs.frequency = str(updates["frequency"])
        if "max_daily_recommendations" in updates and updates["max_daily_recommendations"] is not None:
            prefs.max_daily_recommendations = int(updates["max_daily_recommendations"])
        if "muted_categories" in updates and updates["muted_categories"] is not None:
            prefs.muted_categories = list(updates["muted_categories"])

        prefs.updated_at = utcnow()
        await db.commit()
        await db.refresh(prefs)
        return prefs

    async def generate_recommendations(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        reference_date: Optional[date] = None
    ) -> List[AIRecommendation]:
        """
        Runs detection while respecting user anti-spam preferences:
        - If proactive suggestions are disabled, returns empty list.
        - Respects muted categories.
        - Caps active recommendations to max_daily_recommendations.
        - Suppresses recently dismissed recommendations.
        """
        prefs = await self.get_preferences(user_id=user_id, db=db)
        if not prefs.enabled:
            logger.info(f"Proactive suggestions disabled for user {user_id}.")
            return []

        # 1. Fetch current active recommendations
        active_stmt = (
            select(AIRecommendation)
            .where(
                and_(
                    AIRecommendation.user_id == user_id,
                    AIRecommendation.status == "active"
                )
            )
            .order_by(AIRecommendation.priority_score.desc())
        )
        active_res = await db.execute(active_stmt)
        existing_active = active_res.scalars().all()

        # 2. Fetch recently dismissed to avoid re-spamming within 24h
        cutoff_24h = utcnow() - timedelta(hours=24)
        dismissed_stmt = select(AIRecommendation).where(
            and_(
                AIRecommendation.user_id == user_id,
                AIRecommendation.status == "dismissed",
                AIRecommendation.dismissed_at >= cutoff_24h
            )
        )
        dismissed_res = await db.execute(dismissed_stmt)
        recently_dismissed_titles = {r.title for r in dismissed_res.scalars().all()}
        existing_active_titles = {r.title for r in existing_active}

        # 3. Run detector
        detected_items = await proactive_detector.detect_all(
            user_id=user_id,
            db=db,
            reference_date=reference_date,
            muted_categories=prefs.muted_categories
        )

        newly_created: List[AIRecommendation] = []
        available_slots = max(0, prefs.max_daily_recommendations - len(existing_active))

        for item in detected_items:
            if available_slots <= 0:
                break

            title = item["title"]
            if title in existing_active_titles or title in recently_dismissed_titles:
                continue

            rec = AIRecommendation(
                user_id=user_id,
                category=item["category"],
                title=title,
                recommendation=item["recommendation"],
                reason=item["reason"],
                priority_score=item["priority_score"],
                priority_level=item["priority_level"],
                related_goal=item.get("related_goal"),
                related_deadline=item.get("related_deadline"),
                action_type=item.get("action_type"),
                action_payload=item.get("action_payload", {}),
                status="active"
            )
            db.add(rec)
            newly_created.append(rec)
            existing_active_titles.add(title)
            available_slots -= 1

        if newly_created:
            await db.commit()

        # Return refreshed active list
        return await self.get_active_recommendations(user_id=user_id, db=db)

    async def get_active_recommendations(
        self,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> List[AIRecommendation]:
        """Returns active AI recommendations for dashboard and API."""
        stmt = (
            select(AIRecommendation)
            .where(
                and_(
                    AIRecommendation.user_id == user_id,
                    AIRecommendation.status == "active"
                )
            )
            .order_by(AIRecommendation.priority_score.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def dismiss_recommendation(
        self,
        recommendation_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> AIRecommendation:
        """Dismisses an active recommendation so it is removed from view."""
        stmt = select(AIRecommendation).where(
            and_(
                AIRecommendation.id == recommendation_id,
                AIRecommendation.user_id == user_id
            )
        )
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()
        if not rec:
            raise LookupError(f"Recommendation '{recommendation_id}' not found.")

        rec.status = "dismissed"
        rec.dismissed_at = utcnow()
        rec.updated_at = utcnow()
        await db.commit()
        await db.refresh(rec)
        return rec

    async def execute_recommendation_action(
        self,
        recommendation_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Executes action attached to recommendation (e.g. creating interview prep plan).
        """
        stmt = select(AIRecommendation).where(
            and_(
                AIRecommendation.id == recommendation_id,
                AIRecommendation.user_id == user_id
            )
        )
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()
        if not rec:
            raise LookupError(f"Recommendation '{recommendation_id}' not found.")

        result_data: Dict[str, Any] = {"status": "success", "action_type": rec.action_type}

        if rec.action_type == "create_preparation_plan":
            msg = rec.action_payload.get("message", "I have an interview tomorrow. Help me prepare.")
            workflow_res = await interview_prep_workflow.execute(
                request=OrchestrationRequest(message=msg),
                user_id=user_id,
                db=db
            )
            result_data["workflow_result"] = workflow_res.model_dump(mode="json")
            result_data["message"] = "Interview preparation plan generated and tasks saved."

        rec.status = "executed"
        rec.updated_at = utcnow()
        await db.commit()
        await db.refresh(rec)

        result_data["recommendation_id"] = str(rec.id)
        return result_data

proactive_service = ProactiveService()
