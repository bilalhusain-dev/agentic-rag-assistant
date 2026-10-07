from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from app.models.document import Citation

class QueryRequest(BaseModel):
    query: str = Field(..., description="The user query or question")
    top_k: Optional[int] = Field(default=4, ge=1, le=10)
    filter_doc_ids: Optional[List[str]] = Field(default=None)

class QueryResponse(BaseModel):
    query: str
    answer: str
    grounded: bool
    citations: List[Citation]
    retrieved_chunks_count: int
    processing_time_ms: float

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    citations: Optional[List[Citation]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    enable_agent: bool = True
    top_k: Optional[int] = 4

class ToolExecutionResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    status: Literal["success", "error"]
    result: Dict[str, Any]
    execution_time_ms: float

class ChatResponse(BaseModel):
    session_id: str
    answer: str
    mode_used: Literal["RETRIEVAL", "ACTION", "CONVERSATIONAL", "HYBRID"]
    grounded: bool
    citations: List[Citation]
    tool_executions: List[ToolExecutionResult] = []
    processing_time_ms: float

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    indexed_documents_count: int
    total_vectors_count: int
    embedding_mode: str
