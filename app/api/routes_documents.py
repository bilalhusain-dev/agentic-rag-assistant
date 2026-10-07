import uuid
import time
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.models.document import DocumentMetadata
from app.services.document_parser import DocumentParser
from app.services.chunker import RecursiveSemanticChunker
from app.services.vector_store import vector_store
from app.config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])
chunker = RecursiveSemanticChunker(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP
)

@router.post("/upload", response_model=DocumentMetadata, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """
    Ingests and parses uploaded document (PDF, TXT, MD),
    extracts clean text, generates recursive semantic chunks, and creates vector embeddings.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename must be provided.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"

    try:
        pages = DocumentParser.parse_file(contents, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse document: {str(e)}")

    if not pages:
        raise HTTPException(status_code=422, detail="No readable text extracted from document.")

    chunks = chunker.chunk_document(doc_id, file.filename, pages)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document could not be partitioned into valid chunks.")

    metadata = DocumentMetadata(
        doc_id=doc_id,
        filename=file.filename,
        file_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(contents),
        total_chunks=len(chunks),
        uploaded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        page_count=len(pages)
    )

    await vector_store.add_document(metadata, chunks)
    return metadata

@router.get("", response_model=List[DocumentMetadata])
async def list_documents():
    """Lists all indexed documents and chunk statistics."""
    return vector_store.list_documents()

@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(doc_id: str):
    """Deletes document metadata and purges all indexed vectors."""
    success = vector_store.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return {"success": True, "message": f"Document '{doc_id}' purged successfully."}
