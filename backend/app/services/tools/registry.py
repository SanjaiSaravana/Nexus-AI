from typing import Dict, List, Optional
from app.schemas.tool import ToolDefinitionResponse
from app.services.tools.base import BaseTool
from app.services.tools.task_tool import task_tool
from app.services.tools.calendar_tool import calendar_tool
from app.services.tools.document_tool import document_tool
from app.services.tools.memory_tool import memory_tool
from app.services.tools.project_tool import project_tool
from app.services.tools.graph_tool import knowledge_graph_tool
from app.services.tools.search_tool import search_tool
from app.services.tools.email_tool import email_tool
from app.services.tools.github_tool import github_tool

class ToolRegistry:
    """Central registry maintaining all NEXUS security-scoped tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {
            "task": task_tool,
            "calendar": calendar_tool,
            "documents": document_tool,
            "memory": memory_tool,
            "projects": project_tool,
            "knowledge_graph": knowledge_graph_tool,
            "search": search_tool,
            "email": email_tool,
            "github": github_tool,
        }

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name.lower())

    def list_definitions(self) -> List[ToolDefinitionResponse]:
        return [tool.get_definition() for tool in self._tools.values()]

    def list_tools(self) -> List[ToolDefinitionResponse]:
        return self.list_definitions()

    @property
    def tools(self) -> Dict[str, BaseTool]:
        return self._tools

tool_registry = ToolRegistry()
