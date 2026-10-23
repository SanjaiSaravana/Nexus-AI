import uuid
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import RiskLevel
from app.models.document import Document
from app.services.tools.base import BaseTool
from app.services.rag_service import rag_service

class DocumentTool(BaseTool):
    """Document Intelligence Tool providing semantic search and document retrieval."""

    def __init__(self):
        super().__init__(
            name="documents",
            description="Search connected documents, list uploaded files, and retrieve document chunks.",
            category="knowledge",
            risk_level=RiskLevel.READ_ONLY,
            requires_confirmation=False,
            permissions=["documents:read"]
        )

    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        if action == "search_documents":
            query = params.get("query", "")
            top_k = params.get("top_k", 4)
            chunks_with_scores = await rag_service.retrieve_chunks(
                db=db,
                user_id=user_id,
                query=query,
                top_k=top_k
            )
            return {
                "results": [
                    {
                        "chunk_id": str(c.id),
                        "document_id": str(c.document_id),
                        "filename": c.document.filename if c.document else "Document",
                        "content": c.content[:300],
                        "relevance_score": round(float(s), 3)
                    }
                    for c, s in chunks_with_scores
                ],
                "count": len(chunks_with_scores)
            }
        elif action == "list_documents":
            stmt = select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
            res = await db.execute(stmt)
            docs = res.scalars().all()
            return {
                "documents": [
                    {
                        "id": str(d.id),
                        "filename": d.filename,
                        "document_type": d.document_type,
                        "file_size": d.file_size,
                        "status": d.status
                    }
                    for d in docs
                ],
                "count": len(docs)
            }
        else:
            raise ValueError(f"Unknown document action '{action}'. Supported: search_documents, list_documents")

document_tool = DocumentTool()
