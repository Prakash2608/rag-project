import asyncio
from app.db.base import Base
from app.db.session import engine
import app.db.models  # noqa — registers all models

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created successfully")

asyncio.run(main())