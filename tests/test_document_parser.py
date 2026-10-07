import pytest
import fitz  # PyMuPDF
from app.services.document_parser import DocumentParser

def test_parse_plain_text():
    sample_text = "Nexus Cloud Security.\nSection 1: Passwords must be 14 characters long."
    pages = DocumentParser.parse_file(sample_text.encode("utf-8"), "security_policy.txt")
    assert len(pages) == 1
    assert "Nexus Cloud Security" in pages[0]["text"]
    assert "14 characters" in pages[0]["text"]

def test_parse_markdown():
    sample_md = "# Service Level Agreement\n\n- Uptime guarantee: 99.95%\n- P1 response: 15 minutes."
    pages = DocumentParser.parse_file(sample_md.encode("utf-8"), "sla.md")
    assert len(pages) == 1
    assert "Service Level Agreement" in pages[0]["text"]
    assert "99.95%" in pages[0]["text"]

def test_parse_pdf_via_fitz():
    # Generate an in-memory synthetic PDF with PyMuPDF
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 72), "Confidential Executive Summary Page 1")
    page2 = doc.new_page()
    page2.insert_text((50, 72), "Detailed Financial Audit Page 2")
    
    pdf_bytes = doc.tobytes()
    doc.close()

    pages = DocumentParser.parse_file(pdf_bytes, "audit_report.pdf")
    assert len(pages) == 2
    assert "Executive Summary" in pages[0]["text"]
    assert "Financial Audit" in pages[1]["text"]

def test_parse_empty_raises_error():
    with pytest.raises(ValueError):
        DocumentParser.parse_file(b"", "empty.txt")

def test_parse_unsupported_extension_raises_error():
    with pytest.raises(ValueError):
        DocumentParser.parse_file(b"some content", "data.exe")
