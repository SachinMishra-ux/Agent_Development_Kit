uv run adk deploy --help

Usage: adk deploy [OPTIONS] COMMAND [ARGS]...

  Deploys agent to hosted environments.

Options:
  --help  Show this message and exit.

Commands:
  agent_engine  Deploys an agent to Agent Engine.
  cloud_run     Deploys an agent to Cloud Run.
  gke           Deploys an agent to GKE.


uv run adk deploy cloud_run --help


---

## 1. What is Google Cloud Run?

**Google Cloud Run** is a fully managed, serverless compute platform that automatically scales containerized applications.

### Key Characteristics
* **Serverless Scale-to-Zero:** Cloud Run automatically scales instances based on traffic. When idle, it scales down to **zero active instances**, costing nothing.
* **Container-Based:** Runs standard Docker containers, giving full control over system libraries and dependencies.
* **HTTPS Endpoint:** Provides a secure, public HTTPS URL for your container.

---

## 2. Architecture Comparison

| Feature | Vertex AI Agent Engine | Google Cloud Run |
| :--- | :--- | :--- |
| **Runtime Model** | Managed Python object wrapper (ReasoningEngine) | Standard container running a FastAPI web server |
| **Packaging** | Serialized via `cloudpickle` | Fully containerized Docker image |
| **Scaling** | Managed by Vertex AI platform | Autoscaling container instances (down to 0) |

---

## 3. Isolated File Structure for Cloud Run

We will create the following new files and folders:
* 📄 **[`api_server_cloud_run.py`](file:///Users/sachinmishra/Desktop/Agent_Development_Kit/api_server_cloud_run.py)**: A new local FastAPI proxy server running on port **`8081`** (avoiding port conflicts with the existing server on `8080`). It will connect to the deployed Cloud Run URL.
* 📄 **[`test_deployed_agent_cloud_run.py`](file:///Users/sachinmishra/Desktop/Agent_Development_Kit/test_deployed_agent_cloud_run.py)**: A new integration test script designed to query the Cloud Run deployment.
* 📂 **[`frontend_cloud_run/`](file:///Users/sachinmishra/Desktop/Agent_Development_Kit/frontend_cloud_run/)**: A new folder containing the CRED-style UI, configured to hit the new local API server on port `8081`.
  - `index.html`
  - `style.css`
  - `app.js`

---

## 4. Proposed Deployment Steps

### Step 1 — Deploy the Container to Cloud Run
Run the ADK deployment CLI command to compile and deploy the agent folder:
```bash
uv run adk deploy cloud_run \
  --project=email-copilotmy-project-20497 \
  --region=us-central1 \
  --service_name="adk-simple-bot-service" \
  adk_simple_bot
```

### Step 2 — Configure Environment & New API Server
1. Capture the printed Cloud Run URL (e.g. `https://adk-simple-bot-service-xxxx.a.run.app`).
2. Add `GOOGLE_CLOUD_RUN_URL="https://adk-simple-bot-service-xxxx.a.run.app"` to your [`.env`](file:///Users/sachinmishra/Desktop/Agent_Development_Kit/.env) file.
3. Create `api_server_cloud_run.py` to route queries from port `8081` to the `GOOGLE_CLOUD_RUN_URL`.

### Step 3 — Create New Frontend UI
Create the `frontend_cloud_run/` directory and populate it with the CRED-style UI files, setting `BACKEND_URL` in `app.js` to `http://localhost:8081`.

---

## 5. Verification Plan

### Automated Tests
Verify by running the new test script against the Cloud Run API:
```bash
uv run python test_deployed_agent_cloud_run.py
```

### Manual Verification
Start the new API server on port `8081`, open `frontend_cloud_run/index.html` in your browser, and verify that the colorful UI works seamlessly.
