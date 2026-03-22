# RAG Project

A production-grade Retrieval-Augmented Generation (RAG) system built from scratch.
Designed for local development on Windows with deployment to RunPod.

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Database | PostgreSQL (asyncpg) |
| Vector DB | Qdrant |
| Cache / Broker | Redis |
| Object Storage | MinIO |
| LLM | Groq (switchable to Ollama / OpenAI) |
| Embeddings | Ollama `nomic-embed-text` |
| Background Tasks | Celery |
| Logging | Structlog |
| Config | Pydantic Settings |

---

## Project Structure

```
rag_project/
├── app/
│   ├── main.py               # FastAPI app with lifespan context
│   ├── config.py             # Pydantic settings from .env
│   ├── database.py           # PostgreSQL + SQLAlchemy setup
│   ├── models.py             # DB models (users, documents, llm_traces)
│   ├── auth.py               # JWT authentication
│   ├── routers/              # API endpoints (upload, query, users)
│   ├── llm/                  # LLM abstraction (Groq, Ollama, OpenAI)
│   ├── core/
│   │   └── metrics.py        # Query and document metrics
│   └── workers/
│       ├── celery_app.py     # Celery configuration
│       └── tasks.py          # Background tasks (process_document)
├── tests/
│   ├── test_auth.py          # JWT + password hashing (11 tests)
│   ├── test_chunking.py      # Text splitting logic (16 tests)
│   ├── test_caching.py       # Exact match + semantic cache (28 tests)
│   ├── test_llm_client.py    # LLM provider abstraction (28 tests)
│   └── test_config.py        # Config loading + validation (33 tests)
├── .env.example              # Environment variables template
├── docker-compose.yml        # Infrastructure services
└── requirements.txt          # Python dependencies
```

---

## Quick Start

### 1. Clone and set up environment

```bash
git clone <your-repo-url>
cd rag_project

py -3.11 -m venv rag_env
rag_env\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
# Edit .env and fill in your values (GROQ_API_KEY, SECRET_KEY, etc.)
```

### 3. Start infrastructure

```bash
docker compose up -d
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

### 5. Start Celery worker

```bash
# In a separate terminal (--pool=solo required on Windows)
py -3.11 -m celery -A app.workers.celery_app worker --pool=solo --loglevel=info
```

### 6. Open API docs

```
http://localhost:8000/docs
```

---

## How It Works

```
User uploads PDF
      ↓
FastAPI saves to MinIO (S3_BUCKET) + Postgres
      ↓
Celery task triggered → chunks text (1500 chars, 200 overlap)
      ↓
Ollama embeds chunks (OLLAMA_EMBED_MODEL) → stored in Qdrant
      ↓
User asks a question
      ↓
Check exact cache (SHA256) → return if hit
      ↓
Check semantic cache (cosine similarity ≥ 0.95) → return if hit
      ↓
Embed question → retrieve chunks from Qdrant (score ≥ 0.55)
      ↓
Send chunks + question to Groq LLM (GROQ_LLM_MODEL)
      ↓
Return answer + store in cache
```

---

## Switching LLM Provider

Change `LLM_PROVIDER` in your `.env`:

```env
LLM_PROVIDER=groq      # default
LLM_PROVIDER=ollama
LLM_PROVIDER=openai
```

No code changes needed.

---

## Environment Variables

| Variable | Description |
|---|---|
| `APP_ENV` | `development` or `production` |
| `SECRET_KEY` | Long random string for JWT signing |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `S3_ENDPOINT` | MinIO endpoint URL |
| `S3_ACCESS_KEY` | MinIO access key |
| `S3_SECRET_KEY` | MinIO secret key |
| `S3_BUCKET` | MinIO bucket name |
| `QDRANT_HOST` | Qdrant host |
| `QDRANT_PORT` | Qdrant port (default 6333) |
| `LLM_PROVIDER` | `groq`, `ollama`, or `openai` |
| `GROQ_API_KEY` | Groq API key |
| `GROQ_LLM_MODEL` | Groq model name |
| `OLLAMA_BASE_URL` | Ollama server URL |
| `OLLAMA_LLM_MODEL` | Ollama LLM model |
| `OLLAMA_EMBED_MODEL` | Ollama embedding model |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_LLM_MODEL` | OpenAI model name |
| `SENTRY_DSN` | Sentry DSN (optional) |

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Individual test files
pytest tests/test_auth.py -v
pytest tests/test_chunking.py -v
pytest tests/test_caching.py -v
pytest tests/test_llm_client.py -v
pytest tests/test_config.py -v
```

**Total: 116 tests, all passing.**

---

## Deployment (RunPod)

1. Push your code to a Git repo
2. Set all `.env` values as RunPod environment variables
3. Start infrastructure via `docker compose up -d`
4. Run FastAPI and Celery as separate pods or processes

---

## Key Design Decisions

- **Exact + Semantic caching** — reduces LLM calls for repeated or similar questions
- **Score threshold on retrieval** — `score_threshold=0.55` filters out irrelevant chunks
- **Chunk size 1500 / overlap 200** — tuned for better context preservation
- **`--pool=solo`** — required for Celery on Windows due to multiprocessing limitations
- **`bcrypt==4.0.1`** — avoids the 72-byte password limit bug on Windows
- **asyncpg** — async PostgreSQL driver for non-blocking database queries
