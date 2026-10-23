import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "NEXUS AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="nexus-secret-key-production-change-in-env-32bytes-min")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./nexus.db",
        description="SQLAlchemy Database URL"
    )
    
    # AI & RAG Configuration
    OPENAI_API_KEY: str = Field(default="", description="Optional OpenAI API key for cloud LLM/Embeddings")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    EMBEDDING_DIM: int = 384
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    
    # Neo4j Knowledge Graph Configuration
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="nexuspassword", description="Neo4j password")
    NEO4J_DATABASE: str = Field(default="neo4j", description="Neo4j database name")

    # Redis Cache Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Optional Redis URI for distributed caching")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://testserver",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

settings = Settings()
