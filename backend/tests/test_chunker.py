"""Tests for the semantic chunker."""

from src.rag.chunker import SemanticChunker


class TestSemanticChunker:
    """Tests for SemanticChunker."""

    def setup_method(self) -> None:
        self.chunker = SemanticChunker(max_tokens=50, overlap_tokens=10, chars_per_token=4)

    def test_chunk_short_text(self) -> None:
        text = "Hello world"
        chunks = self.chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world"
        assert chunks[0].index == 0

    def test_chunk_empty_text(self) -> None:
        chunks = self.chunker.chunk("")
        assert chunks == []

    def test_chunk_whitespace_only(self) -> None:
        chunks = self.chunker.chunk("   \n\n  ")
        assert chunks == []

    def test_chunk_long_text_splits(self) -> None:
        text = "A " * 500  # Much larger than max_chars
        chunks = self.chunker.chunk(text)
        assert len(chunks) > 1

    def test_chunk_paragraph_splitting(self) -> None:
        para1 = "First paragraph. " * 20
        para2 = "Second paragraph. " * 20
        text = f"{para1}\n\n{para2}"
        chunks = self.chunker.chunk(text)
        assert len(chunks) >= 2

    def test_chunk_indices_sequential(self) -> None:
        text = "A " * 500
        chunks = self.chunker.chunk(text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_chunk_has_start_end_chars(self) -> None:
        text = "Hello world"
        chunks = self.chunker.chunk(text)
        assert chunks[0].start_char >= 0
        assert chunks[0].end_char > chunks[0].start_char

    def test_max_chars_property(self) -> None:
        chunker = SemanticChunker(max_tokens=100, chars_per_token=4)
        assert chunker.max_chars == 400

    def test_overlap_chars_property(self) -> None:
        chunker = SemanticChunker(overlap_tokens=50, chars_per_token=4)
        assert chunker.overlap_chars == 200

    def test_default_parameters(self) -> None:
        chunker = SemanticChunker()
        assert chunker.max_chars == 512 * 4
        assert chunker.overlap_chars == 100 * 4

    def test_chunks_not_empty(self) -> None:
        text = "Hello world. This is a test document."
        chunks = self.chunker.chunk(text)
        for chunk in chunks:
            assert len(chunk.text.strip()) > 0

    def test_sentence_splitting(self) -> None:
        text = "First sentence. " * 50
        chunks = self.chunker.chunk(text)
        assert len(chunks) >= 2
