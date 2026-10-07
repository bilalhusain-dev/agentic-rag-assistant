import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "version" in data

def test_tool_discovery_and_audit():
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) >= 3

    # Audit logs
    audit_resp = client.get("/api/v1/tools/audit-logs")
    assert audit_resp.status_code == 200
    assert "count" in audit_resp.json()

def test_direct_tool_execution_endpoint():
    response = client.post("/api/v1/tools/execute", json={
        "tool_name": "check_service_status",
        "arguments": {"service_name": "billing-api"}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["tool_name"] == "check_service_status"
    assert data["result"]["status"] == "OPERATIONAL"

def test_full_document_lifecycle_and_rag_query():
    # 1. Upload sample document
    sample_content = (
        "NEXUS DISASTER RECOVERY POLICY.\n"
        "Recovery Point Objective (RPO) is strictly 15 minutes.\n"
        "Recovery Time Objective (RTO) is strictly 1 hour for all primary clusters.\n"
        "Hot failover switches automatically via Geo-DNS within 60 seconds."
    )
    
    files = {"file": ("disaster_recovery.txt", sample_content.encode("utf-8"), "text/plain")}
    upload_res = client.post("/api/v1/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["doc_id"]
    assert doc_data["filename"] == "disaster_recovery.txt"
    assert doc_data["total_chunks"] >= 1

    # 2. List documents
    list_res = client.get("/api/v1/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d["doc_id"] == doc_id for d in docs)

    # 3. Direct RAG query
    query_res = client.post("/api/v1/query", json={
        "query": "What is the Recovery Point Objective (RPO) and RTO?",
        "top_k": 3
    })
    assert query_res.status_code == 200
    q_data = query_res.json()
    assert q_data["grounded"] is True
    assert len(q_data["citations"]) > 0
    assert "15 minutes" in q_data["answer"] or "RPO" in q_data["answer"]

    # 4. Agent Chat with retrieval
    chat_res = client.post("/api/v1/chat", json={
        "message": "What is our failover time for geo-dns?",
        "enable_agent": True
    })
    assert chat_res.status_code == 200
    c_data = chat_res.json()
    assert c_data["mode_used"] == "RETRIEVAL"
    assert len(c_data["citations"]) > 0

    # 5. Agent Chat with Action tool
    chat_action_res = client.post("/api/v1/chat", json={
        "message": "Create a high priority support ticket: Secondary database replication lag high",
        "enable_agent": True
    })
    assert chat_action_res.status_code == 200
    a_data = chat_action_res.json()
    assert a_data["mode_used"] == "ACTION"
    assert len(a_data["tool_executions"]) > 0
    assert a_data["tool_executions"][0]["tool_name"] == "create_support_ticket"

    # 6. Delete document
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
