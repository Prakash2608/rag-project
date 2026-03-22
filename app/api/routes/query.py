from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user, get_redis
from app.rag.pipeline import run_query
from app.core.logging import log

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


@router.post("/")
async def query(
    body  : QueryRequest,
    db    : AsyncSession = Depends(get_db),
    redis                = Depends(get_redis),
    user  : User         = Depends(get_current_user),
):
    log.info("query_received",
        user_id  = user.id,
        question = body.question[:50],
    )

    result = await run_query(
        question = body.question,
        user_id  = user.id,
        db       = db,
        redis    = redis,
    )

    return result