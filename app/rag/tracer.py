import uuid
import time
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import LLMTrace
from app.core.logging import log


@dataclass
class LLMTracer:
    """
    Tracks everything about a single RAG query.
    Created at start of request, saved to DB at end.
    """
    user_id           : str
    question          : str
    model_name        : str  = ""
    prompt_tokens     : int  = 0
    completion_tokens : int  = 0
    total_cost_usd    : float = 0.0
    embed_ms          : int  = 0
    retrieve_ms       : int  = 0
    llm_ms            : int  = 0
    trace_id          : str  = field(default_factory=lambda: str(uuid.uuid4()))
    _start_time       : float = field(default_factory=time.perf_counter, repr=False)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def total_ms(self) -> int:
        return int((time.perf_counter() - self._start_time) * 1000)

    async def save(self, db: AsyncSession):
        """Persists trace to DB"""
        row = LLMTrace(
            id                = self.trace_id,
            user_id           = self.user_id,
            question          = self.question,
            model_name        = self.model_name,
            prompt_tokens     = self.prompt_tokens,
            completion_tokens = self.completion_tokens,
            total_tokens      = self.total_tokens,
            total_cost_usd    = self.total_cost_usd,
            embed_ms          = self.embed_ms,
            retrieve_ms       = self.retrieve_ms,
            llm_ms            = self.llm_ms,
            total_ms          = self.total_ms,
        )
        db.add(row)
        await db.commit()

        log.info("trace_saved",
            trace_id          = self.trace_id,
            user_id           = self.user_id,
            model             = self.model_name,
            prompt_tokens     = self.prompt_tokens,
            completion_tokens = self.completion_tokens,
            total_cost_usd    = self.total_cost_usd,
            embed_ms          = self.embed_ms,
            retrieve_ms       = self.retrieve_ms,
            llm_ms            = self.llm_ms,
            total_ms          = self.total_ms,
        )