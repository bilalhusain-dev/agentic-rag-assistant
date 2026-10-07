import os
import json
from typing import List, Dict, Optional, Any
from app.models.document import DocumentChunk, DocumentMetadata, SearchResult
from app.services.embeddings import EmbeddingService
from app.config import settings

class VectorStore:
    def __init__(self, storage_file: Optional[str] = None):
        self.storage_file = storage_file or settings.VECTOR_INDEX_FILE
        self.chunks: Dict[str, DocumentChunk] = {}
        self.vectors: Dict[str, List[float]] = {}
        self.documents: Dict[str, DocumentMetadata] = {}
        self._load()

    def _ensure_dir(self):
        folder = os.path.dirname(self.storage_file)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

    def _save(self):
        try:
            self._ensure_dir()
            data = {
                "documents": {doc_id: doc.model_dump() for doc_id, doc in self.documents.items()},
                "chunks": {chunk_id: chunk.model_dump() for chunk_id, chunk in self.chunks.items()},
                "vectors": self.vectors
            }
            temp_file = f"{self.storage_file}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(temp_file, self.storage_file)
        except Exception as e:
            # Non-blocking persistence warning
            logging.getLogger(__name__).warning("VectorStore persistence failed: %s", str(e))

    def _load(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.documents = {
                    doc_id: DocumentMetadata(**doc_data)
                    for doc_id, doc_data in data.get("documents", {}).items()
                }
                self.chunks = {
                    chunk_id: DocumentChunk(**chunk_data)
                    for chunk_id, chunk_data in data.get("chunks", {}).items()
                }
                self.vectors = data.get("vectors", {})
            except Exception as e:
                print(f"[VectorStore] Load Warning: {e}")

    async def add_document(
        self,
        metadata: DocumentMetadata,
        chunks: List[DocumentChunk]
    ) -> int:
        """Indexes document chunks and computes their vector embeddings."""
        self.documents[metadata.doc_id] = metadata

        texts = [c.text for c in chunks]
        embeddings = await EmbeddingService.get_batch_embeddings(texts)

        for chunk, vec in zip(chunks, embeddings):
            self.chunks[chunk.chunk_id] = chunk
            self.vectors[chunk.chunk_id] = vec

        self._save()
        return len(chunks)

    def delete_document(self, doc_id: str) -> bool:
        """Purges document metadata, all associated chunks, and vector embeddings."""
        if doc_id not in self.documents:
            return False

        del self.documents[doc_id]
        
        # Remove matching chunks & vectors
        chunk_ids_to_remove = [c_id for c_id, c in self.chunks.items() if c.doc_id == doc_id]
        for c_id in chunk_ids_to_remove:
            self.chunks.pop(c_id, None)
            self.vectors.pop(c_id, None)

        self._save()
        return True

    def list_documents(self) -> List[DocumentMetadata]:
        return list(self.documents.values())

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        return self.documents.get(doc_id)

    async def search(
        self,
        query: str,
        top_k: int = 4,
        min_similarity: float = 0.55,
        filter_doc_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Performs semantic vector search with Cosine Similarity,
        applying threshold gating and optional document filtering.
        """
        if not self.chunks or not self.vectors:
            return []

        query_vec = await EmbeddingService.get_embedding(query)
        scored_results: List[SearchResult] = []

        for chunk_id, chunk_vec in self.vectors.items():
            chunk = self.chunks.get(chunk_id)
            if not chunk:
                continue

            if filter_doc_ids and chunk.doc_id not in filter_doc_ids:
                continue

            sim = EmbeddingService.cosine_similarity(query_vec, chunk_vec)
            if sim >= min_similarity:
                scored_results.append(SearchResult(
                    chunk=chunk,
                    similarity_score=round(sim, 4)
                ))

        # Sort descending by similarity score
        scored_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored_results[:top_k]

    def total_vectors(self) -> int:
        return len(self.vectors)

# Global singleton store
vector_store = VectorStore()
