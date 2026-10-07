/**
 * NexusRAG Web Client
 * Clean Stripe-grade UX for Document Management, Citations & Agent Tools
 */

const API_BASE = '/api/v1';
let activeSessionId = 'sess_' + Math.random().toString(36).substring(2, 9);
let currentCitations = [];

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const docList = document.getElementById('docList');
const docCountBadge = document.getElementById('docCount');
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const excerptModal = document.getElementById('excerptModal');
const modalDocTitle = document.getElementById('modalDocTitle');
const modalExcerptBody = document.getElementById('modalExcerptBody');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  fetchDocuments();
  setupEventListeners();
});

function setupEventListeners() {
  // Dropzone click & drag handlers
  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', handleFileSelect);

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  // Chat input
  sendBtn.addEventListener('click', sendMessage);
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      sendMessage();
    }
  });
}

function handleFileSelect(e) {
  if (e.target.files && e.target.files.length > 0) {
    uploadFile(e.target.files[0]);
  }
}

// Upload file to /api/v1/documents/upload
async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const prevText = dropzone.querySelector('p').textContent;
  dropzone.querySelector('p').textContent = `Uploading ${file.name}...`;

  try {
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }

    const data = await res.json();
    appendSystemNotice(`Indexed "${data.filename}" (${data.total_chunks} chunks parsed).`);
    await fetchDocuments();
  } catch (err) {
    alert(`Document upload error: ${err.message}`);
  } finally {
    dropzone.querySelector('p').textContent = prevText;
    fileInput.value = '';
  }
}

// Fetch indexed documents
async function fetchDocuments() {
  try {
    const res = await fetch(`${API_BASE}/documents`);
    if (!res.ok) return;
    const docs = await res.json();
    renderDocumentList(docs);
  } catch (err) {
    console.error('Failed to load documents:', err);
  }
}

function renderDocumentList(docs) {
  docCountBadge.textContent = docs.length;
  docList.innerHTML = '';

  if (docs.length === 0) {
    docList.innerHTML = `
      <div style="padding: 24px 16px; text-align: center; color: var(--text-muted); font-size: 13px;">
        No documents indexed yet. Upload a PDF, TXT, or MD file to enable grounded RAG.
      </div>
    `;
    return;
  }

  docs.forEach(doc => {
    const card = document.createElement('div');
    card.className = 'doc-card';
    card.innerHTML = `
      <div class="doc-info">
        <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
        <div class="doc-meta">
          <span>${doc.total_chunks} chunks</span> • 
          <span>${formatBytes(doc.file_size_bytes)}</span>
        </div>
      </div>
      <button class="btn-delete" title="Delete document" onclick="deleteDocument('${doc.doc_id}')">✕</button>
    `;
    docList.appendChild(card);
  });
}

// Delete document
async function deleteDocument(docId) {
  if (!confirm('Remove this document and purge its vector embeddings?')) return;
  try {
    const res = await fetch(`${API_BASE}/documents/${docId}`, {
      method: 'DELETE'
    });
    if (res.ok) {
      fetchDocuments();
    }
  } catch (err) {
    alert('Failed to delete document: ' + err.message);
  }
}

// Send chat message
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  // Append user message
  appendUserMessage(text);
  userInput.value = '';
  userInput.focus();

  // Loading indicator
  const loadingRow = appendAssistantLoading();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        session_id: activeSessionId,
        enable_agent: true,
        top_k: 4
      })
    });

    loadingRow.remove();

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Assistant query failed');
    }

    const data = await res.json();
    appendAssistantResponse(data);
  } catch (err) {
    if (loadingRow) loadingRow.remove();
    appendAssistantError(`Request failed: ${err.message}`);
  }
}

function appendUserMessage(text) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  row.innerHTML = `<div class="msg-user-bubble">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function appendAssistantLoading() {
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `
    <div class="msg-assistant-card" style="padding: 12px 18px; color: var(--text-muted); font-size: 13px;">
      Searching knowledge index & evaluating intent...
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
  return row;
}

function appendAssistantResponse(data) {
  const row = document.createElement('div');
  row.className = 'msg-row';

  // Determine tag style
  let tagClass = 'tag-retrieval';
  let tagLabel = 'RAG Retrieval';
  if (data.mode_used === 'ACTION') {
    tagClass = 'tag-action';
    tagLabel = 'Agent Action';
  } else if (data.mode_used === 'CONVERSATIONAL') {
    tagClass = 'tag-conversational';
    tagLabel = 'Conversation';
  }

  // Citations store for modal lookup
  const citationStoreIndex = currentCitations.length;
  currentCitations.push(data.citations || []);

  let citationsHtml = '';
  if (data.citations && data.citations.length > 0) {
    citationsHtml = `
      <div class="citations-container">
        <div class="citations-label">Source Citations (${data.citations.length})</div>
        <div class="citation-pills">
          ${data.citations.map((c, i) => `
            <span class="citation-pill" onclick="openExcerptModal(${citationStoreIndex}, ${i})">
              📄 ${escapeHtml(c.filename)} (Score: ${Math.round(c.score * 100)}%)
            </span>
          `).join('')}
        </div>
      </div>
    `;
  }

  let toolCardHtml = '';
  const executedTool = data.tool_executions && data.tool_executions.length > 0 ? data.tool_executions[0] : null;
  if (executedTool) {
    const t = executedTool;
    const isSuccess = t.status === 'success';
    toolCardHtml = `
      <div class="tool-call-card">
        <div class="tool-call-header">
          <span class="tool-name">⚡ Tool Executed: ${escapeHtml(t.tool_name)}</span>
          <span style="font-size: 11px; font-weight: 600; color: ${isSuccess ? 'var(--success-green)' : '#dc2626'}">
            ${t.status.toUpperCase()}
          </span>
        </div>
        <pre class="tool-receipt">${escapeHtml(JSON.stringify(t.result, null, 2))}</pre>
      </div>
    `;
  }

  row.innerHTML = `
    <div class="msg-assistant-card">
      <div class="msg-header">
        <span class="msg-mode-tag ${tagClass}">${tagLabel}</span>
        <span style="font-size: 11px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">
          ${data.processing_time_ms ? `${data.processing_time_ms}ms` : ''}
        </span>
      </div>
      <div class="msg-body">${formatMessageBody(data.answer)}</div>
      ${toolCardHtml}
      ${citationsHtml}
    </div>
  `;

  chatMessages.appendChild(row);
  scrollToBottom();
}

function appendAssistantError(msg) {
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `
    <div class="msg-assistant-card" style="border-left: 3px solid #dc2626;">
      <div class="msg-body" style="color: #b91c1c;">${escapeHtml(msg)}</div>
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function appendSystemNotice(text) {
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `
    <div style="font-size: 12px; color: var(--text-muted); background: #f1f5f9; padding: 6px 12px; border-radius: 6px; margin: 4px auto;">
      ℹ️ ${escapeHtml(text)}
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
}

// Modal Handlers
function openExcerptModal(batchIdx, citationIdx) {
  const citation = currentCitations[batchIdx]?.[citationIdx];
  if (!citation) return;

  modalDocTitle.textContent = `${citation.filename} (Page ${citation.page_number || 1})`;
  modalExcerptBody.textContent = citation.excerpt;
  excerptModal.classList.add('active');
}

function hideModal() {
  excerptModal.classList.remove('active');
}

function closeModal(event) {
  if (event.target === excerptModal) {
    hideModal();
  }
}

// Quick Prompt Fill
function fillPrompt(text) {
  userInput.value = text;
  userInput.focus();
}

// Utility Helpers
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatMessageBody(text) {
  if (!text) return '';
  // Basic markdown formatting: bold and newlines
  let formatted = escapeHtml(text);
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  formatted = formatted.replace(/\n/g, '<br>');
  return formatted;
}
