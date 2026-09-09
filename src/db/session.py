import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://bajiyadav@localhost:5432/auditagent")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql+psycopg2://bajiyadav@localhost:5432/auditagent")
if SYNC_DATABASE_URL.startswith("postgres://"):
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif SYNC_DATABASE_URL.startswith("postgresql://") and not SYNC_DATABASE_URL.startswith("postgresql+psycopg2://"):
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

is_serverless = os.getenv("VERCEL") == "1"
engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}
if is_serverless:
    engine_kwargs.update({"pool_size": 2, "max_overflow": 3})
else:
    engine_kwargs.update({"pool_size": 15, "max_overflow": 10})

engine = create_async_engine(
    DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async_session_factory = AsyncSessionLocal

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
