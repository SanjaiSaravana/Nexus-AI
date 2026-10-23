import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    RiskLevel,
    EmailSendInput
)
from app.services.tools.base import BaseTool

def utcnow():
    return datetime.now(timezone.utc)

class EmailTool(BaseTool):
    """Email Tool with secure action confirmation and local provider implementation."""

    def __init__(self, db_session: Optional[AsyncSession] = None, user_id: Optional[Any] = None, **kwargs):
        super().__init__(
            name="email",
            description="Send, draft, and list emails. External sends require explicit user approval.",
            category="communication",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,  # Sending email is sensitive external action!
            permissions=["email:send", "email:read"],
            input_model=EmailSendInput,
            db_session=db_session,
            user_id=user_id,
            **kwargs
        )
        # Local mock outbox storing simulated dispatches
        self._sent_emails: List[Dict[str, Any]] = []
        self._drafts: List[Dict[str, Any]] = []

    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        if action == "send_email":
            msg_id = str(uuid.uuid4())
            recipient = params.get("to_address") or params.get("recipient", "")
            record = {
                "id": msg_id,
                "user_id": str(user_id),
                "recipient": recipient,
                "to_address": recipient,
                "subject": params.get("subject", ""),
                "body": params.get("body", ""),
                "cc": params.get("cc", []),
                "status": "sent",
                "sent_at": utcnow().isoformat()
            }
            self._sent_emails.append(record)
            return {
                "message_id": msg_id,
                "recipient": recipient,
                "to_address": recipient,
                "subject": params.get("subject", ""),
                "status": "sent",
                "provider": "mock_local_smtp"
            }
        elif action == "draft_email":
            draft_id = str(uuid.uuid4())
            recipient = params.get("to_address") or params.get("recipient", "")
            record = {
                "id": draft_id,
                "user_id": str(user_id),
                "recipient": recipient,
                "to_address": recipient,
                "subject": params.get("subject", "Draft"),
                "body": params.get("body", ""),
                "created_at": utcnow().isoformat()
            }
            self._drafts.append(record)
            return {
                "draft_id": draft_id,
                "status": "draft_saved"
            }
        elif action == "list_inbox":
            msgs = [
                {
                    "from": "interviewer@company.com",
                    "subject": "Interview Confirmation & Logistics",
                    "preview": "We are excited to speak with you tomorrow regarding the Principal AI Engineer position.",
                    "date": "Today, 10:30 AM"
                }
            ]
            return {
                "messages": msgs,
                "inbox": msgs,
                "count": len(msgs)
            }
        else:
            raise ValueError(f"Unknown email action '{action}'. Supported: send_email, draft_email, list_inbox")

email_tool = EmailTool()
