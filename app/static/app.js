/**
 * NexusRAG — Enterprise Assistant Client
 * ChatGPT / Claude / Stripe caliber UX Controller
 */

const API_BASE = '/api/v1';
let activeSessionId = 'sess_' + Math.random().toString(36).substring(2, 10);
let storedCitations = [];
let activeExcerptText = '';

// DOM Elements
const headerEngineMode = document.getElementById('headerEngineMode');
const dropzone = document.getElementById('dropzone');
const dropzonePrompt = document.getElementById('dropzonePrompt');
const fileInput = document.getElementById('fileInput');
const docListContainer = document.getElementById('docListContainer');
const docCountBadge = document.getElementById('docCountBadge');
const chatScrollArea = document.getElementById('chatScrollArea');
const chatThread = document.getElementById('chatThread');
const heroCard = document.getElementById('heroCard');
const userPromptInput = document.getElementById('userPromptInput');
const sendPromptBtn = document.getElementById('sendPromptBtn');
const citationModal = document.getElementById('citationModal');
const modalDocTitle = document.getElementById('modalDocTitle');
const modalDocBody = document.getElementById('modalDocBody');

// Lifecycle Initialization
document.addEventListener('DOMContentLoaded', () => {
  loadTelemetry();
  fetchDocuments();
  initEventListeners();
});

function initEventListeners() {
  // File upload dropzone
  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadDocumentFile(e.target.files[0]);
    }
  });

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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadDocumentFile(e.dataTransfer.files[0]);
    }
  });

  // Prompt input handling
  sendPromptBtn.addEventListener('click', handleSendMessage);
  
  userPromptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Auto-grow textarea
  userPromptInput.addEventListener('input', () => {
    userPromptInput.style.height = 'auto';
    userPromptInput.style.height = Math.min(userPromptInput.scrollHeight, 180) + 'px';
  });
}

// Telemetry check
async function loadTelemetry() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      if (headerEngineMode) {
        headerEngineMode.textContent = data.embedding_mode || 'Operational';
      }
    }
  } catch (err) {
    console.warn('Telemetry load failed:', err);
  }
}

// Document Management
async function fetchDocuments() {
  try {
    const res = await fetch(`${API_BASE}/documents`);
    if (!res.ok) return;
    const docs = await res.json();
    renderDocumentList(docs);
  } catch (err) {
    console.error('Failed to fetch documents:', err);
  }
}

function renderDocumentList(docs) {
  docCountBadge.textContent = `${docs.length} doc${docs.length === 1 ? '' : 's'}`;
  docListContainer.innerHTML = '';

  if (docs.length === 0) {
    docListContainer.innerHTML = `
      <div style="padding: 24px 12px; text-align: center; color: var(--text-muted); font-size: 12px;">
        No documents indexed yet.<br>Drop a PDF or Markdown file to begin.
      </div>
    `;
    return;
  }

  docs.forEach(doc => {
    const ext = doc.filename.split('.').pop().toLowerCase();
    let icon = '📄';
    if (ext === 'pdf') icon = '📕';
    else if (ext === 'md' || ext === 'markdown') icon = '📝';

    const card = document.createElement('div');
    card.className = 'doc-card';
    card.innerHTML = `
      <div class="doc-meta-info">
        <span class="doc-type-icon">${icon}</span>
        <div class="doc-text-wrapper">
          <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
          <div class="doc-details">${doc.total_chunks} chunks • ${formatBytes(doc.file_size_bytes)}</div>
        </div>
      </div>
      <button class="btn-icon-delete" title="Purge document" onclick="deleteDocument('${doc.doc_id}')">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
      </button>
    `;
    docListContainer.appendChild(card);
  });
}

async function uploadDocumentFile(file) {
  const originalPrompt = dropzonePrompt.textContent;
  dropzonePrompt.textContent = `Indexing ${file.name}...`;

  const formData = new FormData();
  formData.append('file', file);

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
    showToastNotice(`Indexed "${data.filename}" (${data.total_chunks} semantic chunks)`);
    await fetchDocuments();
  } catch (err) {
    alert(`Document upload error: ${err.message}`);
  } finally {
    dropzonePrompt.textContent = originalPrompt;
    fileInput.value = '';
  }
}

async function deleteDocument(docId) {
  if (!confirm('Permanently purge this document and all indexed vectors?')) return;
  try {
    const res = await fetch(`${API_BASE}/documents/${docId}`, { method: 'DELETE' });
    if (res.ok) {
      fetchDocuments();
    }
  } catch (err) {
    alert('Deletion failed: ' + err.message);
  }
}

// Chat & Agent Interaction
async function handleSendMessage() {
  const query = userPromptInput.value.trim();
  if (!query) return;

  // Hide hero card on first message
  if (heroCard && heroCard.style.display !== 'none') {
    heroCard.style.display = 'none';
  }

  // Append user bubble
  appendUserMessage(query);
  userPromptInput.value = '';
  userPromptInput.style.height = 'auto';
  userPromptInput.focus();

  // Loading skeleton
  const loadingElement = appendLoadingIndicator();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: query,
        session_id: activeSessionId,
        enable_agent: true,
        top_k: 4
      })
    });

    loadingElement.remove();

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Query execution error');
    }

    const data = await res.json();
    appendAssistantMessage(data);
  } catch (err) {
    if (loadingElement) loadingElement.remove();
    appendErrorMessage(`Request Error: ${err.message}`);
  }
}

function appendUserMessage(text) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  row.innerHTML = `<div class="msg-user-bubble">${escapeHtml(text)}</div>`;
  chatThread.appendChild(row);
  scrollToBottom();
}

function appendLoadingIndicator() {
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  row.innerHTML = `
    <div class="assistant-card" style="padding: 14px 18px; color: var(--text-muted); font-size: 13px; display: flex; align-items: center; gap: 8px;">
      <span class="pulse-dot"></span>
      Searching vector index & evaluating agent intent...
    </div>
  `;
  chatThread.appendChild(row);
  scrollToBottom();
  return row;
}

function appendAssistantMessage(data) {
  const row = document.createElement('div');
  row.className = 'msg-row assistant';

  let modeClass = 'mode-retrieval';
  let modeLabel = 'RAG Retrieval';
  let modeIcon = '🔍';

  if (data.mode_used === 'ACTION') {
    modeClass = 'mode-action';
    modeLabel = 'Agent Action';
    modeIcon = '⚡';
  } else if (data.mode_used === 'CONVERSATIONAL') {
    modeClass = 'mode-conversational';
    modeLabel = 'Conversational';
    modeIcon = '💬';
  }

  // Citations mapping
  const citationBatchIdx = storedCitations.length;
  storedCitations.push(data.citations || []);

  let citationsHtml = '';
  if (data.citations && data.citations.length > 0) {
    citationsHtml = `
      <div class="citations-panel">
        <div class="citations-header-title">
          <span>📚 Verified Citations (${data.citations.length})</span>
        </div>
        <div class="citations-pill-row">
          ${data.citations.map((c, i) => `
            <button class="citation-btn-pill" onclick="openCitationExcerpt(${citationBatchIdx}, ${i})">
              <span>📄 ${escapeHtml(c.filename)} (p. ${c.page_number || 1})</span>
              <span class="citation-score-badge">${Math.round(c.score * 100)}%</span>
            </button>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Tool Call Banner
  let toolBannerHtml = '';
  const executedTool = data.tool_executions && data.tool_executions.length > 0 ? data.tool_executions[0] : null;
  if (executedTool) {
    toolBannerHtml = `
      <div class="tool-call-banner">
        <div class="tool-banner-header">
          <div class="tool-banner-title">
            <span>⚡ Action Executed:</span>
            <span>${escapeHtml(executedTool.tool_name)}</span>
          </div>
          <span class="tool-banner-badge">${executedTool.status.toUpperCase()}</span>
        </div>
        <pre class="tool-payload-content">${escapeHtml(JSON.stringify(executedTool.result, null, 2))}</pre>
      </div>
    `;
  }

  row.innerHTML = `
    <div class="assistant-card">
      <div class="assistant-header">
        <div class="assistant-mode-pill ${modeClass}">
          <span>${modeIcon}</span>
          <span>${modeLabel}</span>
        </div>
        <span class="assistant-meta-time">${data.processing_time_ms ? `${data.processing_time_ms}ms` : ''}</span>
      </div>
      <div class="assistant-body">${formatMarkdownBody(data.answer)}</div>
      ${toolBannerHtml}
      ${citationsHtml}
      <div class="card-actions-bar">
        <button class="btn-action-copy" onclick="copyCardContent(this, \`${escapeJsString(data.answer)}\`)">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy Answer
        </button>
      </div>
    </div>
  `;

  chatThread.appendChild(row);
  scrollToBottom();
}

function appendErrorMessage(msg) {
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  row.innerHTML = `
    <div class="assistant-card" style="border-left: 3px solid #ef4444;">
      <div style="color: #b91c1c; font-size: 13.5px; font-weight: 500;">${escapeHtml(msg)}</div>
    </div>
  `;
  chatThread.appendChild(row);
  scrollToBottom();
}

function showToastNotice(text) {
  const notice = document.createElement('div');
  notice.style.cssText = `
    position: fixed;
    bottom: 90px;
    right: 24px;
    background: #0f172a;
    color: #ffffff;
    font-size: 12px;
    font-weight: 500;
    padding: 8px 14px;
    border-radius: 8px;
    box-shadow: var(--shadow-float);
    z-index: 50;
    animation: fadeIn 0.15s ease-out;
  `;
  notice.textContent = `✓ ${text}`;
  document.body.appendChild(notice);
  setTimeout(() => notice.remove(), 3200);
}

// Modal Handlers
function openCitationExcerpt(batchIdx, citIdx) {
  const citation = storedCitations[batchIdx]?.[citIdx];
  if (!citation) return;

  activeExcerptText = citation.excerpt;
  modalDocTitle.textContent = `${citation.filename} (Page ${citation.page_number || 1}) • Match ${Math.round(citation.score * 100)}%`;
  modalDocBody.textContent = citation.excerpt;
  citationModal.classList.add('active');
}

function hideCitationModal() {
  citationModal.classList.remove('active');
}

function closeModalOnBackdrop(e) {
  if (e.target === citationModal) {
    hideCitationModal();
  }
}

function copyCitationSnippet() {
  if (!activeExcerptText) return;
  navigator.clipboard.writeText(activeExcerptText).then(() => {
    alert('Citation excerpt copied to clipboard!');
  });
}

function copyCardContent(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = '✓ Copied!';
    setTimeout(() => { btn.innerHTML = originalText; }, 1800);
  });
}

// Prompt Suggestion Selector
function selectPrompt(promptText) {
  userPromptInput.value = promptText;
  userPromptInput.focus();
  handleSendMessage();
}

// Helpers
function scrollToBottom() {
  chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
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

function escapeJsString(str) {
  if (!str) return '';
  return String(str).replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
}

function formatMarkdownBody(text) {
  if (!text) return '';
  let formatted = escapeHtml(text);
  
  // Bold
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Bullet lists
  formatted = formatted.replace(/^\* (.*$)/gim, '<li>$1</li>');
  formatted = formatted.replace(/^- (.*$)/gim, '<li>$1</li>');
  formatted = formatted.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
  
  // Code snippets
  formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #0f172a;">$1</code>');
  
  // Paragraphs / line breaks
  formatted = formatted.replace(/\n\n/g, '<br><br>');
  formatted = formatted.replace(/\n/g, '<br>');
  
  return formatted;
}
