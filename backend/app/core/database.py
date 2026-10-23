import uuid
from typing import AsyncGenerator
from sqlalchemy import TypeDecorator, CHAR, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's native UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            if not isinstance(value, uuid.UUID):
                try:
                    return str(uuid.UUID(str(value)))
                except (ValueError, AttributeError):
                    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(value)))
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                try:
                    return str(uuid.UUID(str(value)))
                except (ValueError, AttributeError):
                    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(value)))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                try:
                    return uuid.UUID(str(value))
                except (ValueError, AttributeError):
                    return uuid.uuid5(uuid.NAMESPACE_DNS, str(value))
            else:
                return value

class VectorType(TypeDecorator):
    """Platform-independent Vector type.
    Uses pgvector's Vector type when running on PostgreSQL,
    and falls back to JSON on SQLite or other engines.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 384, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector as PGVector
                return dialect.type_descriptor(PGVector(self.dim))
            except ImportError:
                return dialect.type_descriptor(JSON())
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        else:
            if isinstance(value, list):
                return value
            elif isinstance(value, str):
                import json
                return json.loads(value)
            return list(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            import json
            try:
                return json.loads(value)
            except Exception:
                return [float(x.strip()) for x in value.strip("[]").split(",") if x.strip()]
        return list(value)

connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
