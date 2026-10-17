# 🚀 Google Cloud (gcloud) Commands Guide for Vertex AI RAG Agent

This step-by-step operational guide provides all the exact `gcloud` CLI commands required to authenticate, manage projects, configure billing, enable APIs, set up IAM permissions, and populate your `.env` configuration file to run the **Vertex AI RAG Agent**.

---

## Hierarchy Overview

```text
Step 1: Authenticate with Google Cloud (User & ADC Login)
   │
Step 2: Inspect Existing Projects or Create a New GCP Project
   │
Step 3: Link Billing Account (Required for Vertex AI & Vector Search)
   │
Step 4: Set the Active Project & Retrieve Project Number
   │
Step 5: Enable Required Google Cloud APIs
   │
Step 6: Configure IAM Permissions & Vertex AI Service Agent
   │
Step 7: Populate Environment Variables into `.env`
   │
Step 8: Verify Setup & Launch the RAG Agent
```

---

## Step 1: Authenticate with Google Cloud

Authenticate both the Google Cloud CLI and the **Application Default Credentials (ADC)** that Python libraries (like `vertexai` and `google-cloud-*`) use locally.

```bash
# 1. Log in to your Google Cloud user account in the browser
gcloud auth login

# 2. Generate local Application Default Credentials (ADC) for Python SDKs
gcloud auth application-default login
```

> [!NOTE]
> `gcloud auth login` authorizes the `gcloud` CLI tool.
> `gcloud auth application-default login` creates the credentials JSON file on your machine that `vertexai.init()` reads automatically.

---

## Step 2: View Existing Projects or Create a New Project

Check your available GCP projects or provision a dedicated project for the RAG agent.

### Option A: View existing projects

```bash
# List all projects accessible by your authenticated account
gcloud projects list
```

### Option B: Create a brand-new project

```bash
# Define your unique project ID (lowercase letters, numbers, and hyphens)
export PROJECT_ID="my-rag-agent-$(date +%s)"

# Create the GCP project
gcloud projects create ${PROJECT_ID} --name="Vertex AI RAG Agent"
```

---

## Step 3: Link a Billing Account (Required for Vertex AI)

Vertex AI and Vector Search APIs require an active billing account linked to the project.

```bash
# 1. List available billing accounts
gcloud billing accounts list

# 2. Export your chosen billing account ID (format: 012345-6789AB-CDEF01)
export BILLING_ACCOUNT_ID="YOUR_BILLING_ACCOUNT_ID"

# 3. Link the billing account to your project
gcloud billing projects link ${PROJECT_ID} --billing-account=${BILLING_ACCOUNT_ID}
```

---

## Step 4: Set Active Project & Retrieve Project Number

Configure `gcloud` to make your target project the active default and extract the numeric **Project Number** (which is needed to identify the Vertex AI Service Agent).

```bash
# 1. Set the active default project in gcloud
gcloud config set project ${PROJECT_ID}

# 2. Verify the active configuration
gcloud config get-value project

# 3. Retrieve and export your Project Number
export PROJECT_NUM=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
echo "Project ID:     ${PROJECT_ID}"
echo "Project Number: ${PROJECT_NUM}"
```

---

## Step 5: Enable Required Google Cloud APIs

Enable the Vertex AI, Vector Search, Cloud Storage, and Google Drive APIs.

```bash
# Enable all required services in a single command
gcloud services enable \
    aiplatform.googleapis.com \
    vectorsearch.googleapis.com \
    storage.googleapis.com \
    drive.googleapis.com \
    --project=${PROJECT_ID}
```

### Verify Enabled APIs:

```bash
# Check that the APIs are enabled and ready
gcloud services list --enabled --filter="NAME:(aiplatform OR vectorsearch OR storage OR drive)"
```

Expected output:

```text
NAME                         TITLE
aiplatform.googleapis.com    Vertex AI API
drive.googleapis.com         Google Drive API
storage.googleapis.com       Cloud Storage API
vectorsearch.googleapis.com  Vertex AI Vector Search API
```

---

## Step 6: Configure IAM Permissions & Vertex AI Service Agent

### 1. Grant Developer Permissions

Ensure your personal Google identity has access to Vertex AI:

```bash
# Export your Google Cloud email
export USER_EMAIL=$(gcloud config get-value account)

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="user:${USER_EMAIL}" \
    --role="roles/aiplatform.user"
```

### 2. Identify the Vertex AI Service Agent

When you call `add_data` to import documents from Google Cloud Storage or Google Drive, Google's backend **Vertex AI Service Agent** performs the file retrieval:

```bash
# Construct the Service Agent email
export SERVICE_AGENT_EMAIL="service-${PROJECT_NUM}@gcp-sa-aiplatform.iam.gserviceaccount.com"
echo "Vertex AI Service Agent: ${SERVICE_AGENT_EMAIL}"
```

### 3. Grant Permissions to Ingest Data:

#### For Google Cloud Storage (`gs://`):

If your documents are stored in a GCS bucket, grant the service agent read permissions:

```bash
# Create a sample bucket if needed (in us-central1)
export BUCKET_NAME="${PROJECT_ID}-rag-docs"
gcloud storage buckets create gs://${BUCKET_NAME} --location=us-central1

# Grant Storage Object Viewer to the Vertex AI Service Agent
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member="serviceAccount:${SERVICE_AGENT_EMAIL}" \
    --role="roles/storage.objectViewer"
```

#### For Google Drive Files / Folders:

1. Open Google Drive in your web browser.
2. Select the document or folder you want the RAG agent to ingest.
3. Click **Share**.
4. Paste the Service Agent email: `service-{PROJECT_NUM}@gcp-sa-aiplatform.iam.gserviceaccount.com`.
5. Set permission level to **Viewer** and click **Send**.

---

## Step 7: Add Projects & Variables to `.env`

Automatically write the configuration parameters directly to your project's `.env` file in the repository root.

```bash
# Navigate to repository root (if not already there)
cd /Users/sachinmishra/Desktop/Agent_Development_Kit

# Ensure the .env file exists
touch .env

# Ensure PROJECT_ID is set (either from your variable or from active gcloud config)
if [ -z "${PROJECT_ID}" ]; then
  export PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

# Ensure PROJECT_NUM is set (or fetch it dynamically)
if [ -z "${PROJECT_NUM}" ] && [ -n "${PROJECT_ID}" ]; then
  export PROJECT_NUM=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)" 2>/dev/null || echo "")
fi

# Remove any existing GCP config keys to avoid duplicates
sed -i '' '/GOOGLE_CLOUD_PROJECT=/d' .env 2>/dev/null || true
sed -i '' '/GOOGLE_CLOUD_PROJECT_NUM=/d' .env 2>/dev/null || true
sed -i '' '/GOOGLE_CLOUD_LOCATION=/d' .env 2>/dev/null || true

# Append the active GCP configuration into .env
cat <<EOF >> .env
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GOOGLE_CLOUD_PROJECT_NUM=${PROJECT_NUM}
GOOGLE_CLOUD_LOCATION=asia-south1
EOF

# Display the updated .env configuration
cat .env
```

> [!TIP]
> Ensure you also have `GOOGLE_API_KEY=your-gemini-api-key` in your `.env` so Gemini 3.1 Flash Lite can execute within the Google ADK runtime.

---

## Step 8: Verify Setup & Launch the RAG Agent

### Quick Python Initialization Check:

Run a one-line test to verify that `vertexai.init()` connects successfully with your newly configured project:

```bash
python3 -c "
import os, vertexai
from dotenv import load_dotenv
load_dotenv()
project = os.environ.get('GOOGLE_CLOUD_PROJECT')
location = os.environ.get('GOOGLE_CLOUD_LOCATION')
print(f'Testing Vertex AI with project={project}, location={location}')
vertexai.init(project=project, location=location)
print('✅ Vertex AI connection successful!')
"
```

### Launch with Google ADK Web UI:

```bash
adk web rag_agent
```

### Or Run in CLI Interactive Mode:

```bash
adk run rag_agent
```

---

## Quick Reference Summary Cheat Sheet

| Action                       | Single-Line Command                                                                                                          |
| :--------------------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| **Login**              | `gcloud auth login && gcloud auth application-default login`                                                               |
| **List Projects**      | `gcloud projects list`                                                                                                     |
| **Set Project**        | `gcloud config set project <PROJECT_ID>`                                                                                   |
| **Get Project Number** | `gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)"`                              |
| **Enable All APIs**    | `gcloud services enable aiplatform.googleapis.com vectorsearch.googleapis.com storage.googleapis.com drive.googleapis.com` |
| **Launch Agent**       | `adk web rag_agent`                                                                                                        |
