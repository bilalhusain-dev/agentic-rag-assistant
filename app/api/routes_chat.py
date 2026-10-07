from fastapi import APIRouter
from app.models.schemas import QueryRequest, QueryResponse, ChatRequest, ChatResponse
from app.services.rag_engine import RAGEngine
from app.services.agent_router import AgentRouter

router = APIRouter(tags=["RAG & Chat"])

@router.post("/query", response_model=QueryResponse)
async def query_documents(req: QueryRequest):
    """
    Direct single-turn RAG search endpoint.
    Retrieves document context and returns grounded answer with exact source citations.
    """
    return await RAGEngine.query(
        query=req.query,
        top_k=req.top_k or 4,
        filter_doc_ids=req.filter_doc_ids
    )

@router.post("/chat", response_model=ChatResponse)
async def chat_interaction(req: ChatRequest):
    """
    Agentic conversational endpoint.
    Automatically classifies user intent (RETRIEVAL vs ACTION vs CONVERSATIONAL),
    executes external tools if requested, or retrieves grounded document knowledge.
    """
    return await AgentRouter.process_chat(
        message=req.message,
        session_id=req.session_id,
        enable_agent=req.enable_agent,
        top_k=req.top_k or 4
    )
