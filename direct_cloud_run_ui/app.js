// ── Configuration & State ────────────────────────────────────────────────────
// Connect directly to the deployed Cloud Run service URL
const BACKEND_URL = "https://adk-simple-bot-service-206644930711.us-central1.run.app";
const APP_NAME = "adk_simple_bot";
let CURRENT_SESSION_ID = "";
let USER_ID = "";

// ── DOM Elements ─────────────────────────────────────────────────────────────
const chatFeed = document.getElementById("chat-feed");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const newChatBtn = document.getElementById("new-chat-btn");
const sessionsList = document.getElementById("sessions-list");
const currentSessionText = document.getElementById("current-session-id");
const sessionInfoPill = document.getElementById("session-info-pill");
const serverStatusText = document.getElementById("status-text");
const statusDot = document.querySelector(".status-dot");
const modelBadge = document.getElementById("model-badge");

// Configure marked if available
if (window.marked) {
  marked.setOptions({
    gfm: true,
    breaks: true
  });
}

// ── Application Initialization ───────────────────────────────────────────────
async function initApp() {
  setupUser();
  await checkHealth();
  await loadSessions();
}

// ── User Setup ───────────────────────────────────────────────────────────────
function setupUser() {
  let storedUser = localStorage.getItem("adk_direct_cr_user_id");
  if (!storedUser) {
    storedUser = "user_direct_" + Math.random().toString(36).substring(2, 9);
    localStorage.setItem("adk_direct_cr_user_id", storedUser);
  }
  USER_ID = storedUser;
}

// ── Server Health & Info Check ──────────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${BACKEND_URL}/health`);
    if (res.ok) {
      if (statusDot) statusDot.className = "status-dot online";
      if (serverStatusText) serverStatusText.textContent = "Cloud Run Connected";
      return true;
    } else {
      throw new Error(`Health returned status ${res.status}`);
    }
  } catch (e) {
    if (statusDot) statusDot.className = "status-dot";
    if (serverStatusText) serverStatusText.textContent = "Cloud Run Offline";
    console.warn("Cloud Run health check warning:", e);
    return false;
  }
}

// ── Session Management ────────────────────────────────────────────────────────
async function loadSessions() {
  let sessions = getSavedSessions();
  sessionsList.innerHTML = "";

  if (sessions.length === 0) {
    await createNewSession();
    return;
  }

  // Verify whether the most recent session is still valid on Cloud Run
  const lastActive = localStorage.getItem("adk_direct_cr_active_session") || sessions[0].id;
  const isValid = await verifySessionOnServer(lastActive);

  if (!isValid) {
    console.log("Cached session is no longer active on Cloud Run. Provisioning fresh session...");
    sessions = [];
    saveSessions(sessions);
    await createNewSession();
    return;
  }

  sessions.forEach(sess => {
    renderSessionItem(sess);
  });

  await selectSession(lastActive);
}

async function verifySessionOnServer(sessionId) {
  if (!sessionId) return false;
  try {
    const res = await fetch(`${BACKEND_URL}/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionId}`);
    return res.ok;
  } catch (e) {
    return false;
  }
}

// Retrieve from localStorage (scoped specifically to Direct Cloud Run user)
function getSavedSessions() {
  const raw = localStorage.getItem(`adk_direct_sessions_${USER_ID}`);
  return raw ? JSON.parse(raw) : [];
}

function saveSessions(sessions) {
  localStorage.setItem(`adk_direct_sessions_${USER_ID}`, JSON.stringify(sessions));
}

async function createNewSession() {
  try {
    const sessionUrl = `${BACKEND_URL}/apps/${APP_NAME}/users/${USER_ID}/sessions`;
    const res = await fetch(sessionUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({})
    });

    if (res.ok) {
      const data = await res.json();
      const newSession = {
        id: data.id,
        created: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      const sessions = getSavedSessions();
      sessions.unshift(newSession);
      saveSessions(sessions);

      renderSessionItem(newSession);
      await selectSession(newSession.id);
      return newSession.id;
    } else {
      console.error("Cloud Run session endpoint failed:", res.status);
    }
  } catch (e) {
    console.error("Failed to create session on Cloud Run:", e);
  }
  return null;
}

function renderSessionItem(session) {
  const item = document.createElement("div");
  item.className = "session-item";
  item.dataset.id = session.id;
  item.innerHTML = `
    <span class="material-symbols-rounded session-icon">chat_bubble</span>
    <span>Session ${session.id.substring(0, 8)}...</span>
  `;
  item.addEventListener("click", () => selectSession(session.id));
  sessionsList.appendChild(item);
}

async function selectSession(sessionId) {
  CURRENT_SESSION_ID = sessionId;
  localStorage.setItem("adk_direct_cr_active_session", sessionId);
  if (currentSessionText) {
    currentSessionText.textContent = `Session: ${sessionId.substring(0, 12)}...`;
  }

  // Highlight in sidebar
  document.querySelectorAll(".session-item").forEach(item => {
    if (item.dataset.id === sessionId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  chatFeed.innerHTML = "";

  // Attempt to restore session events history from Cloud Run
  try {
    const res = await fetch(`${BACKEND_URL}/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionId}`);
    if (res.ok) {
      const data = await res.json();
      const events = data.events || [];
      if (events.length > 0) {
        renderSessionHistory(events);
        return;
      }
    }
  } catch (e) {
    console.warn("Could not retrieve session events:", e);
  }

  showWelcomeScreen();
}

function renderSessionHistory(events) {
  chatFeed.innerHTML = "";
  let currentReasoningContainer = null;
  let activeToolCard = null;

  for (const event of events) {
    const role = event.content?.role || (event.author === 'user' ? 'user' : 'model');
    const parts = event.content?.parts || [];

    if (role === 'user') {
      const userText = parts.map(p => p.text || '').join('');
      if (userText) {
        appendMessageRow('user', userText);
      }
      currentReasoningContainer = null;
    } else if (role === 'model') {
      for (const part of parts) {
        const fc = part.functionCall || part.function_call;
        if (fc) {
          if (!currentReasoningContainer) {
            currentReasoningContainer = document.createElement("div");
            currentReasoningContainer.className = "reasoning-container";
            chatFeed.appendChild(currentReasoningContainer);
          }
          activeToolCard = createReasoningCard(fc.name, fc.args);
          currentReasoningContainer.appendChild(activeToolCard);
        }

        const text = part.text;
        if (text) {
          const row = appendMessageRow('agent', '');
          const bubble = row.querySelector('.message-bubble');
          renderMarkdown(bubble, text, false);
          currentReasoningContainer = null;
        }
      }
    } else if (role === 'tool') {
      for (const part of parts) {
        const fr = part.functionResponse || part.function_response;
        if (fr && activeToolCard) {
          updateReasoningCardSuccess(activeToolCard, fr.name, fr.response);
        }
      }
    }
  }
  scrollToBottom();
}

function showWelcomeScreen() {
  const welcome = document.createElement("div");
  welcome.className = "welcome-container";
  welcome.id = "welcome-container";
  welcome.innerHTML = `
    <span class="material-symbols-rounded welcome-icon">forum</span>
    <h3>Welcome to adk_simple_bot</h3>
    <p>
      An intelligent AI agent running live on <strong>Google Cloud Run</strong>.
      This interface communicates directly with your Cloud Run service URL in real-time.
    </p>
    <div class="suggestions">
      <button class="suggestion-card" onclick="sendSuggestion('What is the weather in Delhi?')">
        <span class="material-symbols-rounded">cloud</span>
        <span>"What is the weather in Delhi?"</span>
      </button>
      <button class="suggestion-card" onclick="sendSuggestion('Can you shorten this: The meeting scheduled for tomorrow has been postponed to next week.')">
        <span class="material-symbols-rounded">compress</span>
        <span>"Can you shorten this message..."</span>
      </button>
      <button class="suggestion-card" onclick="sendSuggestion('Who are you and what tools do you have?')">
        <span class="material-symbols-rounded">smart_toy</span>
        <span>"Who are you and what tools do you have?"</span>
      </button>
    </div>
  `;
  chatFeed.appendChild(welcome);
}

// ── Helper to copy Session ID ────────────────────────────────────────────────
if (sessionInfoPill) {
  sessionInfoPill.addEventListener("click", () => {
    if (CURRENT_SESSION_ID) {
      navigator.clipboard.writeText(CURRENT_SESSION_ID);
      const originalText = currentSessionText.textContent;
      currentSessionText.textContent = "Copied!";
      setTimeout(() => {
        currentSessionText.textContent = originalText;
      }, 1500);
    }
  });
}

// ── Send Suggestion ──────────────────────────────────────────────────────────
window.sendSuggestion = function(messageText) {
  if (chatInput) {
    chatInput.value = messageText;
    handleMessageSubmit();
  }
};

// ── Message Submission ───────────────────────────────────────────────────────
if (chatForm) {
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleMessageSubmit();
  });
}

function handleMessageSubmit() {
  const text = chatInput.value.trim();
  if (!text) return;

  // Clear welcome screen if present
  const welcome = document.getElementById("welcome-container");
  if (welcome) {
    welcome.remove();
  }

  appendMessageRow("user", text);
  chatInput.value = "";
  
  // Stream query
  streamAgentQuery(text);
}

// ── Append message to Feed ───────────────────────────────────────────────────
function appendMessageRow(sender, text) {
  const row = document.createElement("div");
  row.className = `message-row ${sender}`;
  const senderName = sender === 'user' ? 'You' : 'adk_simple_bot';
  const initialContent = sender === 'user' ? escapeHtml(text) : text;
  
  row.innerHTML = `
    <div class="message-sender">${senderName}</div>
    <div class="message-bubble">${initialContent}</div>
  `;
  chatFeed.appendChild(row);
  scrollToBottom();
  return row;
}

// ── Streaming Response with Perplexity-style reasoning UI ────────────────────
async function streamAgentQuery(message, retryCount = 0) {
  // Ensure we have a valid session ID
  if (!CURRENT_SESSION_ID) {
    const newId = await createNewSession();
    if (!newId) {
      const errRow = appendMessageRow("agent", "");
      errRow.querySelector(".message-bubble").innerHTML = `<span style="color:var(--error)">Failed to initialize a Cloud Run session. Check service availability.</span>`;
      return;
    }
  }

  // Create reasoning container for tools
  const reasoningContainer = document.createElement("div");
  reasoningContainer.className = "reasoning-container";
  chatFeed.appendChild(reasoningContainer);

  // Append empty assistant message row
  const agentRow = appendMessageRow("agent", "");
  const bubble = agentRow.querySelector(".message-bubble");
  
  // Setup cursor effect
  bubble.innerHTML = '<span class="typing-cursor"></span>';

  let fullResponseText = "";
  let activeToolCard = null;

  try {
    const runSseUrl = `${BACKEND_URL}/run_sse`;
    const response = await fetch(runSseUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        appName: APP_NAME,
        userId: USER_ID,
        sessionId: CURRENT_SESSION_ID,
        newMessage: {
          role: "user",
          parts: [{ text: message }]
        }
      })
    });

    // Handle expired/not found session by auto-recreating and retrying once
    if (response.status === 404 && retryCount === 0) {
      console.warn("Session expired on Cloud Run. Recreating session and retrying...");
      reasoningContainer.remove();
      agentRow.remove();
      await createNewSession();
      return streamAgentQuery(message, retryCount + 1);
    }

    if (!response.ok) {
      const errorText = await response.text();
      bubble.innerHTML = `<span style="color:var(--error)">Cloud Run Error (${response.status}): ${escapeHtml(errorText)}</span>`;
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");

      // Keep last incomplete segment in buffer
      buffer = lines.pop();

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;

        const rawData = trimmed.substring(5).trim();
        try {
          const event = JSON.parse(rawData);

          // Check if event reports a backend error
          if (event.errorMessage || event.error) {
            const errDesc = event.errorMessage || (typeof event.error === 'string' ? event.error : JSON.stringify(event.error));
            const cursor = bubble.querySelector(".typing-cursor");
            if (cursor) cursor.remove();
            bubble.innerHTML += `<div style="color:var(--error); margin-top:8px;">⚠️ ${escapeHtml(errDesc)}</div>`;
            continue;
          }

          const content = event.content || {};
          const parts = content.parts || [];
          
          for (const part of parts) {
            if (!part) continue;

            // 1. Text chunk
            const text = part.text;
            if (text) {
              fullResponseText += text;
              renderMarkdown(bubble, fullResponseText, true);
            }

            // 2. Tool Function Call
            const fc = part.functionCall || part.function_call;
            if (fc) {
              activeToolCard = createReasoningCard(fc.name, fc.args);
              reasoningContainer.appendChild(activeToolCard);
            }

            // 3. Tool Function Response
            const fr = part.functionResponse || part.function_response;
            if (fr) {
              if (activeToolCard) {
                updateReasoningCardSuccess(activeToolCard, fr.name, fr.response);
              }
            }
          }
          scrollToBottom();
        } catch (e) {
          console.error("Error parsing direct stream event:", e, rawData);
        }
      }
    }

    // Finished streaming: finalize markdown rendering without cursor
    renderMarkdown(bubble, fullResponseText, false);

  } catch (e) {
    bubble.innerHTML = `<span style="color:var(--error)">Network connection failed. Verify Cloud Run URL: ${escapeHtml(BACKEND_URL)}</span>`;
    console.error("Direct streaming failed:", e);
  }
}

// ── Markdown & Text Rendering ────────────────────────────────────────────────
function renderMarkdown(element, rawText, isStreaming = false) {
  let html = "";
  if (window.marked && typeof marked.parse === "function") {
    html = marked.parse(rawText);
  } else {
    html = escapeHtml(rawText).replace(/\n/g, "<br>");
  }

  if (isStreaming) {
    html += '<span class="typing-cursor"></span>';
  }
  element.innerHTML = html;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ── Perplexity-style reasoning UI elements ──────────────────────────────────
function createReasoningCard(toolName, args) {
  const card = document.createElement("div");
  card.className = "reasoning-step";
  
  const formattedArgs = formatJSON(args);
  const cardId = "card-" + Math.random().toString(36).substring(2, 9);
  
  card.innerHTML = `
    <div class="reasoning-header" onclick="toggleReasoningContent('${cardId}')">
      <div class="reasoning-header-left">
        <span class="material-symbols-rounded reasoning-icon">settings_ethernet</span>
        <span>Calling <strong>${escapeHtml(toolName)}</strong>...</span>
      </div>
      <span class="reasoning-badge running">Running</span>
    </div>
    <div class="reasoning-content open" id="${cardId}">
      <p style="margin-bottom:8px; color:var(--text-muted)">Tool Call Input Payload:</p>
      <pre>${formattedArgs}</pre>
    </div>
  `;
  return card;
}

function updateReasoningCardSuccess(card, toolName, response) {
  const badge = card.querySelector(".reasoning-badge");
  if (badge) {
    badge.textContent = "Success";
    badge.className = "reasoning-badge success";
  }
  
  const headerText = card.querySelector(".reasoning-header-left span");
  if (headerText) {
    headerText.innerHTML = `<span class="material-symbols-rounded" style="color:var(--success);font-size:18px;vertical-align:middle;margin-right:6px">check_circle</span>Retrieved <strong>${escapeHtml(toolName)}</strong> response`;
  }

  const formattedResponse = formatJSON(response);
  const content = card.querySelector(".reasoning-content");
  if (content) {
    content.innerHTML += `
      <p style="margin:12px 0 8px 0; color:var(--text-muted)">Tool Output Response:</p>
      <pre>${formattedResponse}</pre>
    `;
  }
}

window.toggleReasoningContent = function(cardId) {
  const content = document.getElementById(cardId);
  if (content) {
    content.classList.toggle("open");
  }
};

function formatJSON(obj) {
  if (!obj) return "{}";
  const str = JSON.stringify(obj, null, 2);
  return escapeHtml(str)
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")/g, '<span class="json-key">$1</span>')
    .replace(/(:\s*)("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")/g, '$1<span class="json-val">$2</span>')
    .replace(/(:\s*)(\d+)/g, '$1<span class="json-num">$2</span>');
}

// ── Sidebar button handlers ──────────────────────────────────────────────────
if (newChatBtn) {
  newChatBtn.addEventListener("click", createNewSession);
}

// ── Auto Scroll ──────────────────────────────────────────────────────────────
function scrollToBottom() {
  if (chatFeed) {
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }
}

// ── App boot ─────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", initApp);
