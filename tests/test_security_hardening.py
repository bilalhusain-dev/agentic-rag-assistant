from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_security_headers_present():
    """Verify enterprise defensive HTTP headers are attached to every response."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "strict-origin" in response.headers.get("Referrer-Policy", "")

def test_path_traversal_filename_sanitization():
    """Verify filenames with directory traversal are stripped to basenames."""
    traversal_filename = "../../../etc/passwd.txt"
    files = {"file": (traversal_filename, b"root:x:0:0:root:/root:/bin/bash", "text/plain")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "passwd.txt"
    assert "/" not in data["filename"]
    assert "\\" not in data["filename"]

def test_disallowed_file_extension_rejection():
    """Verify executable or dangerous extensions are rejected with HTTP 400."""
    files = {"file": ("malware.exe", b"MZ\x90\x00BinaryPayload", "application/octet-stream")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]

def test_file_size_limit_rejection():
    """Verify uploads exceeding MAX_UPLOAD_SIZE_BYTES are rejected with HTTP 413."""
    # Temporarily set max size to small value for test
    original_limit = settings.MAX_UPLOAD_SIZE_BYTES
    try:
        settings.MAX_UPLOAD_SIZE_BYTES = 500  # 500 bytes limit
        oversized_payload = b"A" * 600
        files = {"file": ("large_file.txt", oversized_payload, "text/plain")}
        response = client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = original_limit
