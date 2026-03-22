import time
import json
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log
from app.core.exceptions import LLMException, ValidationException
from app.rag.tracer import LLMTracer
from app.rag.cost import calculate_cost, format_cost


async def run_query(
    question : str,
    user_id  : str,
    db       : AsyncSession,
    redis,
) -> dict:
    """
    Full RAG pipeline:
    1. Check Redis cache
    2. Embed the question
    3. Retrieve top-k chunks from Qdrant
    4. Build prompt
    5. Call LLM (Groq)
    6. Save trace to DB
    7. Cache result
    8. Return answer
    """

    # ── Validate input ────────────────────────────────────────
    if not question.strip():
        raise ValidationException("Question cannot be empty")

    if len(question) > 2000:
        raise ValidationException("Question too long. Max 2000 characters")

    # ── Start tracer ──────────────────────────────────────────
    tracer = LLMTracer(user_id=user_id, question=question)

    # ── Step 1: Check Redis cache ─────────────────────────────
    cache_key = "rag:query:" + hashlib.sha256(question.encode()).hexdigest()
    cached    = await redis.get(cache_key)

    if cached:
        log.info("cache_hit", question=question[:50])
        result                      = json.loads(cached)
        result["meta"]["cache_hit"] = True
        return result

    # ── Step 2: Embed the question ────────────────────────────
    t0 = time.perf_counter()
    try:
        import ollama
        embed_result = ollama.embeddings(
            model  = settings.OLLAMA_EMBED_MODEL,
            prompt = question,
        )
        query_vector = embed_result["embedding"]

    except Exception as e:
        raise LLMException(f"Embedding failed: {str(e)}")

    tracer.embed_ms = int((time.perf_counter() - t0) * 1000)
    log.info("question_embedded", embed_ms=tracer.embed_ms)

    # ── Step 3: Retrieve chunks from Qdrant ───────────────────
    t1 = time.perf_counter()
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant  = QdrantClient(
            host = settings.QDRANT_HOST,
            port = settings.QDRANT_PORT,
        )

        results = qdrant.search(
            collection_name = "documents",
            query_vector    = query_vector,
            limit           = 4,          # was 5
            with_payload    = True,
            score_threshold = 0.55,       # only chunks with good relevance
        )

    except Exception as e:
        raise LLMException(f"Vector search failed: {str(e)}")

    tracer.retrieve_ms = int((time.perf_counter() - t1) * 1000)
    log.info("chunks_retrieved",
        num_chunks  = len(results),
        retrieve_ms = tracer.retrieve_ms,
        top_score   = round(results[0].score, 4) if results else 0,
    )

    # ── No results found ──────────────────────────────────────
    if not results:
        return {
            "answer" : "I could not find any relevant information in the uploaded documents.",
            "sources": [],
            "meta"   : {
                "cache_hit"        : False,
                "embed_ms"         : tracer.embed_ms,
                "retrieve_ms"      : tracer.retrieve_ms,
                "llm_ms"           : 0,
                "total_ms"         : tracer.total_ms,
                "prompt_tokens"    : 0,
                "completion_tokens": 0,
                "total_cost"       : "free",
            }
        }

# ── Step 4: Build prompt ──────────────────────────────────
    context = "\n\n---\n\n".join(
        f"[Chunk {i+1}]:\n{r.payload['chunk']}"
        for i, r in enumerate(results)
    )

    messages = [
        {
            "role"   : "system",
            "content": (
                "You are a precise document assistant. "
                "You will be given context chunks extracted from a document. "
                "Answer the user's question using ONLY information found in these chunks. "
                "If the answer is not clearly stated in the chunks, say exactly: "
                "'I could not find a clear answer in the provided document.' "
                "Do NOT repeat yourself. "
                "Do NOT make up information. "
                "Keep your answer concise — maximum 5 sentences unless more detail is asked."
            ),
        },
        {
            "role"   : "user",
            "content": (
                f"Document chunks:\n\n{context}"
                f"\n\nQuestion: {question}"
                f"\n\nAnswer based only on the chunks above:"
            ),
        },
    ]

    # ── Step 5: Call Groq LLM ─────────────────────────────────
    t2 = time.perf_counter()
    try:
        from groq import Groq
        client   = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model       = settings.GROQ_LLM_MODEL,
            messages    = messages,
            temperature = 0.2,
            max_tokens  = 1024,
        )

    except Exception as e:
        raise LLMException(f"LLM call failed: {str(e)}")

    tracer.llm_ms            = int((time.perf_counter() - t2) * 1000)
    tracer.model_name        = settings.GROQ_LLM_MODEL
    tracer.prompt_tokens     = response.usage.prompt_tokens
    tracer.completion_tokens = response.usage.completion_tokens
    tracer.total_cost_usd    = calculate_cost(
        model             = settings.GROQ_LLM_MODEL,
        prompt_tokens     = tracer.prompt_tokens,
        completion_tokens = tracer.completion_tokens,
    )

    answer  = response.choices[0].message.content
    sources = [
        {
            "doc_id": r.payload.get("doc_id", ""),
            "chunk" : r.payload.get("chunk", "")[:200],
            "score" : round(r.score, 4),
        }
        for r in results
    ]

    log.info("llm_response",
        model             = tracer.model_name,
        prompt_tokens     = tracer.prompt_tokens,
        completion_tokens = tracer.completion_tokens,
        cost              = format_cost(tracer.total_cost_usd),
        llm_ms            = tracer.llm_ms,
        total_ms          = tracer.total_ms,
    )

    # ── Step 6: Save trace to DB ──────────────────────────────
    await tracer.save(db)

    # ── Step 7: Cache result for 1 hour ──────────────────────
    result = {
        "answer" : answer,
        "sources": sources,
        "meta"   : {
            "trace_id"         : tracer.trace_id,
            "cache_hit"        : False,
            "model"            : tracer.model_name,
            "prompt_tokens"    : tracer.prompt_tokens,
            "completion_tokens": tracer.completion_tokens,
            "total_tokens"     : tracer.total_tokens,
            "total_cost"       : format_cost(tracer.total_cost_usd),
            "embed_ms"         : tracer.embed_ms,
            "retrieve_ms"      : tracer.retrieve_ms,
            "llm_ms"           : tracer.llm_ms,
            "total_ms"         : tracer.total_ms,
        }
    }

    await redis.setex(cache_key, 3600, json.dumps(result))

    return result