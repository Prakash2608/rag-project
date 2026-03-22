from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from app.core.config import settings
from app.core.logging import log


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",  # logs SQL in dev only
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency — use this in every route that needs DB"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            log.error("db_session_error", error=str(e))
            raise
        finally:
            await session.close()