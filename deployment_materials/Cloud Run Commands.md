# Cloud Run Deployment and Deletion Reference Commands

This document contains a reference list of commands used for configuring IAM permissions, deploying, testing, running, and deleting the ADK Agent on Google Cloud Run.

---

## 🔑 1. Setting Up IAM Permissions

If Cloud Build fails with permissions errors regarding the default Compute Engine service account during deployment, execute these commands to set the proper permissions:

### A. Grant Impersonation Access (Service Account User)
Allows the Cloud Build agent to act as the default Compute Engine service account:
```bash
gcloud iam service-accounts add-iam-policy-binding \
    206644930711-compute@developer.gserviceaccount.com \
    --member="serviceAccount:206644930711@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --project=email-copilotmy-project-20497 \
    --quiet
```

### B. Grant Project-Level Build Permissions
Grants the default Compute Engine service account the roles needed to read source files, push container images, and write logs:

```bash
# 1. Read access for staged zip files in Cloud Storage
gcloud projects add-iam-policy-binding email-copilotmy-project-20497 \
    --member="serviceAccount:206644930711-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectViewer" \
    --quiet

# 2. Write access to Artifact Registry (for pushing built Docker images)
gcloud projects add-iam-policy-binding email-copilotmy-project-20497 \
    --member="serviceAccount:206644930711-compute@developer.gserviceaccount.com" \
    --role="roles/artifactregistry.writer" \
    --quiet

# 3. Access to stream and write build logs
gcloud projects add-iam-policy-binding email-copilotmy-project-20497 \
    --member="serviceAccount:206644930711-compute@developer.gserviceaccount.com" \
    --role="roles/logging.logWriter" \
    --quiet
```

---

## 🚀 2. Deploying the Agent to Cloud Run

To package and deploy the local agent to Google Cloud Run with CORS enabled:

```bash
uv run adk deploy cloud_run \
  --project=email-copilotmy-project-20497 \
  --region=us-central1 \
  --service_name="adk-simple-bot-service" \
  --allow_origins="*" \
  adk_simple_bot
```

*The `--allow_origins="*"` argument allows web browsers to connect to the Cloud Run endpoint directly without needing a local proxy server.*

---

## 🧪 3. Running & Testing

### A. Local Proxy Server (Port 8081)
To run the secure isolated FastAPI proxy server (if using a backend proxy):
```bash
uv run python backend_cloud_run/api_server_cloud_run.py
```

### B. Automated Integration Test Script
To execute the automated multi-turn test script targeting the Cloud Run service directly:
```bash
uv run python test_deployed_agent_cloud_run.py
```

---

## 🧹 4. Deleting the Deployment & Resources

Execute these commands to remove all provisioned Cloud Run services, repositories, and staging storage files to ensure zero billing:

### A. Delete the Cloud Run Service
```bash
gcloud run services delete adk-simple-bot-service \
  --region=us-central1 \
  --project=email-copilotmy-project-20497 \
  --quiet
```

### B. Delete the Artifact Registry Repository
```bash
gcloud artifacts repositories delete cloud-run-source-deploy \
  --location=us-central1 \
  --project=email-copilotmy-project-20497 \
  --quiet
```

### C. Delete the Cloud Storage Staging Bucket
```bash
gcloud storage rm -r gs://run-sources-email-copilotmy-project-20497-us-central1/ --quiet
```
