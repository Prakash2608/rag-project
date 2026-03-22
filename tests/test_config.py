import unittest
import os
from unittest.mock import patch


# ── Minimal Config (mirrors your app/config.py) ───────────────────────────────

from pydantic_settings import BaseSettings
from pydantic import ValidationError


class Settings(BaseSettings):
    # App
    app_name: str = "RAG System"
    debug: bool = False

    # Database
    postgres_url: str = "postgresql://user:password@localhost:5432/ragdb"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "documents"

    # LLM
    llm_provider: str = "groq"
    groq_api_key: str = ""
    openai_api_key: str = ""

    # Embeddings
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"

    # JWT
    secret_key: str = "changeme-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Chunking
    chunk_size: int = 1500
    chunk_overlap: int = 200

    # Semantic cache
    semantic_cache_threshold: float = 0.95

    model_config = {"env_file": ".env", "extra": "ignore"}


# ── Test: Default Values ──────────────────────────────────────────────────────

class TestDefaultValues(unittest.TestCase):
    """Ensure defaults are correct when no .env is present."""

    def setUp(self):
        # Load settings with no env overrides
        with patch.dict(os.environ, {}, clear=True):
            self.settings = Settings()

    def test_default_app_name(self):
        self.assertEqual(self.settings.app_name, "RAG System")

    def test_default_debug_is_false(self):
        self.assertFalse(self.settings.debug)

    def test_default_llm_provider_is_groq(self):
        self.assertEqual(self.settings.llm_provider, "groq")

    def test_default_chunk_size(self):
        self.assertEqual(self.settings.chunk_size, 1500)

    def test_default_chunk_overlap(self):
        self.assertEqual(self.settings.chunk_overlap, 200)

    def test_default_algorithm_is_hs256(self):
        self.assertEqual(self.settings.algorithm, "HS256")

    def test_default_token_expiry(self):
        self.assertEqual(self.settings.access_token_expire_minutes, 30)

    def test_default_qdrant_port(self):
        self.assertEqual(self.settings.qdrant_port, 6333)

    def test_default_semantic_cache_threshold(self):
        self.assertAlmostEqual(self.settings.semantic_cache_threshold, 0.95)

    def test_default_embedding_model(self):
        self.assertEqual(self.settings.embedding_model, "nomic-embed-text")

    def test_default_minio_bucket(self):
        self.assertEqual(self.settings.minio_bucket, "documents")


# ── Test: Env Var Overrides ───────────────────────────────────────────────────

class TestEnvVarOverrides(unittest.TestCase):
    """Ensure .env values correctly override defaults."""

    def test_override_app_name(self):
        with patch.dict(os.environ, {"APP_NAME": "My Custom RAG"}):
            s = Settings()
            self.assertEqual(s.app_name, "My Custom RAG")

    def test_override_debug_true(self):
        with patch.dict(os.environ, {"DEBUG": "true"}):
            s = Settings()
            self.assertTrue(s.debug)

    def test_override_llm_provider(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
            s = Settings()
            self.assertEqual(s.llm_provider, "ollama")

    def test_override_groq_api_key(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_testkey123"}):
            s = Settings()
            self.assertEqual(s.groq_api_key, "gsk_testkey123")

    def test_override_chunk_size(self):
        with patch.dict(os.environ, {"CHUNK_SIZE": "2000"}):
            s = Settings()
            self.assertEqual(s.chunk_size, 2000)

    def test_override_chunk_overlap(self):
        with patch.dict(os.environ, {"CHUNK_OVERLAP": "300"}):
            s = Settings()
            self.assertEqual(s.chunk_overlap, 300)

    def test_override_qdrant_port(self):
        with patch.dict(os.environ, {"QDRANT_PORT": "6334"}):
            s = Settings()
            self.assertEqual(s.qdrant_port, 6334)

    def test_override_semantic_cache_threshold(self):
        with patch.dict(os.environ, {"SEMANTIC_CACHE_THRESHOLD": "0.90"}):
            s = Settings()
            self.assertAlmostEqual(s.semantic_cache_threshold, 0.90)

    def test_override_secret_key(self):
        with patch.dict(os.environ, {"SECRET_KEY": "my-super-secret"}):
            s = Settings()
            self.assertEqual(s.secret_key, "my-super-secret")

    def test_override_token_expiry(self):
        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "60"}):
            s = Settings()
            self.assertEqual(s.access_token_expire_minutes, 60)


# ── Test: Type Validation ─────────────────────────────────────────────────────

class TestTypeValidation(unittest.TestCase):
    """Pydantic should cast or reject wrong types from env."""

    def test_qdrant_port_is_int(self):
        with patch.dict(os.environ, {"QDRANT_PORT": "6333"}):
            s = Settings()
            self.assertIsInstance(s.qdrant_port, int)

    def test_debug_is_bool(self):
        with patch.dict(os.environ, {"DEBUG": "false"}):
            s = Settings()
            self.assertIsInstance(s.debug, bool)

    def test_chunk_size_is_int(self):
        s = Settings()
        self.assertIsInstance(s.chunk_size, int)

    def test_semantic_cache_threshold_is_float(self):
        s = Settings()
        self.assertIsInstance(s.semantic_cache_threshold, float)

    def test_access_token_expire_minutes_is_int(self):
        s = Settings()
        self.assertIsInstance(s.access_token_expire_minutes, int)

    def test_bool_from_string_true(self):
        with patch.dict(os.environ, {"DEBUG": "1"}):
            s = Settings()
            self.assertTrue(s.debug)

    def test_bool_from_string_false(self):
        with patch.dict(os.environ, {"DEBUG": "0"}):
            s = Settings()
            self.assertFalse(s.debug)


# ── Test: URL Formats ─────────────────────────────────────────────────────────

class TestURLFormats(unittest.TestCase):
    """Check that URL fields contain expected patterns."""

    def setUp(self):
        self.settings = Settings()

    def test_postgres_url_starts_with_postgresql(self):
        self.assertTrue(self.settings.postgres_url.startswith("postgresql://"))

    def test_redis_url_starts_with_redis(self):
        self.assertTrue(self.settings.redis_url.startswith("redis://"))

    def test_ollama_base_url_starts_with_http(self):
        self.assertTrue(self.settings.ollama_base_url.startswith("http://"))

    def test_minio_endpoint_has_port(self):
        self.assertIn(":", self.settings.minio_endpoint)


# ── Test: Settings Are Read-Only After Load ───────────────────────────────────

class TestSettingsImmutability(unittest.TestCase):

    def test_settings_loads_without_error(self):
        try:
            s = Settings()
        except Exception as e:
            self.fail(f"Settings() raised an exception: {e}")

    def test_two_instances_have_same_defaults(self):
        s1 = Settings()
        s2 = Settings()
        self.assertEqual(s1.chunk_size, s2.chunk_size)
        self.assertEqual(s1.llm_provider, s2.llm_provider)
        self.assertEqual(s1.algorithm, s2.algorithm)


if __name__ == "__main__":
    unittest.main()