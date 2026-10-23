from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.core.middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    safe_exception_handler
)
from app.api.v1 import (
    auth, users, projects, tasks, goals, dashboard,
    documents, chat, memories, knowledge_graph, agents,
    actions, calendar, workflows, recommendations,
    evaluation, observability, mlops
)
from app.services.graph.neo4j_client import neo4j_client
from app.core.redis_client import redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialize Neo4j and Redis connections (with automatic resilient in-memory fallbacks)
    await neo4j_client.connect()
    await redis_client.connect()
    yield
    # Shutdown logic
    await redis_client.close()
    await neo4j_client.close()
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="NEXUS AI - Agentic Personal Intelligence & Productivity Platform API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. Security Headers Middleware (Nosniff, Frame-Options, CSP, Referrer)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Rate Limiting Middleware (Sliding Window DoS & Brute Force Defense)
app.add_middleware(RateLimitMiddleware, auth_limit=15, general_limit=300, window_seconds=60)

# 3. Hardened CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# 4. Safe Exception Handler (Prevents stack trace / database schema disclosure)
app.add_exception_handler(Exception, safe_exception_handler)

# Root level routes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(goals.router, prefix="/goals", tags=["Goals"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(memories.router, prefix="/memories", tags=["Memories"])
app.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["Knowledge Graph"])
app.include_router(agents.router, prefix="/agents", tags=["Multi-Agent System"])
app.include_router(actions.router, prefix="/actions", tags=["Action Execution & Tools"])
app.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
app.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Proactive Intelligence & Recommendations"])
app.include_router(evaluation.router, prefix="/evaluation", tags=["AI Evaluation"])
app.include_router(observability.router, prefix="/observability", tags=["Observability & Metrics"])
app.include_router(mlops.router, prefix="/mlops", tags=["MLOps & MLflow"])

# API v1 prefixed routes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication v1"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users v1"])
app.include_router(projects.router, prefix=f"{settings.API_V1_STR}/projects", tags=["Projects v1"])
app.include_router(tasks.router, prefix=f"{settings.API_V1_STR}/tasks", tags=["Tasks v1"])
app.include_router(goals.router, prefix=f"{settings.API_V1_STR}/goals", tags=["Goals v1"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard v1"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["Documents v1"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["Chat v1"])
app.include_router(memories.router, prefix=f"{settings.API_V1_STR}/memories", tags=["Memories v1"])
app.include_router(knowledge_graph.router, prefix=f"{settings.API_V1_STR}/knowledge-graph", tags=["Knowledge Graph v1"])
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/agents", tags=["Multi-Agent System v1"])
app.include_router(actions.router, prefix=f"{settings.API_V1_STR}/actions", tags=["Action Execution & Tools v1"])
app.include_router(calendar.router, prefix=f"{settings.API_V1_STR}/calendar", tags=["Calendar v1"])
app.include_router(workflows.router, prefix=f"{settings.API_V1_STR}/workflows", tags=["Workflows v1"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}/recommendations", tags=["Proactive Intelligence & Recommendations v1"])
app.include_router(evaluation.router, prefix=f"{settings.API_V1_STR}/evaluation", tags=["AI Evaluation v1"])
app.include_router(observability.router, prefix=f"{settings.API_V1_STR}/observability", tags=["Observability & Metrics v1"])
app.include_router(mlops.router, prefix=f"{settings.API_V1_STR}/mlops", tags=["MLOps & MLflow v1"])

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": "1.0.0",
        "neo4j_connected": neo4j_client.is_connected
    }

