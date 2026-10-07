import time
import re
import uuid
from typing import Dict, Any, List, Optional
from app.models.schemas import ChatResponse, ToolExecutionResult
from app.services.rag_engine import RAGEngine
from app.services.tool_registry import ToolRegistry
from app.services.vector_store import vector_store
from app.config import settings

class AgentRouter:
    # In-memory session dialogue store with capacity cap
    SESSIONS: Dict[str, List[Dict[str, str]]] = {}

    @classmethod
    def get_session_history(cls, session_id: str) -> List[Dict[str, str]]:
        if session_id not in cls.SESSIONS:
            if len(cls.SESSIONS) >= settings.MAX_SESSION_CACHE:
                # Evict oldest session key
                oldest_key = next(iter(cls.SESSIONS))
                cls.SESSIONS.pop(oldest_key, None)
            cls.SESSIONS[session_id] = []
        return cls.SESSIONS[session_id]

    @classmethod
    def classify_intent(cls, message: str) -> str:
        """
        Classifies incoming prompt intent: ACTION, RETRIEVAL, or CONVERSATIONAL.
        """
        msg_lower = message.lower().strip()

        # Action triggers (tickets, customer lookup, service health)
        is_ticket_action = "ticket" in msg_lower and any(
            v in msg_lower for v in ["create", "open", "file", "raise", "support", "submit", "new", "priority"]
        )
        is_customer_action = any(
            k in msg_lower for k in ["lookup customer", "find customer", "customer account", "crm", "account status", "lookup", "account"]
        ) and any(w in msg_lower for w in ["customer", "account", "crm", "tier", "mrr", "csm"])
        
        is_service_action = any(
            k in msg_lower for k in ["service status", "check service", "check status", "system status", "service health"]
        )

        if is_ticket_action or is_customer_action or is_service_action:
            return "ACTION"

        # Conversational greetings & identity queries
        greeting_starters = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
        is_greeting = any(msg_lower.startswith(g) or g in re.sub(r'[^\w\s]', '', msg_lower).split() for g in greeting_starters)
        is_identity = any(phrase in msg_lower for phrase in ["who are you", "what can you do", "what are your tools", "help me"])

        if is_greeting or is_identity:
            if len(msg_lower.split()) <= 6 or is_identity:
                return "CONVERSATIONAL"

        # Default to Document Retrieval
        return "RETRIEVAL"

    @classmethod
    async def process_chat(
        cls,
        message: str,
        session_id: Optional[str] = None,
        enable_agent: bool = True,
        top_k: int = 4
    ) -> ChatResponse:
        start_time = time.perf_counter()
        active_session = session_id or str(uuid.uuid4())
        history = cls.get_session_history(active_session)

        intent = cls.classify_intent(message)
        tool_executions: List[ToolExecutionResult] = []
        citations = []
        grounded = False

        if intent == "ACTION" and enable_agent:
            # Parse tool parameters from message
            msg_lower = message.lower()
            
            if "ticket" in msg_lower:
                priority = "medium"
                if "critical" in msg_lower or "p1" in msg_lower or "urgent" in msg_lower:
                    priority = "critical"
                elif "high" in msg_lower:
                    priority = "high"
                elif "low" in msg_lower:
                    priority = "low"

                tool_args = {
                    "title": message[:60].strip(),
                    "priority": priority,
                    "category": "Technical Infrastructure",
                    "description": message.strip()
                }
                exec_result = await ToolRegistry.execute_tool("create_support_ticket", tool_args)
                tool_executions.append(exec_result)

                if exec_result.status == "success":
                    t = exec_result.result
                    answer = (
                        f"✅ **Support Ticket Created**\n\n"
                        f"* **Ticket ID:** `{t['ticket_id']}`\n"
                        f"* **Priority:** `{t['priority'].upper()}`\n"
                        f"* **SLA Target:** `{t['sla_target_hours']} hours`\n"
                        f"* **Status:** `{t['status']}`\n\n"
                        f"The operations engineering team has been notified."
                    )
                else:
                    answer = f"⚠️ Failed to create ticket: {exec_result.result}"

            elif "customer" in msg_lower or "crm" in msg_lower:
                query_target = message
                for prefix in ["lookup customer", "find customer", "account status", "customer"]:
                    if prefix in msg_lower:
                        query_target = message[msg_lower.find(prefix) + len(prefix):].strip(" :,-")
                        break

                tool_args = {"query": query_target or "Acme Global"}
                exec_result = await ToolRegistry.execute_tool("lookup_customer_account", tool_args)
                tool_executions.append(exec_result)

                if exec_result.status == "success":
                    c = exec_result.result
                    answer = (
                        f"📊 **CRM Account Record**\n\n"
                        f"* **Account Name:** {c['account_name']}\n"
                        f"* **Tier:** `{c['tier']}`\n"
                        f"* **MRR:** `{c['mrr']}`\n"
                        f"* **Assigned CSM:** {c['csm']}\n"
                        f"* **Status:** `{c['status']}`"
                    )
                else:
                    answer = f"⚠️ Customer lookup failed: {exec_result.result}"

            elif "service" in msg_lower or "status" in msg_lower:
                service = "core-gateway"
                if "auth" in msg_lower:
                    service = "auth-service"
                elif "db" in msg_lower or "vector" in msg_lower:
                    service = "vector-store"

                tool_args = {"service_name": service}
                exec_result = await ToolRegistry.execute_tool("check_service_status", tool_args)
                tool_executions.append(exec_result)

                if exec_result.status == "success":
                    s = exec_result.result
                    answer = (
                        f"🟢 **Service Health Telemetry**\n\n"
                        f"* **Service:** `{s['service']}`\n"
                        f"* **Status:** `{s['status']}`\n"
                        f"* **30-Day Uptime:** `{s['uptime_30d']}`\n"
                        f"* **P95 Latency:** `{s['latency_p95_ms']} ms`\n"
                        f"* **Active Incidents:** `{s['active_incidents']}`"
                    )
                else:
                    answer = f"⚠️ Service health check failed: {exec_result.result}"

            else:
                answer = "Action intent detected, but no matching tool schema could be mapped."

            mode_used = "ACTION"

        elif intent == "CONVERSATIONAL":
            answer = (
                "Hello! I am NexusRAG, your enterprise AI assistant. "
                "I can answer questions grounded in your uploaded internal documents "
                "with exact citations, or perform actions such as creating support tickets "
                "and looking up CRM customer accounts."
            )
            mode_used = "CONVERSATIONAL"

        else:
            # Document RAG Retrieval Mode
            rag_resp = await RAGEngine.query(query=message, top_k=top_k)
            answer = rag_resp.answer
            citations = rag_resp.citations
            grounded = rag_resp.grounded
            mode_used = "RETRIEVAL"

        # Update session memory
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": answer})
        if len(history) > 10:
            history = history[-10:]
            cls.SESSIONS[active_session] = history

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return ChatResponse(
            session_id=active_session,
            answer=answer,
            mode_used=mode_used,
            grounded=grounded,
            citations=citations,
            tool_executions=tool_executions,
            processing_time_ms=round(elapsed_ms, 2)
        )
