from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.api.deps import get_admin_user
from app.db.models import User

router = APIRouter()


@router.get("/usage")
async def usage_stats(
    db   : AsyncSession = Depends(get_db),
    admin: User         = Depends(get_admin_user),
):
    """Per user token and cost breakdown"""
    result = await db.execute(text("""
        SELECT
            user_id,
            COUNT(*)                                AS total_queries,
            SUM(prompt_tokens)                      AS total_prompt_tokens,
            SUM(completion_tokens)                  AS total_completion_tokens,
            SUM(total_tokens)                       AS total_tokens,
            ROUND(SUM(total_cost_usd)::numeric, 6)  AS total_cost_usd,
            ROUND(AVG(total_ms)::numeric, 0)        AS avg_latency_ms,
            ROUND(AVG(llm_ms)::numeric, 0)          AS avg_llm_ms,
            MAX(created_at)                         AS last_query_at
        FROM llm_traces
        GROUP BY user_id
        ORDER BY total_cost_usd DESC
    """))
    rows = result.mappings().all()
    return {"users": [dict(r) for r in rows]}


@router.get("/usage/daily")
async def daily_usage(
    db   : AsyncSession = Depends(get_db),
    admin: User         = Depends(get_admin_user),
):
    """Daily token and cost summary for last 30 days"""
    result = await db.execute(text("""
        SELECT
            DATE(created_at)                        AS day,
            COUNT(*)                                AS total_queries,
            SUM(total_tokens)                       AS total_tokens,
            ROUND(SUM(total_cost_usd)::numeric, 6)  AS total_cost_usd
        FROM llm_traces
        GROUP BY DATE(created_at)
        ORDER BY day DESC
        LIMIT 30
    """))
    rows = result.mappings().all()
    return {"daily": [dict(r) for r in rows]}


@router.get("/usage/me")
async def my_usage(
    db  : AsyncSession = Depends(get_db),
    user: User         = Depends(get_admin_user),
):
    """Current user own usage stats"""
    result = await db.execute(text("""
        SELECT
            COUNT(*)                                AS total_queries,
            SUM(prompt_tokens)                      AS total_prompt_tokens,
            SUM(completion_tokens)                  AS total_completion_tokens,
            ROUND(SUM(total_cost_usd)::numeric, 6)  AS total_cost_usd,
            ROUND(AVG(total_ms)::numeric, 0)        AS avg_latency_ms
        FROM llm_traces
        WHERE user_id = :user_id
    """), {"user_id": user.id})
    row = result.mappings().one_or_none()
    return dict(row) if row else {}