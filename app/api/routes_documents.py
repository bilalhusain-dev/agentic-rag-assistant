import os
import uuid
import time
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.models.document import DocumentMetadata
from app.services.document_parser import DocumentParser
from app.services.chunker import RecursiveSemanticChunker
from app.services.vector_store import vector_store
from app.config import settings

logger = logging.getLogger(__name__)

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

    # Security: Sanitize filename to prevent directory traversal
    clean_filename = os.path.basename(file.filename.replace("\\", "/")).strip()
    if not clean_filename or clean_filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename format.")

    # Security: Strict extension whitelisting
    ext = os.path.splitext(clean_filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Security: Read with size limit guarding against memory exhaustion
    contents = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB."
        )

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"

    try:
        pages = DocumentParser.parse_file(contents, clean_filename)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("Failed to parse document '%s': %s", clean_filename, str(e), exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to parse document: {str(e)}")

    if not pages:
        raise HTTPException(status_code=422, detail="No readable text extracted from document.")

    chunks = chunker.chunk_document(doc_id, clean_filename, pages)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document could not be partitioned into valid chunks.")

    metadata = DocumentMetadata(
        doc_id=doc_id,
        filename=clean_filename,
        file_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(contents),
        total_chunks=len(chunks),
        uploaded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        page_count=len(pages)
    )

    await vector_store.add_document(metadata, chunks)
    logger.info("Successfully ingested document '%s' (doc_id=%s, chunks=%d)", clean_filename, doc_id, len(chunks))
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
