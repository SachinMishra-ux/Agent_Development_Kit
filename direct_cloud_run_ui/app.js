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

// ── Application Initialization ───────────────────────────────────────────────
async function initApp() {
  setupUser();
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

// ── Session Management ────────────────────────────────────────────────────────
async function loadSessions() {
  const sessions = getSavedSessions();
  sessionsList.innerHTML = "";

  if (sessions.length === 0) {
    await createNewSession();
    return;
  }

  sessions.forEach(sess => {
    renderSessionItem(sess);
  });

  // Select the last active session or the first one
  const lastActive = localStorage.getItem("adk_direct_cr_active_session") || sessions[0].id;
  await selectSession(lastActive);
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
        id: data.id, // Direct Cloud Run session creation returns 'id'
        created: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      const sessions = getSavedSessions();
      sessions.unshift(newSession);
      saveSessions(sessions);

      renderSessionItem(newSession);
      await selectSession(newSession.id);
    } else {
      console.error("Cloud Run session endpoint failed:", res.status);
    }
  } catch (e) {
    console.error("Failed to create session on Cloud Run:", e);
  }
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
  currentSessionText.textContent = `Session: ${sessionId.substring(0, 12)}...`;

  // Highlight in sidebar
  document.querySelectorAll(".session-item").forEach(item => {
    if (item.dataset.id === sessionId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Clear feed and show welcome screen
  chatFeed.innerHTML = "";
  showWelcomeScreen();
}

function showWelcomeScreen() {
  const welcome = document.createElement("div");
  welcome.className = "welcome-container";
  welcome.id = "welcome-container";
  welcome.innerHTML = `
    <span class="material-symbols-rounded welcome-icon">forum</span>
    <h3>Welcome to adk_simple_bot</h3>
    <p>
      An intelligent AI agent running live on **Google Cloud Run**.
      This interface queries your Cloud Run endpoint **directly** with no local server.
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
    </div>
  `;
  chatFeed.appendChild(welcome);
}

// ── Helper to copy Session ID ────────────────────────────────────────────────
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

// ── Send Suggestion ──────────────────────────────────────────────────────────
function sendSuggestion(messageText) {
  chatInput.value = messageText;
  handleMessageSubmit();
}

// ── Message Submission ───────────────────────────────────────────────────────
chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  handleMessageSubmit();
});

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
  row.innerHTML = `
    <div class="message-sender">${sender === 'user' ? 'You' : 'adk_simple_bot'}</div>
    <div class="message-bubble">${text}</div>
  `;
  chatFeed.appendChild(row);
  scrollToBottom();
  return row;
}

// ── Streaming Response with Perplexity-style reasoning UI ────────────────────
async function streamAgentQuery(message) {
  // Create reasoning container
  const reasoningContainer = document.createElement("div");
  reasoningContainer.className = "reasoning-container";
  chatFeed.appendChild(reasoningContainer);

  // Append empty assistant message row
  const agentRow = appendMessageRow("agent", "");
  const bubble = agentRow.querySelector(".message-bubble");
  
  // Setup cursor effect
  bubble.innerHTML = '<span class="typing-cursor"></span>';

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
          parts: [{"text": message}]
        }
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      bubble.innerHTML = `<span style="color:var(--error)">Error: ${errorText}</span>`;
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    // Track active tool reasoning card
    let activeToolCard = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");

      // Save the last incomplete line back to the buffer
      buffer = lines.pop();

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;

        const rawData = trimmed.substring(5).trim();
        try {
          const event = JSON.parse(rawData);

          const content = event.content || {};
          const parts = content.parts || [];
          
          for (const part of parts) {
            if (!part) continue;

            // 1. Plain text chunk
            const text = part.text;
            if (text) {
              const cursor = bubble.querySelector(".typing-cursor");
              if (cursor) cursor.remove();
              bubble.innerHTML += text;
              bubble.appendChild(createCursorElement());
            }

            // 2. Tool Function Call (Handle camelCase and snake_case)
            const fc = part.functionCall || part.function_call;
            if (fc) {
              activeToolCard = createReasoningCard(fc.name, fc.args);
              reasoningContainer.appendChild(activeToolCard);
            }

            // 3. Tool Function Response (Handle camelCase and snake_case)
            const fr = part.functionResponse || part.function_response;
            if (fr) {
              if (activeToolCard) {
                updateReasoningCardSuccess(activeToolCard, fr.name, fr.response);
              }
            }
          }
          scrollToBottom();
        } catch (e) {
          console.error("Error parsing direct stream event:", e);
        }
      }
    }

    // Finished streaming — clean up cursor
    const finalCursor = bubble.querySelector(".typing-cursor");
    if (finalCursor) finalCursor.remove();

  } catch (e) {
    bubble.innerHTML = `<span style="color:var(--error)">Network connection failed. Make sure the Cloud Run service is reachable.</span>`;
    console.error("Direct streaming failed:", e);
  }
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
        <span>Calling <strong>${toolName}</strong>...</span>
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
  badge.textContent = "Success";
  badge.className = "reasoning-badge success";
  
  const headerText = card.querySelector(".reasoning-header-left span");
  headerText.innerHTML = `<span class="material-symbols-rounded" style="color:var(--success);font-size:18px;vertical-align:middle;margin-right:6px">check_circle</span>Retrieved <strong>${toolName}</strong> response`;

  const formattedResponse = formatJSON(response);
  const content = card.querySelector(".reasoning-content");
  
  // Append response to card content
  content.innerHTML += `
    <p style="margin:12px 0 8px 0; color:var(--text-muted)">Tool Output Response:</p>
    <pre>${formattedResponse}</pre>
  `;
}

function toggleReasoningContent(cardId) {
  const content = document.getElementById(cardId);
  if (content) {
    content.classList.toggle("open");
  }
}

function createCursorElement() {
  const span = document.createElement("span");
  span.className = "typing-cursor";
  return span;
}

function formatJSON(obj) {
  if (!obj) return "{}";
  const str = JSON.stringify(obj, null, 2);
  // Basic color syntax highlighting for display
  return str
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")/g, '<span class="json-key">$1</span>')
    .replace(/(:\s*)("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")/g, '$1<span class="json-val">$2</span>')
    .replace(/(:\s*)(\d+)/g, '$1<span class="json-num">$2</span>');
}

// ── Sidebar button handlers ──────────────────────────────────────────────────
newChatBtn.addEventListener("click", createNewSession);

// ── Auto Scroll ──────────────────────────────────────────────────────────────
function scrollToBottom() {
  chatFeed.scrollTop = chatFeed.scrollHeight;
}

// ── App boot ─────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", initApp);
