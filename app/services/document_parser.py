import re
import os
from typing import List, Dict, Any

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

class DocumentParser:
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Cleans and normalizes extracted text.
        Removes orphan hyphenation, non-printable characters, redundant whitespace.
        """
        if not text:
            return ""
        
        # Remove non-printable control characters (except standard whitespace)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # De-hyphenate line breaks (e.g., "en- \nterprise" -> "enterprise")
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Normalize redundant blank lines (max 2 consecutive newlines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Collapse multiple spaces or tabs into a single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()

    @classmethod
    def parse_file(cls, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Extracts clean text and page numbers from file bytes.
        Returns a list of dicts: [{"page_number": int, "text": str}]
        """
        if not file_bytes:
            raise ValueError("Uploaded document bytes are empty.")

        ext = os.path.splitext(filename)[1].lower()
        pages: List[Dict[str, Any]] = []

        if ext == ".pdf":
            if not PYMUPDF_AVAILABLE:
                raise RuntimeError("PyMuPDF (fitz) is not installed for PDF parsing.")
            
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                raw_text = page.get_text("text")
                cleaned = cls.clean_text(raw_text)
                if cleaned:
                    pages.append({
                        "page_number": page_idx + 1,
                        "text": cleaned
                    })
            doc.close()

        elif ext in [".txt", ".md", ".markdown", ".json", ".csv"]:
            try:
                raw_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raw_text = file_bytes.decode("latin-1", errors="replace")
            
            cleaned = cls.clean_text(raw_text)
            if cleaned:
                pages.append({
                    "page_number": 1,
                    "text": cleaned
                })
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .pdf, .txt, .md, .markdown, .json, .csv")

        return pages
