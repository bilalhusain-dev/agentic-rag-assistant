import time
import random
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError
from app.models.schemas import ToolDefinition, ToolExecutionResult

# Pydantic Schemas for Strict Tool Validation
class CreateSupportTicketInput(BaseModel):
    title: str = Field(..., min_length=5, description="Brief summary of the issue")
    priority: str = Field(..., pattern="^(low|medium|high|critical)$", description="Priority level")
    category: str = Field(default="Technical", description="Issue category (e.g. Billing, Technical, Security)")
    description: str = Field(..., min_length=10, description="Detailed description of the issue")

class LookupCustomerAccountInput(BaseModel):
    query: str = Field(..., min_length=3, description="Customer ID, company name, or account email")

class CheckServiceStatusInput(BaseModel):
    service_name: str = Field(..., min_length=2, description="Target service (e.g., auth-api, vector-db, payments)")

class ToolRegistry:
    # Simulated persistent storage for tickets and mock customer records
    TICKETS_DB: List[Dict[str, Any]] = []
    CUSTOMERS_DB = {
        "acme": {"account_name": "Acme Global", "tier": "Enterprise", "mrr": "$12,500", "csm": "Sarah Chen", "status": "Active"},
        "stripe": {"account_name": "Stripe Payments EU", "tier": "Strategic", "mrr": "$48,000", "csm": "David Miller", "status": "Active"},
        "cyberdyne": {"account_name": "CyberDyne Defense", "tier": "Defense Prime", "mrr": "$32,000", "csm": "Alex Reed", "status": "Active"}
    }
    AUDIT_LOGS: List[Dict[str, Any]] = []

    @classmethod
    def get_tool_definitions(cls) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="create_support_ticket",
                description="Dispatches a new high-priority support ticket to the internal Jira/Zendesk system.",
                parameters=CreateSupportTicketInput.model_json_schema()
            ),
            ToolDefinition(
                name="lookup_customer_account",
                description="Queries the CRM database to retrieve customer contract tier, MRR, and assigned CSM.",
                parameters=LookupCustomerAccountInput.model_json_schema()
            ),
            ToolDefinition(
                name="check_service_status",
                description="Checks real-time operational status, incident telemetry, and uptime of internal services.",
                parameters=CheckServiceStatusInput.model_json_schema()
            )
        ]

    @classmethod
    async def execute_tool(cls, tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        start_time = time.perf_counter()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        try:
            if tool_name == "create_support_ticket":
                validated = CreateSupportTicketInput(**arguments)
                ticket_id = f"TICK-{random.randint(1000, 9999)}"
                sla_hours = {"low": 48, "medium": 24, "high": 4, "critical": 1}[validated.priority]
                
                result_payload = {
                    "ticket_id": ticket_id,
                    "title": validated.title,
                    "priority": validated.priority,
                    "category": validated.category,
                    "status": "OPEN",
                    "sla_target_hours": sla_hours,
                    "created_at": timestamp
                }
                cls.TICKETS_DB.append(result_payload)
                status = "success"

            elif tool_name == "lookup_customer_account":
                validated = LookupCustomerAccountInput(**arguments)
                q = validated.query.lower()
                
                # Match against customer DB
                match = None
                for key, val in cls.CUSTOMERS_DB.items():
                    if key in q or val["account_name"].lower() in q:
                        match = val
                        break

                if match:
                    result_payload = match
                else:
                    result_payload = {
                        "account_name": validated.query,
                        "tier": "Standard Pro",
                        "mrr": "$2,400",
                        "csm": "Unassigned (Pooled CSM)",
                        "status": "Active"
                    }
                status = "success"

            elif tool_name == "check_service_status":
                validated = CheckServiceStatusInput(**arguments)
                result_payload = {
                    "service": validated.service_name,
                    "status": "OPERATIONAL",
                    "uptime_30d": "99.98%",
                    "latency_p95_ms": 14,
                    "active_incidents": 0
                }
                status = "success"

            else:
                raise ValueError(f"Unsupported tool '{tool_name}' requested.")

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Record audit log
            cls.AUDIT_LOGS.append({
                "timestamp": timestamp,
                "tool": tool_name,
                "arguments": arguments,
                "status": status,
                "latency_ms": round(elapsed_ms, 2)
            })

            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                status=status,
                result=result_payload,
                execution_time_ms=round(elapsed_ms, 2)
            )

        except ValidationError as ve:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            error_details = {"validation_errors": ve.errors()}
            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                status="error",
                result=error_details,
                execution_time_ms=round(elapsed_ms, 2)
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                status="error",
                result={"error": str(e)},
                execution_time_ms=round(elapsed_ms, 2)
            )
