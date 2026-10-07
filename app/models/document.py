from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    text: str
    chunk_index: int
    page_number: Optional[int] = 1
    char_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    total_chunks: int
    uploaded_at: str
    page_count: int = 1

class Citation(BaseModel):
    doc_id: str
    filename: str
    page_number: int
    chunk_index: int
    score: float
    excerpt: str

class SearchResult(BaseModel):
    chunk: DocumentChunk
    similarity_score: float
