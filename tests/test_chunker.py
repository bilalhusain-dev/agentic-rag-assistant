from app.services.chunker import RecursiveSemanticChunker

def test_recursive_chunker_basic():
    chunker = RecursiveSemanticChunker(chunk_size=150, chunk_overlap=30)
    pages = [
        {
            "page_number": 1,
            "text": (
                "Paragraph one discusses database architecture and master-replica replication latency.\n\n"
                "Paragraph two discusses Redis caching strategies and LRU cache invalidation policies.\n\n"
                "Paragraph three discusses API gateway rate limiting, token buckets, and ingress firewalls."
            )
        }
    ]
    chunks = chunker.chunk_document("doc_test_1", "arch.txt", pages)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.doc_id == "doc_test_1"
        assert chunk.filename == "arch.txt"
        assert chunk.char_count > 0
        assert len(chunk.text) > 0

def test_recursive_chunker_overlap():
    chunker = RecursiveSemanticChunker(chunk_size=100, chunk_overlap=25)
    pages = [{"page_number": 1, "text": "A" * 80 + " " + "B" * 80 + " " + "C" * 80}]
    chunks = chunker.chunk_document("doc_test_2", "long.txt", pages)
    assert len(chunks) > 1
    # Check that chunks retain page number and sequential indices
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.page_number == 1

def test_empty_document_produces_no_chunks():
    chunker = RecursiveSemanticChunker()
    chunks = chunker.chunk_document("doc_empty", "empty.txt", [{"page_number": 1, "text": "   "}])
    assert len(chunks) == 0
