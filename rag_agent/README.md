# 🧠 Vertex AI RAG Agent (Google ADK)

An autonomous Retrieval Augmented Generation (RAG) agent built on the **Google Agent Development Kit (ADK)** and powered by **Google Cloud Vertex AI RAG Engine** and **Vertex AI Vector Search**.

---

## 1. Overview & Capabilities

`RagAgent` enables conversational interaction with document corpora stored in Google Cloud Vertex AI:

- **Corpus Management**: Create, list, inspect, and delete managed vector corpora.
- **Data Ingestion**: Add documents from **Google Drive**, **Google Docs/Sheets/Slides**, or **Google Cloud Storage (`gs://`)** with automatic semantic chunking and embedding generation via `text-embedding-005`.
- **Grounded Semantic Retrieval**: Query documents using approximate nearest neighbor vector search with similarity distance thresholds, returning factual answers with source citations.
- **Session State Tracking**: Automatically retains the active corpus across conversational turns so you don't need to repeat resource names.

---

## 2. Tools Summary

| Tool Name                     | Source File                                             | Purpose                                                                                              |
| :---------------------------- | :------------------------------------------------------ | :--------------------------------------------------------------------------------------------------- |
| **`rag_query`**       | [`tools/rag_query.py`](tools/rag_query.py)             | Performs dense vector retrieval on a corpus using `top_k=3` and `vector_distance_threshold=0.5`. |
| **`list_corpora`**    | [`tools/list_corpora.py`](tools/list_corpora.py)       | Lists all available RAG corpora in your GCP project and location.                                    |
| **`create_corpus`**   | [`tools/create_corpus.py`](tools/create_corpus.py)     | Creates a new managed corpus using `text-embedding-005` and `RagManagedDb`.                      |
| **`add_data`**        | [`tools/add_data.py`](tools/add_data.py)               | Ingests Google Drive URLs or GCS paths with chunking (`chunk_size=512`, `overlap=100`).          |
| **`get_corpus_info`** | [`tools/get_corpus_info.py`](tools/get_corpus_info.py) | Retrieves detailed corpus statistics and list of indexed file IDs.                                   |
| **`delete_document`** | [`tools/delete_document.py`](tools/delete_document.py) | Deletes a specific file/document from a corpus.                                                      |
| **`delete_corpus`**   | [`tools/delete_corpus.py`](tools/delete_corpus.py)     | Deletes an entire corpus and its indexed vectors (requires `confirm=True`).                        |

---

## 3. Quickstart & GCP Configuration

### Prerequisites & GCP Settings

1. **Enable GCP APIs**:
   ```bash
   gcloud services enable aiplatform.googleapis.com vectorsearch.googleapis.com storage.googleapis.com drive.googleapis.com --project=YOUR_PROJECT_ID
   ```
2. **Authenticate Local Environment**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **Configure Environment Variables (`.env`)**:
   ```env
   GOOGLE_CLOUD_PROJECT=your-gcp-project-id
   GOOGLE_CLOUD_LOCATION=asia-south1
   GOOGLE_API_KEY=your-gemini-api-key
   ```
4. **Grant Access to the Vertex AI Service Agent**:
   - Service Agent: `service-{PROJECT_NUM}@gcp-sa-aiplatform.iam.gserviceaccount.com`
   - Grant `Storage Object Viewer` on your GCS bucket, or share Drive files/folders with this email as **Viewer**.

---

## 4. Running the Agent

Start the agent using the ADK Web UI:

```bash
adk web rag_agent
```

### Detailed Documentation

For in-depth guides, operational commands, and architectural breakdowns:

- 💻 **[Complete gcloud Commands Guide (Login to Deployment)](documents/command.md)**
- 📖 **[Architecture, Tool Execution &amp; GCP Setup Guide](documents/rag_agent_architecture_and_gcp_guide.md)**
