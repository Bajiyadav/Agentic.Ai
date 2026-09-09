import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://bajiyadav@localhost:5432/auditagent")
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql+psycopg2://bajiyadav@localhost:5432/auditagent")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=15,
    max_overflow=10,
    pool_pre_ping=True
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
