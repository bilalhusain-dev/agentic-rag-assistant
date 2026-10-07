import uuid
from typing import List, Dict, Any
from app.models.document import DocumentChunk

class RecursiveSemanticChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """
        Recursively splits text into chunks under chunk_size respecting natural separators.
        """
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        if not separators:
            # Base case: split by character size
            chunks = []
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                c = text[i:i + self.chunk_size].strip()
                if c:
                    chunks.append(c)
            return chunks

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep == "":
            splits = list(text)
        else:
            splits = text.split(sep)

        good_chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for piece in splits:
            piece_len = len(piece) + (len(sep) if current_chunk else 0)

            if piece_len > self.chunk_size:
                # If current piece itself is larger than chunk_size, recursively subdivide it
                if current_chunk:
                    merged = sep.join(current_chunk).strip()
                    if merged:
                        good_chunks.append(merged)
                    current_chunk = []
                    current_len = 0
                
                sub_chunks = self._split_text(piece, remaining_seps)
                good_chunks.extend(sub_chunks)
            elif current_len + piece_len <= self.chunk_size:
                current_chunk.append(piece)
                current_len += piece_len
            else:
                merged = sep.join(current_chunk).strip()
                if merged:
                    good_chunks.append(merged)
                
                # Setup overlap from previous chunk if available
                current_chunk = [piece]
                current_len = len(piece)

        if current_chunk:
            merged = sep.join(current_chunk).strip()
            if merged:
                good_chunks.append(merged)

        return good_chunks

    def chunk_document(
        self,
        doc_id: str,
        filename: str,
        pages: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """
        Processes pages into indexed DocumentChunk objects with overlap and metadata.
        """
        all_chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            raw_text = page.get("text", "")
            if not raw_text:
                continue

            text_splits = self._split_text(raw_text, self.separators)

            for split_text in text_splits:
                if not split_text.strip():
                    continue

                chunk_id = f"{doc_id}_c{global_chunk_idx:04d}"
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    filename=filename,
                    text=split_text.strip(),
                    chunk_index=global_chunk_idx,
                    page_number=page_num,
                    char_count=len(split_text.strip()),
                    metadata={"source": filename, "page": page_num}
                )
                all_chunks.append(chunk)
                global_chunk_idx += 1

        return all_chunks
