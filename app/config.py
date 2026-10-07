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
    
    # Storage
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./data_storage")
    VECTOR_INDEX_FILE: str = os.path.join(STORAGE_DIR, "vector_index.json")

settings = Settings()
