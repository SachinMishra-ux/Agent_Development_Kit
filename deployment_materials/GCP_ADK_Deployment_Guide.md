# Deploying Your Google ADK Agent to Google Cloud Platform

**Product:** Google Agent Development Kit (ADK) &nbsp;|&nbsp; **Audience:** Developers &nbsp;|&nbsp; **Last Updated:** August 2026

---

## Overview

The **Google Agent Development Kit (ADK)** is an open-source, code-first Python framework for building and deploying production-grade AI agents. After testing your agent locally with `adk web`, you are ready to deploy it to **Google Cloud Platform (GCP)**.

This guide covers all **three officially supported deployment options**:

| # | Option | Type | Effort Level |
|---|---|---|---|
| **A** | [Vertex AI Agent Engine](#option-a--vertex-ai-agent-engine) | Fully Managed (PaaS) | ⭐ Lowest |
| **B** | [Cloud Run](#option-b--cloud-run) | Serverless Containers | ⭐⭐ Low |
| **C** | [Google Kubernetes Engine (GKE)](#option-c--google-kubernetes-engine-gke) | Container Orchestration | ⭐⭐⭐ High |

---

## Before You Begin — Common Prerequisites

All three deployment options require the following setup. Complete these steps before proceeding to any option.

### 1. Google Cloud Project

- An active **Google Cloud Project** with **billing enabled**
- Go to: [https://console.cloud.google.com](https://console.cloud.google.com)

### 2. Install the Google Cloud CLI

```bash
# macOS (via Homebrew)
brew install google-cloud-sdk

# Authenticate and configure your project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 3. Verify Your Project Structure

Your project should look like this before deploying:

```
Agent_Development_Kit/              ← Run all commands from here
├── .env                            ← Contains GOOGLE_API_KEY
├── pyproject.toml
├── requirements.txt                ← Generate this (see below)
└── adk_simple_bot/
    ├── __init__.py                 ← Must contain: from . import agent
    ├── agent.py                    ← Must define: root_agent = Agent(...)
    ├── prompt.py
    └── tools/
        ├── __init__.py             ← Must export tools
        └── dummy_wether.py
```

### 4. Generate `requirements.txt`

```bash
cd /Users/sachinmishra/Desktop/Agent_Development_Kit
uv pip freeze > requirements.txt
```

> **Important:** Always run deployment commands from the **project root directory** (`Agent_Development_Kit/`), not from inside the `adk_simple_bot/` subfolder.

---

## Option A — Vertex AI Agent Engine

> **Best for:** Teams who want Google to manage all infrastructure, and need built-in session memory and monitoring out of the box.

### What Is Vertex AI Agent Engine?

Vertex AI Agent Engine (part of the **Gemini Enterprise Agent Platform**) is Google's fully managed runtime for ADK agents. You upload your Python code and Google handles everything else: scaling, sessions, memory, telemetry, and monitoring dashboards.

### Step 1 — Enable the Vertex AI API

```bash
gcloud services enable aiplatform.googleapis.com
```

### Step 2 — Install ADK with Vertex AI Support

```bash
pip install "google-adk[vertexai]"
```

Or if using `uv` (your project setup):

```bash
uv add "google-adk[vertexai]"
```

### Step 3 — Create a Google Cloud Storage Bucket (for staging)

```bash
gcloud storage buckets create gs://YOUR_PROJECT_ID-adk-staging \
  --location=us-central1
```

### Step 4 — Deploy Using the ADK CLI

Navigate to your project root and run:

```bash
cd /Users/sachinmishra/Desktop/Agent_Development_Kit

uv run adk deploy agent_engine \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  --display_name="adk_simple_bot" \
  --staging_bucket=gs://YOUR_PROJECT_ID-adk-staging \
  adk_simple_bot
```

**What happens when you run this command:**
1. ADK wraps your `root_agent` in a `reasoning_engines.AdkApp` object
2. It packages your code and uploads it to the staging bucket
3. Vertex AI provisions a managed runtime and deploys your agent
4. You receive a `resource_name` upon completion

**Sample output:**
```
Deploying agent to Vertex AI Agent Engine...
✓ Agent packaged successfully
✓ Uploaded to gs://YOUR_PROJECT_ID-adk-staging/
✓ Deployed to: projects/YOUR_PROJECT_ID/locations/us-central1/reasoningEngines/123456789
```

### Step 5 — Verify Deployment in the Console

Go to **Vertex AI Console → Agent Engine** in the Google Cloud Console to see your deployed agent, monitoring metrics, and session logs.

### Step 6 — Test Your Deployed Agent

```python
import vertexai
from vertexai.preview import reasoning_engines

# Initialize the Vertex AI client
vertexai.init(project="YOUR_PROJECT_ID", location="us-central1")

# Reference your deployed agent
agent = reasoning_engines.ReasoningEngine(
    "projects/YOUR_PROJECT_ID/locations/us-central1/reasoningEngines/123456789"
)

# Create a session
session = agent.create_session(user_id="user_001")

# Send a message and stream the response
response = agent.stream_query(
    user_id="user_001",
    session_id=session["id"],
    message="What is the weather in Delhi?"
)

for chunk in response:
    print(chunk, end="", flush=True)
```

### What Agent Engine Manages Automatically

| Feature | Details |
|---|---|
| ✅ Session Persistence | Conversation history retained across calls automatically |
| ✅ Scaling | Fully managed auto-scaling by Google |
| ✅ Monitoring | Built-in dashboard in Cloud Console |
| ✅ Telemetry | Logs, traces, and performance metrics included |
| ✅ Security | Google-managed IAM, no API key exposure |

### Pricing

| Billing Meter | Unit |
|---|---|
| Agent Runtime | Per vCPU-hour |
| Session & Memory | Per 1,000 events |
| Gemini Model Tokens | Per input/output token |
| Vertex AI Search (if used) | Per 1,000 queries |

> Typical prototyping cost: **$1–5/month**. Heavy production traffic: **$500–$2,000+/month**

### Pros & Cons

| ✅ Advantages | ❌ Limitations |
|---|---|
| Zero infrastructure management | Cannot deploy a custom Web UI directly |
| Built-in session persistence | Less container-level flexibility |
| Full monitoring dashboard in GCP Console | Fragmented pricing across 4 meters |
| Tightest Gemini model integration | Limited regional availability for some features |
| No container or Docker knowledge needed | |

---

## Option B — Cloud Run

> **Best for:** Most ADK agent deployments. Offers serverless containers with true scale-to-zero, custom web UIs, and straightforward CI/CD integration.

### What Is Cloud Run?

Cloud Run is Google's fully managed **serverless container platform**. Your ADK agent is packaged as a Docker container and deployed as a scalable HTTPS service. It automatically scales from zero (when idle) to thousands of instances (under load).

### Step 1 — Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

### Step 2 — Create an Artifact Registry Repository

```bash
gcloud artifacts repositories create adk-agents \
  --repository-format=docker \
  --location=us-central1 \
  --description="ADK agent container images"
```

### Step 3 — Create a `Dockerfile`

Create this file in your project root (`Agent_Development_Kit/`):

```dockerfile
# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy dependency file and install packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all agent code
COPY . .

# Cloud Run injects PORT automatically (default: 8080)
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Start the ADK API server
CMD ["adk", "api_server", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "adk_simple_bot"]
```

### Step 4A — Deploy Using the ADK CLI (Simplest Method)

```bash
cd /Users/sachinmishra/Desktop/Agent_Development_Kit

adk deploy cloud_run \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  --service_name=adk-simple-bot \
  adk_simple_bot
```

The `adk deploy cloud_run` command automatically:
1. Builds a Docker image from your project
2. Pushes it to Artifact Registry
3. Deploys it as a Cloud Run service
4. Returns a live **HTTPS URL** for your agent

### Step 4B — Deploy Using `gcloud` (Full Manual Control)

Use this method for custom CI/CD pipelines.

**Build and push the container image:**
```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/adk-agents/adk-simple-bot:v1 \
  .
```

**Deploy to Cloud Run:**
```bash
gcloud run deploy adk-simple-bot \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/adk-agents/adk-simple-bot:v1 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=YOUR_API_KEY
```

### Step 5 — Store API Key Securely with Secret Manager

Instead of passing your API key as a plain environment variable, use **Google Secret Manager**:

```bash
# Enable Secret Manager
gcloud services enable secretmanager.googleapis.com

# Create the secret
echo -n "YOUR_GOOGLE_API_KEY" | \
  gcloud secrets create GOOGLE_API_KEY \
  --replication-policy="automatic" \
  --data-file=-

# Redeploy with the secret mounted
gcloud run deploy adk-simple-bot \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/adk-agents/adk-simple-bot:v1 \
  --region us-central1 \
  --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
```

### Step 6 — Get Your Live Service URL

```bash
gcloud run services describe adk-simple-bot \
  --region us-central1 \
  --format="value(status.url)"
```

**Sample output:**
```
https://adk-simple-bot-abc123-uc.a.run.app
```

Your agent is now live at this public HTTPS URL.

### Step 7 — Handle Session State (Optional)

Cloud Run is stateless by default. For persistent conversation sessions, connect to **Cloud Firestore**:

```bash
gcloud services enable firestore.googleapis.com
gcloud firestore databases create --region=us-central1
```

Then update your `agent.py` to use `FirestoreSessionService` instead of the default in-memory session.

### Pricing

| Tier | Details |
|---|---|
| Free Tier | First 2 million requests/month FREE |
| Requests | ~$0.40 per million additional requests |
| CPU/Memory | Billed only during active request processing |
| Idle Cost | **$0.00** — scales to zero automatically |

### Pros & Cons

| ✅ Advantages | ❌ Limitations |
|---|---|
| True scale-to-zero (zero idle cost) | Session state requires external storage (Firestore) |
| Full container flexibility | Requires a `Dockerfile` |
| Supports custom Web UIs | Cold-start latency on first request |
| Easy CI/CD pipeline integration | |
| Identity-Aware Proxy (IAP) support for auth | |
| Supports HTTP streaming and WebSockets | |

---

## Option C — Google Kubernetes Engine (GKE)

> **Best for:** Enterprise teams needing GPU support, complex custom networking, self-hosted LLMs, or organizations already standardized on Kubernetes.

### What Is GKE?

**Google Kubernetes Engine (GKE)** gives you full Kubernetes-based container orchestration. This is the most powerful but most complex option. Use **GKE Autopilot** (recommended) for simplified cluster management while retaining full Kubernetes flexibility.

### Step 1 — Enable Required APIs

```bash
gcloud services enable \
  container.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com
```

### Step 2 — Create a GKE Autopilot Cluster

```bash
gcloud container clusters create-auto adk-agents-cluster \
  --region=us-central1 \
  --project=YOUR_PROJECT_ID
```

> `create-auto` provisions a **GKE Autopilot** cluster — Google manages node provisioning and scaling automatically.

### Step 3 — Configure `kubectl` Access

```bash
gcloud container clusters get-credentials adk-agents-cluster \
  --region=us-central1

# Verify connection
kubectl get nodes
```

### Step 4 — Build & Push Container Image

Use the same `Dockerfile` from Option B (Cloud Run):

```bash
# Build and push to Artifact Registry
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/adk-agents/adk-simple-bot:v1 \
  .
```

### Step 5 — Create Kubernetes Deployment Manifest

Create a file `k8s-deployment.yaml` in your project root:

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adk-simple-bot
  namespace: default
  labels:
    app: adk-simple-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: adk-simple-bot
  template:
    metadata:
      labels:
        app: adk-simple-bot
    spec:
      serviceAccountName: adk-simple-bot-sa
      containers:
      - name: adk-simple-bot
        image: us-central1-docker.pkg.dev/YOUR_PROJECT_ID/adk-agents/adk-simple-bot:v1
        ports:
        - containerPort: 8080
        env:
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: google-api-key-secret
              key: GOOGLE_API_KEY
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "2Gi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: adk-simple-bot-service
  namespace: default
spec:
  selector:
    app: adk-simple-bot
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
```

### Step 6 — Create a Kubernetes Secret for the API Key

```bash
kubectl create secret generic google-api-key-secret \
  --from-literal=GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
```

### Step 7 — Set Up Workload Identity (Secure Authentication)

Workload Identity lets your GKE pods authenticate to Google Cloud services without embedding API keys:

```bash
# Create a Kubernetes Service Account
kubectl create serviceaccount adk-simple-bot-sa

# Create a Google Cloud IAM Service Account
gcloud iam service-accounts create adk-simple-bot-gsa \
  --display-name="ADK Simple Bot Service Account"

# Grant it access to Vertex AI (for Gemini model)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:adk-simple-bot-gsa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Bind the Kubernetes SA to the GCP IAM SA
gcloud iam service-accounts add-iam-policy-binding \
  adk-simple-bot-gsa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:YOUR_PROJECT_ID.svc.id.goog[default/adk-simple-bot-sa]"

# Annotate the Kubernetes SA
kubectl annotate serviceaccount adk-simple-bot-sa \
  iam.gke.io/gcp-service-account=adk-simple-bot-gsa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### Step 8 — Deploy to GKE

```bash
kubectl apply -f k8s-deployment.yaml

# Watch pods come online
kubectl get pods --watch
```

### Step 9 — Get the External IP Address

```bash
kubectl get service adk-simple-bot-service

# Wait until EXTERNAL-IP is assigned, then access:
# http://EXTERNAL-IP/
```

### ADK CLI Shortcut for GKE

```bash
adk deploy gke \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  --cluster=adk-agents-cluster \
  adk_simple_bot
```

### Pros & Cons

| ✅ Advantages | ❌ Limitations |
|---|---|
| Maximum infrastructure control | Steepest learning curve of the three options |
| GPU node pool support for custom LLMs | No native scale-to-zero (cluster always costs money) |
| Complex networking & security policies | Requires Kubernetes expertise |
| Ideal for self-hosted models (vLLM, Llama) | Highest management overhead |
| Works with existing Kubernetes tooling (Helm, Argo) | |

---

## Side-by-Side Comparison

| Feature | Vertex AI Agent Engine | Cloud Run | GKE |
|---|:---:|:---:|:---:|
| **Deployment Effort** | ⭐ Very Low | ⭐⭐ Low | ⭐⭐⭐ High |
| **Infrastructure Management** | Google manages all | Serverless (none) | You manage cluster |
| **Session Persistence** | ✅ Built-in | ❌ Needs Firestore | ❌ Needs Firestore |
| **Scale to Zero** | ✅ Yes | ✅ Yes | ❌ No |
| **Custom Dockerfile** | ❌ Not needed | ✅ Required | ✅ Required |
| **Custom Web UI** | ❌ Not supported | ✅ Yes | ✅ Yes |
| **GPU Node Pools** | ❌ No | ❌ Limited | ✅ Yes |
| **Monitoring Dashboard** | ✅ Built-in | Via Cloud Logging | Via Cloud Logging |
| **ADK CLI Command** | `adk deploy agent_engine` | `adk deploy cloud_run` | `adk deploy gke` |
| **Idle Cost** | Low | **$0.00** | Cluster costs accrue |
| **Recommended For** | Fast managed deployments | **Most use cases** | Enterprise / GPU workloads |

---

## Decision Guide

```
Q: Do you want zero infrastructure management?
   └── YES → Vertex AI Agent Engine ✅

Q: Do you need a custom Web UI or CI/CD integration?
   └── YES → Cloud Run ✅

Q: Do you need GPUs or custom Kubernetes networking?
   └── YES → GKE ✅

Q: Are you a beginner or prototyping?
   └── YES → Cloud Run (simplest path) ✅

Q: Do you need built-in session memory without extra code?
   └── YES → Vertex AI Agent Engine ✅

Q: Is cost optimization for idle workloads a priority?
   └── YES → Cloud Run (scale-to-zero = $0 idle) ✅
```

> **Recommendation for `adk_simple_bot`:** Start with **Cloud Run**. It provides the best balance of simplicity, cost-efficiency, and flexibility. When you need built-in session memory without extra code, migrate to **Vertex AI Agent Engine**.

---

## Quick Reference — All CLI Commands

```bash
# ── Common Setup ──────────────────────────────────────────────
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# ── Option A: Vertex AI Agent Engine ─────────────────────────
gcloud services enable aiplatform.googleapis.com
uv run adk deploy agent_engine \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  --display_name=adk_simple_bot \
  adk_simple_bot

# ── Option B: Cloud Run ───────────────────────────────────────
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
adk deploy cloud_run \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  --service_name=adk-simple-bot \
  adk_simple_bot

# ── Option C: GKE ─────────────────────────────────────────────
gcloud services enable container.googleapis.com
gcloud container clusters create-auto adk-agents-cluster --region=us-central1
adk deploy gke \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  --cluster=adk-agents-cluster \
  adk_simple_bot
```

---

## Useful Resources

| Resource | Link |
|---|---|
| ADK Official Documentation | https://adk.dev |
| Google Cloud Console | https://console.cloud.google.com |
| Vertex AI Agent Engine Docs | https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine |
| Cloud Run Documentation | https://cloud.google.com/run/docs |
| GKE Documentation | https://cloud.google.com/kubernetes-engine/docs |
| Google AI Studio (API Keys) | https://aistudio.google.com/app/api-keys |
| Secret Manager | https://cloud.google.com/secret-manager/docs |
| Artifact Registry | https://cloud.google.com/artifact-registry/docs |

---

*Google ADK Deployment Guide &nbsp;|&nbsp; Agent: `adk_simple_bot` &nbsp;|&nbsp; Platform: Google Cloud Platform &nbsp;|&nbsp; August 2026*
