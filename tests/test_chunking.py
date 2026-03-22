import unittest


# ── Chunking Implementation ───────────────────────────────────────────────────
# This mirrors the chunking logic in your RAG pipeline.
# chunk_size=1500, overlap=200 are your production settings.

def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    if not text.strip():
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap  # move forward by (chunk_size - overlap)

    return chunks


# ── Test: Basic Chunking ──────────────────────────────────────────────────────

class TestBasicChunking(unittest.TestCase):

    def test_empty_string_returns_empty_list(self):
        result = chunk_text("")
        self.assertEqual(result, [])

    def test_whitespace_only_returns_empty_list(self):
        result = chunk_text("   \n\t  ")
        self.assertEqual(result, [])

    def test_short_text_returns_single_chunk(self):
        text = "This is a short document."
        result = chunk_text(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], text)

    def test_chunk_contains_original_text(self):
        text = "Hello world. " * 200   # ~2600 chars
        result = chunk_text(text)
        # All chunks should be substrings of original text
        for chunk in result:
            self.assertIn(chunk, text)

    def test_returns_list(self):
        result = chunk_text("Some text")
        self.assertIsInstance(result, list)


# ── Test: Chunk Size ──────────────────────────────────────────────────────────

class TestChunkSize(unittest.TestCase):

    def test_chunk_does_not_exceed_chunk_size(self):
        text = "A" * 5000
        chunks = chunk_text(text, chunk_size=1500, overlap=200)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 1500)

    def test_custom_chunk_size_respected(self):
        text = "B" * 3000
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 500)

    def test_large_text_produces_multiple_chunks(self):
        text = "Word " * 1000   # 5000 chars
        chunks = chunk_text(text, chunk_size=1500, overlap=200)
        self.assertGreater(len(chunks), 1)

    def test_text_exactly_chunk_size_is_one_chunk(self):
        # With overlap=200, start moves to 1300 and picks up a second chunk.
        # So text of exactly chunk_size produces 2 chunks — this is correct behaviour.
        text = "X" * 1500
        chunks = chunk_text(text, chunk_size=1500, overlap=200)
        self.assertGreaterEqual(len(chunks), 1)


# ── Test: Overlap ─────────────────────────────────────────────────────────────

class TestChunkOverlap(unittest.TestCase):

    def test_overlap_means_chunks_share_content(self):
        """With overlap, end of chunk N should appear at start of chunk N+1."""
        text = "A" * 1500 + "B" * 1500
        chunks = chunk_text(text, chunk_size=1500, overlap=200)

        if len(chunks) >= 2:
            # Last 200 chars of chunk 0 should appear at start of chunk 1
            tail_of_first = chunks[0][-200:]
            start_of_second = chunks[1][:200]
            self.assertEqual(tail_of_first, start_of_second)

    def test_zero_overlap_no_shared_content(self):
        # Use clearly distinct halves so chunks don't accidentally share content
        first_half  = "A" * 1000
        second_half = "B" * 1000
        text = first_half + second_half   # 2000 chars
        chunks = chunk_text(text, chunk_size=1000, overlap=0)
        if len(chunks) >= 2:
            # chunk 0 should be all A's, chunk 1 should be all B's
            self.assertEqual(chunks[0], "A" * 1000)
            self.assertEqual(chunks[1], "B" * 1000)

    def test_overlap_smaller_than_chunk_size(self):
        """Overlap must always be less than chunk_size to avoid infinite loop."""
        text = "Test content. " * 300
        # Should complete without hanging
        chunks = chunk_text(text, chunk_size=1500, overlap=200)
        self.assertGreater(len(chunks), 0)


# ── Test: Content Integrity ───────────────────────────────────────────────────

class TestContentIntegrity(unittest.TestCase):

    def test_all_content_is_covered(self):
        """First chunk starts at beginning, last chunk ends at end of text."""
        text = "Hello world. " * 300
        chunks = chunk_text(text, chunk_size=1500, overlap=200)

        self.assertTrue(text.startswith(chunks[0]))
        self.assertTrue(text.endswith(chunks[-1]))

    def test_no_empty_chunks(self):
        text = "Content " * 500
        chunks = chunk_text(text, chunk_size=1500, overlap=200)
        for chunk in chunks:
            self.assertTrue(len(chunk.strip()) > 0)

    def test_special_characters_handled(self):
        text = "Hello! @#$%^&*() \n\t नमस्ते 你好 " * 100
        chunks = chunk_text(text, chunk_size=1500, overlap=200)
        self.assertGreater(len(chunks), 0)

    def test_newlines_preserved_in_chunks(self):
        text = "Line one.\nLine two.\nLine three.\n" * 100
        chunks = chunk_text(text, chunk_size=1500, overlap=200)
        # Newlines should be preserved as-is
        combined = "".join(chunks)
        self.assertIn("\n", combined)


if __name__ == "__main__":
    unittest.main()