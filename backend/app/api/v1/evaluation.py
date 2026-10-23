"""
Evaluation API Endpoints:
Provides access to RAG evaluation, Agent evaluation, and benchmark executions.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.evaluation.runner import evaluation_runner

router = APIRouter()

@router.post("/run")
async def execute_evaluation_benchmark(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Triggers an execution of the full RAG & Multi-Agent evaluation benchmark.
    Measures Context Precision, Context Recall, Answer Relevance, Faithfulness,
    Citation Accuracy, Task Success Rate, Planning Accuracy, Tool Selection Accuracy,
    and logs run metrics into MLflow.
    """
    return evaluation_runner.run_full_evaluation()

@router.get("/rag")
async def get_rag_evaluation(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Returns the latest RAG evaluation benchmark results.
    """
    return evaluation_runner.run_rag_evaluation()

@router.get("/agent")
async def get_agent_evaluation(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Returns the latest Agent evaluation benchmark results.
    """
    return evaluation_runner.run_agent_evaluation()

@router.get("/summary")
async def get_evaluation_summary(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Returns aggregated evaluation summary for the Developer / Admin dashboard.
    """
    return evaluation_runner.get_summary()
