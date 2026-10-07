import pytest
from app.services.tool_registry import ToolRegistry
from app.services.agent_router import AgentRouter

def test_tool_registry_discovery():
    tools = ToolRegistry.get_tool_definitions()
    tool_names = [t.name for t in tools]
    assert "create_support_ticket" in tool_names
    assert "lookup_customer_account" in tool_names
    assert "check_service_status" in tool_names

@pytest.mark.asyncio
async def test_execute_create_support_ticket():
    result = await ToolRegistry.execute_tool(
        tool_name="create_support_ticket",
        arguments={
            "title": "Database connection pool exhausted",
            "priority": "critical",
            "description": "API cluster receiving HTTP 504 gateway timeouts"
        }
    )
    assert result.status == "success"
    assert "ticket_id" in result.result
    assert result.result["priority"] == "critical"
    assert result.result["status"] == "OPEN"

@pytest.mark.asyncio
async def test_execute_lookup_customer_account():
    result = await ToolRegistry.execute_tool(
        tool_name="lookup_customer_account",
        arguments={"query": "Acme Global"}
    )
    assert result.status == "success"
    assert result.result["tier"] == "Enterprise"
    assert result.result["status"] == "Active"

@pytest.mark.asyncio
async def test_execute_check_service_status():
    result = await ToolRegistry.execute_tool(
        tool_name="check_service_status",
        arguments={"service_name": "auth-service"}
    )
    assert result.status == "success"
    assert result.result["service"] == "auth-service"
    assert result.result["status"] == "OPERATIONAL"

@pytest.mark.asyncio
async def test_execute_invalid_tool_name():
    result = await ToolRegistry.execute_tool(
        tool_name="unsupported_dangerous_action",
        arguments={}
    )
    assert result.status == "error"
    assert "Unsupported tool" in result.result["error"]

@pytest.mark.asyncio
async def test_execute_invalid_tool_arguments():
    # Priority is restricted to 'low', 'normal', 'high', 'critical'
    result = await ToolRegistry.execute_tool(
        tool_name="create_support_ticket",
        arguments={"title": "Test", "priority": "urgent_asap_not_valid"}
    )
    assert result.status == "error"
    assert "validation_errors" in result.result

@pytest.mark.asyncio
async def test_agent_intent_classification():
    # Action intent
    action_resp = await AgentRouter.process_chat(
        message="Create a support ticket: Payment webhook failure",
        enable_agent=True
    )
    assert action_resp.mode_used == "ACTION"
    assert len(action_resp.tool_executions) > 0
    assert action_resp.tool_executions[0].tool_name == "create_support_ticket"

    # Conversational intent
    conv_resp = await AgentRouter.process_chat(
        message="Hello! Who are you?",
        enable_agent=True
    )
    assert conv_resp.mode_used == "CONVERSATIONAL"
    assert "NexusRAG" in conv_resp.answer
