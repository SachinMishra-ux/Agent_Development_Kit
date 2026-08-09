// ── Configuration & State ────────────────────────────────────────────────────
// Cloud Run secure proxy gateway runs on port 8081
const BACKEND_URL = "http://localhost:8081";
let API_KEY = "";
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
  await fetchConfig();
  await loadSessions();
}

// ── User Setup ───────────────────────────────────────────────────────────────
function setupUser() {
  let storedUser = localStorage.getItem("adk_cloud_run_user_id");
  if (!storedUser) {
    storedUser = "user_cr_" + Math.random().toString(36).substring(2, 9);
    localStorage.setItem("adk_cloud_run_user_id", storedUser);
  }
  USER_ID = storedUser;
}

// ── Fetch Config from Backend ────────────────────────────────────────────────
async function fetchConfig() {
  try {
    const response = await fetch(`${BACKEND_URL}/config`);
    if (response.ok) {
      const data = await response.json();
      API_KEY = data.api_key;
      statusDot.className = "status-dot online";
      serverStatusText.textContent = "Cloud Run Connected";
    } else {
      throw new Error("Could not load config");
    }
  } catch (e) {
    statusDot.className = "status-dot";
    serverStatusText.textContent = "Cloud Run Offline";
    console.error("Config fetch failed: ", e);
  }
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
  const lastActive = localStorage.getItem("adk_cloud_run_active_session") || sessions[0].id;
  await selectSession(lastActive);
}

// Retrieve from localStorage (scoped specifically to Cloud Run user)
function getSavedSessions() {
  const raw = localStorage.getItem(`adk_cr_sessions_${USER_ID}`);
  return raw ? JSON.parse(raw) : [];
}

function saveSessions(sessions) {
  localStorage.setItem(`adk_cr_sessions_${USER_ID}`, JSON.stringify(sessions));
}

async function createNewSession() {
  if (!API_KEY) {
    console.warn("API Key not loaded yet. Waiting...");
    await fetchConfig();
  }

  try {
    const res = await fetch(`${BACKEND_URL}/sessions`, {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ user_id: USER_ID })
    });

    if (res.ok) {
      const data = await res.json();
      const newSession = {
        id: data.session_id,
        created: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      const sessions = getSavedSessions();
      sessions.unshift(newSession);
      saveSessions(sessions);

      renderSessionItem(newSession);
      await selectSession(newSession.id);
    }
  } catch (e) {
    console.error("Failed to create session:", e);
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
  localStorage.setItem("adk_cloud_run_active_session", sessionId);
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
      This bot is configured to shorten long messages and check the weather using tool execution.
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
    const response = await fetch(`${BACKEND_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        user_id: USER_ID,
        session_id: CURRENT_SESSION_ID,
        message: message
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

          switch (event.type) {
            case "session_created":
              // Handle dynamically created session from the backend
              CURRENT_SESSION_ID = event.session_id;
              currentSessionText.textContent = `Session: ${CURRENT_SESSION_ID.substring(0, 12)}...`;
              
              const newSession = {
                id: CURRENT_SESSION_ID,
                created: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              };
              const sessions = getSavedSessions();
              sessions.unshift(newSession);
              saveSessions(sessions);
              
              // Add to sidebar UI
              renderSessionItem(newSession);
              document.querySelectorAll(".session-item").forEach(item => {
                if (item.dataset.id === CURRENT_SESSION_ID) {
                  item.classList.add("active");
                } else {
                  item.classList.remove("active");
                }
              });
              break;

            case "text":
              // Remove cursor, append text, add cursor back
              const cursor = bubble.querySelector(".typing-cursor");
              if (cursor) cursor.remove();
              bubble.innerHTML += event.content;
              bubble.appendChild(createCursorElement());
              break;

            case "tool_call":
              activeToolCard = createReasoningCard(event.name, event.args);
              reasoningContainer.appendChild(activeToolCard);
              break;

            case "tool_response":
              if (activeToolCard) {
                updateReasoningCardSuccess(activeToolCard, event.name, event.response);
              }
              break;

            case "error":
              const errCursor = bubble.querySelector(".typing-cursor");
              if (errCursor) errCursor.remove();
              bubble.innerHTML += `<br><span style="color:var(--error)">[Error] ${event.content}</span>`;
              break;
          }
          scrollToBottom();
        } catch (e) {
          console.error("Error parsing event stream line:", e);
        }
      }
    }

    // Finished streaming — clean up cursor
    const finalCursor = bubble.querySelector(".typing-cursor");
    if (finalCursor) finalCursor.remove();

  } catch (e) {
    bubble.innerHTML = `<span style="color:var(--error)">Network connection failed. Make sure the FastAPI server is running.</span>`;
    console.error("Streaming failed:", e);
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
