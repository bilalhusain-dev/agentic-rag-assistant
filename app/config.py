import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    APP_NAME: str = "NexusRAG Enterprise Assistant"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # LLM & Embedding Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    
    # RAG Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    SIMILARITY_THRESHOLD: float = 0.35
    TOP_K_RESULTS: int = 4
    
    # Security & Operational Limits
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25MB max file upload
    MAX_PDF_PAGES: int = 150                      # DoS mitigation against PDF bombs
    MAX_SESSION_CACHE: int = 1000                 # Session store eviction limit
    ALLOWED_EXTENSIONS: list = [".pdf", ".txt", ".md", ".markdown", ".json", ".csv"]
    ALLOWED_ORIGINS: list = ["*"]
    
    # Storage
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./data_storage")
    VECTOR_INDEX_FILE: str = os.path.join(STORAGE_DIR, "vector_index.json")

settings = Settings()
