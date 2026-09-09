import pytest
import pytest_asyncio
from src.db.session import engine

@pytest_asyncio.fixture(autouse=True)
async def dispose_engine_on_cleanup():
    yield
    await engine.dispose()
