# Vertex AI Agent Engine CLI & Python Reference Commands

This document contains a reference list of commands used for deploying, testing, running, and deleting the ADK Agent on Google Cloud Vertex AI Agent Engine.

---

## 🚀 1. Deploying the Agent

To package and deploy the local agent source code to Vertex AI Agent Engine, run:

```bash
uv run adk deploy agent_engine \
  --project=email-copilotmy-project-20497 \
  --region=us-central1 \
  --display_name="adk_simple_bot" \
  adk_simple_bot
```

*This command automatically builds the environment package, creates the container, and provisions the Vertex AI Reasoning Engine instance.*

---

## 🧪 2. Testing the Agent

### A. Local Integration Script
To run the automated multi-turn test script that queries the active Reasoning Engine instance directly:

```bash
uv run python test_deployed_agent.py
```

### B. Local API Server (Proxy Server)
To run the secure FastAPI proxy server that exposes the endpoints for frontend consumption:

```bash
uv run uvicorn api_server:app --host 0.0.0.0 --port 8080 --reload
```

---

## 🧹 3. Deleting the Agent & Resources

### A. Force-Deleting the Reasoning Engine (Python Script)
Because reasoning engines contain active sessions (child resources), they must be force-deleted. Execute this Python command in your terminal to delete the engine:

```bash
uv run python -c "
import google.cloud.aiplatform_v1beta1 as gapic
from google.cloud import aiplatform

aiplatform.init(project='email-copilotmy-project-20497', location='us-central1')

client = gapic.ReasoningEngineServiceClient(
    client_options={'api_endpoint': 'us-central1-aiplatform.googleapis.com'}
)

# Replace <ENGINE_ID> with your active engine ID (e.g., 7211680823664181248)
request = gapic.DeleteReasoningEngineRequest(
    name='projects/206644930711/locations/us-central1/reasoningEngines/<ENGINE_ID>',
    force=True
)

print('Deleting reasoning engine...')
operation = client.delete_reasoning_engine(request=request)
operation.result()
print('Deletion complete!')
"
```

### B. Checking and Deleting Container Repositories
To list any Docker repositories created during the container build process:

```bash
gcloud artifacts repositories list --project=email-copilotmy-project-20497
```

To delete a specific repository:

```bash
gcloud artifacts repositories delete REPOSITORY_NAME --location=us-central1 --project=email-copilotmy-project-20497
```

### C. Checking and Deleting Staging Buckets
To list Cloud Storage staging buckets:

```bash
gcloud storage buckets list --project=email-copilotmy-project-20497
```

To delete a staging bucket recursively:

```bash
gcloud storage buckets delete gs://BUCKET_NAME --recursive
```
