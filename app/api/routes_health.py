import time
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.vector_store import vector_store
from app.config import settings

router = APIRouter(tags=["Health & Telemetry"])
START_TIME = time.time()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Returns system operational health, vector count, and uptime stats."""
    uptime = time.time() - START_TIME
    mode = "OpenAI API (Cloud)" if settings.OPENAI_API_KEY else "Deterministic Local 384d (Offline/Zero-Cost)"
    
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        uptime_seconds=round(uptime, 2),
        indexed_documents_count=len(vector_store.list_documents()),
        total_vectors_count=vector_store.total_vectors(),
        embedding_mode=mode
    )
