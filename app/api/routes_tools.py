from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.models.schemas import ToolDefinition, ToolExecutionResult
from app.services.tool_registry import ToolRegistry

router = APIRouter(prefix="/tools", tags=["Agent Tools"])

class ExecuteToolPayload(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

@router.get("", response_model=List[ToolDefinition])
async def list_tools():
    """Lists all available external tools and their JSON parameter schemas."""
    return ToolRegistry.get_tool_definitions()

@router.post("/execute", response_model=ToolExecutionResult)
async def execute_tool(payload: ExecuteToolPayload):
    """Direct execution endpoint for tools with strict input validation."""
    return await ToolRegistry.execute_tool(payload.tool_name, payload.arguments)

@router.get("/audit-logs")
async def get_tool_audit_logs():
    """Retrieves immutable audit trail of executed tools and external API calls."""
    return {"count": len(ToolRegistry.AUDIT_LOGS), "logs": ToolRegistry.AUDIT_LOGS}
