import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    RiskLevel,
    GitHubCreateIssueInput
)
from app.services.tools.base import BaseTool

def utcnow():
    return datetime.now(timezone.utc)

class GitHubTool(BaseTool):
    """GitHub Tool providing repository management and issue creation with secure approval."""

    def __init__(self, db_session: Optional[AsyncSession] = None, user_id: Optional[Any] = None, **kwargs):
        super().__init__(
            name="github",
            description="Inspect GitHub repositories, create issues, and manage project tracking.",
            category="developer",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,  # Creating external issues requires user confirmation
            permissions=["github:issues:write", "github:repo:read"],
            input_model=GitHubCreateIssueInput,
            db_session=db_session,
            user_id=user_id,
            **kwargs
        )
        self._created_issues: List[Dict[str, Any]] = []

    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        if action == "create_issue":
            issue_number = len(self._created_issues) + 101
            repo = params.get("repo") or params.get("repository", "user/repo")
            issue_record = {
                "id": str(uuid.uuid4()),
                "issue_number": issue_number,
                "repository": repo,
                "repo": repo,
                "title": params["title"],
                "body": params["body"],
                "labels": params.get("labels", ["nexus-ai", "task"]),
                "url": f"https://github.com/{repo}/issues/{issue_number}",
                "status": "opened",
                "created_at": utcnow().isoformat()
            }
            self._created_issues.append(issue_record)
            return {
                "issue_number": issue_number,
                "repository": repo,
                "repo": repo,
                "url": issue_record["url"],
                "status": "created",
                "provider": "mock_local_github"
            }
        elif action == "list_repositories":
            return {
                "repositories": [
                    {
                        "name": "nexus-ai-platform",
                        "full_name": "user/nexus-ai-platform",
                        "stars": 42,
                        "primary_language": "Python",
                        "description": "Agentic Personal Intelligence Platform with Neo4j Knowledge Graph"
                    },
                    {
                        "name": "distributed-graph-rag",
                        "full_name": "user/distributed-graph-rag",
                        "stars": 18,
                        "primary_language": "TypeScript",
                        "description": "High-throughput graph retrieval pipeline"
                    }
                ],
                "count": 2
            }
        else:
            raise ValueError(f"Unknown github action '{action}'. Supported: create_issue, list_repositories")

github_tool = GitHubTool()
