import pytest
import pytest_asyncio
from app.services.vector_store import vector_store
from app.services.rag_engine import RAGEngine
from app.models.document import DocumentChunk, DocumentMetadata

@pytest_asyncio.fixture(autouse=True)
async def setup_test_index():
    # Setup test vectors in global vector store
    meta = DocumentMetadata(
        doc_id="doc_policy_fixture",
        filename="company_policy.txt",
        file_type="text/plain",
        file_size_bytes=400,
        total_chunks=1,
        uploaded_at="2026-10-07T00:00:00Z",
        page_count=1
    )
    chunk = DocumentChunk(
        chunk_id="chunk_fixture_1",
        doc_id="doc_policy_fixture",
        filename="company_policy.txt",
        page_number=1,
        chunk_index=0,
        text="The mandatory password length is 14 characters. Sessions timeout after 15 minutes of inactivity.",
        char_count=98
    )
    await vector_store.add_document(meta, [chunk])
    yield
    vector_store.delete_document("doc_policy_fixture")

@pytest.mark.asyncio
async def test_grounded_answer_with_citations():
    query = "What is the mandatory password length and session timeout?"
    resp = await RAGEngine.query(query=query, top_k=2)
    
    assert resp.grounded is True
    assert len(resp.citations) > 0
    assert "14 characters" in resp.answer or "password" in resp.answer
    assert resp.citations[0].filename == "company_policy.txt"

@pytest.mark.asyncio
async def test_hallucination_prevention_on_unrelated_query():
    # Query completely absent from the indexed documents
    unrelated_query = "What is the secret recipe for baking artisanal sourdough bread?"
    resp = await RAGEngine.query(query=unrelated_query, top_k=2)
    
    # Must reject without hallucinating
    assert resp.grounded is False
    assert len(resp.citations) == 0
    assert "do not contain" in resp.answer.lower() or "not sufficient" in resp.answer.lower() or "sufficient" in resp.answer.lower()
