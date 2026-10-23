"""
MLOps & MLflow API Endpoints:
Provides experiment listing, run tracking, and registry versioning for:
- prompts
- models
- embeddings
- rerankers
- recommendation models
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_user
from app.models.user import User
from app.mlops.mlflow_service import mlflow_service

router = APIRouter()

@router.get("/experiments")
async def list_experiments(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Returns list of MLflow experiments and their latest runs:
    - model_experiments
    - embedding_experiments
    - retrieval_experiments
    - recommendation_experiments
    - evaluation_results
    """
    return mlflow_service.list_experiments()

@router.get("/experiments/{experiment_name}/runs")
async def get_experiment_runs(
    experiment_name: str,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Returns individual experiment runs with parameters and metrics.
    """
    return mlflow_service.get_experiment_runs(experiment_name=experiment_name, limit=limit)

@router.get("/registry")
async def get_model_registry(
    current_user: User = Depends(get_current_user)
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns versioned assets:
    - prompts
    - models
    - embeddings
    - rerankers
    - recommendation models
    """
    return mlflow_service.get_registry()
