import pytest
from app.services.vector_store import VectorStore
from app.services.embeddings import EmbeddingService
from app.models.document import DocumentChunk, DocumentMetadata

@pytest.mark.asyncio
async def test_vector_store_indexing_and_similarity(tmp_path):
    test_storage = str(tmp_path / "test_vectors.json")
    vstore = VectorStore(storage_file=test_storage)
    
    meta = DocumentMetadata(
        doc_id="doc_sla",
        filename="cloud_sla.txt",
        file_type="text/plain",
        file_size_bytes=500,
        total_chunks=2,
        uploaded_at="2026-10-07T00:00:00Z",
        page_count=1
    )
    
    chunks = [
        DocumentChunk(
            chunk_id="doc_sla_0",
            doc_id="doc_sla",
            filename="cloud_sla.txt",
            page_number=1,
            chunk_index=0,
            text="Service Level Agreement guarantees 99.95% uptime for production database clusters.",
            char_count=84
        ),
        DocumentChunk(
            chunk_id="doc_sla_1",
            doc_id="doc_sla",
            filename="cloud_sla.txt",
            page_number=1,
            chunk_index=1,
            text="Priority 1 incidents require a response time of 15 minutes by engineering on-call.",
            char_count=82
        )
    ]
    
    await vstore.add_document(meta, chunks)
    assert vstore.total_vectors() == 2
    assert len(vstore.list_documents()) == 1

    # Search for uptime guarantee
    results = await vstore.search("uptime commitment percentage", top_k=2, min_similarity=0.2)
    assert len(results) > 0
    top_result = results[0]
    assert "99.95%" in top_result.chunk.text
    assert top_result.similarity_score > 0.3

    # Delete document
    deleted = vstore.delete_document("doc_sla")
    assert deleted is True
    assert vstore.total_vectors() == 0
    assert len(vstore.list_documents()) == 0

@pytest.mark.asyncio
async def test_vector_store_filter_by_doc_id(tmp_path):
    test_storage = str(tmp_path / "test_filter_vectors.json")
    vstore = VectorStore(storage_file=test_storage)
    
    meta1 = DocumentMetadata(
        doc_id="doc_1", filename="doc1.txt", file_type="text/plain",
        file_size_bytes=100, total_chunks=1, uploaded_at="2026-10-07", page_count=1
    )
    chunks1 = [DocumentChunk(chunk_id="c1", doc_id="doc_1", filename="doc1.txt", page_number=1, chunk_index=0, text="Alpha protocol security guidelines.", char_count=36)]
    
    meta2 = DocumentMetadata(
        doc_id="doc_2", filename="doc2.txt", file_type="text/plain",
        file_size_bytes=100, total_chunks=1, uploaded_at="2026-10-07", page_count=1
    )
    chunks2 = [DocumentChunk(chunk_id="c2", doc_id="doc_2", filename="doc2.txt", page_number=1, chunk_index=0, text="Beta protocol security guidelines.", char_count=35)]
    
    await vstore.add_document(meta1, chunks1)
    await vstore.add_document(meta2, chunks2)
    
    # Filter search to doc_2 only
    results = await vstore.search("security guidelines", top_k=5, filter_doc_ids=["doc_2"], min_similarity=0.1)
    assert len(results) == 1
    assert results[0].chunk.doc_id == "doc_2"
