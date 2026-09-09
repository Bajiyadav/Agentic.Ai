import asyncio
from dotenv import load_dotenv
load_dotenv()

from src.db.session import engine, Base
from src.db.models import *

async def create_tables():
    print("⚡ Connecting to PostgreSQL database...")
    async with engine.begin() as conn:
        print("⚡ Creating all multi-tenant relational tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All tables successfully created in PostgreSQL!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
