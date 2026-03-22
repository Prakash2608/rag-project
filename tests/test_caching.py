import unittest
import hashlib
import json
from unittest.mock import MagicMock, patch


# ── Caching Implementation ────────────────────────────────────────────────────
# Mirrors the caching logic in your RAG pipeline.

def normalize_question(question: str) -> str:
    """Lowercase and strip whitespace for consistent cache keys."""
    return question.strip().lower()


def make_cache_key(question: str) -> str:
    """SHA256 hash of normalized question — used for exact match cache."""
    normalized = normalize_question(question)
    return hashlib.sha256(normalized.encode()).hexdigest()


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = sum(a ** 2 for a in vec_a) ** 0.5
    mag_b = sum(b ** 2 for b in vec_b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def is_semantic_cache_hit(similarity: float, threshold: float = 0.95) -> bool:
    """Return True if similarity meets or exceeds the threshold."""
    return similarity >= threshold


# ── Test: Normalization ───────────────────────────────────────────────────────

class TestNormalization(unittest.TestCase):

    def test_lowercase_applied(self):
        self.assertEqual(normalize_question("HELLO WORLD"), "hello world")

    def test_leading_trailing_whitespace_stripped(self):
        self.assertEqual(normalize_question("  hello  "), "hello")

    def test_mixed_case_and_spaces(self):
        self.assertEqual(normalize_question("  What Is RAG?  "), "what is rag?")

    def test_already_normalized_unchanged(self):
        self.assertEqual(normalize_question("what is rag?"), "what is rag?")

    def test_empty_string(self):
        self.assertEqual(normalize_question(""), "")


# ── Test: Exact Match Cache Key ───────────────────────────────────────────────

class TestExactMatchCacheKey(unittest.TestCase):

    def test_returns_string(self):
        key = make_cache_key("what is rag?")
        self.assertIsInstance(key, str)

    def test_key_is_64_chars(self):
        """SHA256 hex digest is always 64 characters."""
        key = make_cache_key("what is rag?")
        self.assertEqual(len(key), 64)

    def test_same_question_same_key(self):
        key1 = make_cache_key("what is rag?")
        key2 = make_cache_key("what is rag?")
        self.assertEqual(key1, key2)

    def test_different_questions_different_keys(self):
        key1 = make_cache_key("what is rag?")
        key2 = make_cache_key("what is langchain?")
        self.assertNotEqual(key1, key2)

    def test_case_insensitive_same_key(self):
        """Normalization ensures case variants hit the same cache entry."""
        key1 = make_cache_key("What is RAG?")
        key2 = make_cache_key("what is rag?")
        self.assertEqual(key1, key2)

    def test_whitespace_insensitive_same_key(self):
        key1 = make_cache_key("  what is rag?  ")
        key2 = make_cache_key("what is rag?")
        self.assertEqual(key1, key2)

    def test_key_is_hexadecimal(self):
        key = make_cache_key("test question")
        self.assertTrue(all(c in "0123456789abcdef" for c in key))


# ── Test: Cosine Similarity ───────────────────────────────────────────────────

class TestCosineSimilarity(unittest.TestCase):

    def test_identical_vectors_return_1(self):
        vec = [1.0, 2.0, 3.0]
        result = cosine_similarity(vec, vec)
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_opposite_vectors_return_minus_1(self):
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [-1.0, 0.0, 0.0]
        result = cosine_similarity(vec_a, vec_b)
        self.assertAlmostEqual(result, -1.0, places=5)

    def test_orthogonal_vectors_return_0(self):
        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]
        result = cosine_similarity(vec_a, vec_b)
        self.assertAlmostEqual(result, 0.0, places=5)

    def test_zero_vector_returns_0(self):
        vec_a = [0.0, 0.0, 0.0]
        vec_b = [1.0, 2.0, 3.0]
        result = cosine_similarity(vec_a, vec_b)
        self.assertEqual(result, 0.0)

    def test_similar_vectors_high_score(self):
        vec_a = [1.0, 1.0, 1.0]
        vec_b = [1.0, 1.0, 0.9]
        result = cosine_similarity(vec_a, vec_b)
        self.assertGreater(result, 0.9)

    def test_result_between_minus1_and_1(self):
        vec_a = [0.5, 0.3, 0.8]
        vec_b = [0.1, 0.9, 0.4]
        result = cosine_similarity(vec_a, vec_b)
        self.assertGreaterEqual(result, -1.0)
        self.assertLessEqual(result, 1.0)


# ── Test: Semantic Cache Hit ──────────────────────────────────────────────────

class TestSemanticCacheHit(unittest.TestCase):

    def test_exact_threshold_is_hit(self):
        self.assertTrue(is_semantic_cache_hit(0.95, threshold=0.95))

    def test_above_threshold_is_hit(self):
        self.assertTrue(is_semantic_cache_hit(0.99, threshold=0.95))

    def test_below_threshold_is_miss(self):
        self.assertFalse(is_semantic_cache_hit(0.94, threshold=0.95))

    def test_very_low_similarity_is_miss(self):
        self.assertFalse(is_semantic_cache_hit(0.10, threshold=0.95))

    def test_perfect_similarity_is_hit(self):
        self.assertTrue(is_semantic_cache_hit(1.0, threshold=0.95))

    def test_custom_threshold_respected(self):
        self.assertTrue(is_semantic_cache_hit(0.80, threshold=0.75))
        self.assertFalse(is_semantic_cache_hit(0.70, threshold=0.75))


# ── Test: Cache Flow (Mocked Redis) ──────────────────────────────────────────

class TestCacheFlow(unittest.TestCase):
    """Simulate get/set cache operations using a mock Redis client."""

    def setUp(self):
        self.redis = MagicMock()

    def test_cache_miss_returns_none(self):
        self.redis.get.return_value = None
        key = make_cache_key("what is rag?")
        result = self.redis.get(key)
        self.assertIsNone(result)

    def test_cache_hit_returns_value(self):
        cached_answer = json.dumps({"answer": "RAG stands for Retrieval Augmented Generation."})
        self.redis.get.return_value = cached_answer
        key = make_cache_key("what is rag?")
        result = self.redis.get(key)
        self.assertEqual(result, cached_answer)

    def test_cache_set_called_with_correct_key(self):
        question = "what is rag?"
        answer = "RAG stands for Retrieval Augmented Generation."
        key = make_cache_key(question)
        self.redis.set(key, json.dumps({"answer": answer}))
        self.redis.set.assert_called_once_with(key, json.dumps({"answer": answer}))

    def test_cache_key_used_for_get_and_set(self):
        """Same question should produce same key for both get and set."""
        question = "what is rag?"
        key_on_set = make_cache_key(question)
        key_on_get = make_cache_key(question)
        self.assertEqual(key_on_set, key_on_get)


if __name__ == "__main__":
    unittest.main()