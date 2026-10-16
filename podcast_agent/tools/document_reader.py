"""Document Reader Tool (read_document).

This module extracts text content from uploaded files (PDFs, Word documents, plain text):
1. Local File Extraction: Reads directly from disk if a valid local filepath is provided.
2. ADK Session Artifact Extraction: In ADK Web UI, user attachments (via paperclip 📎)
   are uploaded as Session Artifacts. This tool inspects ToolContext.list_artifacts()
   and loads file bytes in-memory via ToolContext.load_artifact().
3. Format Parsing:
   - PDFs parsed via pypdf
   - Word (.docx) parsed via python-docx
   - Plain text/Markdown decoded via utf-8
"""

import base64
import io
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext


# ── 1. Byte Parsing Helper ───────────────────────────────────────────────────

def _parse_bytes_content(data: bytes, ext_hint: str) -> str:
    """Helper to extract clean text from raw file bytes based on format extension."""
    ext = ext_hint.lower().strip()
    
    # ── PDF Parsing ──
    if ext == ".pdf" or data.startswith(b"%PDF"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        extracted = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted.append(f"--- Page {i+1} ---\n{text}")
        return "\n\n".join(extracted) if extracted else "Warning: PDF contains no readable text."

    # ── Word Document (.docx / .doc) Parsing ──
    elif ext in [".docx", ".doc"]:
        import docx
        doc = docx.Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs) if paragraphs else "Warning: Word document contains no text."

    # ── Plain Text / Markdown / CSV / JSON ──
    else:
        return data.decode("utf-8", errors="replace")


# ── 2. Main Document Reading Tool ────────────────────────────────────────────

async def read_document(
    file_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Reads and extracts text from an uploaded document (PDF, Word DOCX, TXT) or a local file.
    
    Compatible with:
    1. Files uploaded via Google ADK Web UI (Session Artifacts like 'job_satisfaction.pdf').
    2. Local filesystem paths (e.g. '/path/to/document.pdf').

    Args:
        file_path: Optional file path or uploaded artifact name. If omitted, the tool
                   automatically looks for any uploaded documents in the current session.
        tool_context: ADK ToolContext injected by the runtime to access session artifacts.

    Returns:
        Extracted text content from the file.
    """
    cleaned_path = file_path.strip().strip("'\"") if file_path else ""

    # ── Block A: Check Local Filesystem First ─────────────────────────────────
    if cleaned_path and os.path.exists(cleaned_path):
        try:
            with open(cleaned_path, "rb") as f:
                content_bytes = f.read()
            ext = os.path.splitext(cleaned_path)[1]
            return _parse_bytes_content(content_bytes, ext)
        except Exception as e:
            return f"Error reading local file '{cleaned_path}': {str(e)}"

    # ── Block B: Query ADK Session Artifacts (Web UI Uploads) ────────────────
    # When files are uploaded in ADK Web, they are stored in the active session's
    # ArtifactService rather than on local disk.
    if tool_context is not None:
        try:
            available_artifacts = await tool_context.list_artifacts()
        except Exception:
            available_artifacts = []

        if available_artifacts:
            target_artifact = None

            # Match by specific filename if requested by user or model
            if cleaned_path:
                target_base = os.path.basename(cleaned_path).lower()
                for art in available_artifacts:
                    if art.lower() == target_base or target_base in art.lower():
                        target_artifact = art
                        break

            # Fallback: Auto-detect most relevant uploaded document
            if not target_artifact:
                doc_candidates = [
                    a for a in available_artifacts
                    if a.lower().endswith((".pdf", ".docx", ".doc", ".txt", ".md", ".csv"))
                ]
                if doc_candidates:
                    target_artifact = doc_candidates[-1]
                else:
                    target_artifact = available_artifacts[-1]

            # Ingest and decode the selected artifact bytes
            try:
                part = await tool_context.load_artifact(filename=target_artifact)
                if not part:
                    return f"Error: Could not load artifact '{target_artifact}' from session."

                # Case 1: Binary data (PDF / DOCX)
                if part.inline_data and part.inline_data.data:
                    raw_data = part.inline_data.data
                    if isinstance(raw_data, str):
                        try:
                            raw_data = base64.b64decode(raw_data)
                        except Exception:
                            raw_data = raw_data.encode("utf-8")
                    ext = os.path.splitext(target_artifact)[1]
                    extracted_text = _parse_bytes_content(raw_data, ext)
                    return f"[Successfully read uploaded session file: '{target_artifact}']\n\n{extracted_text}"

                # Case 2: Text part
                elif part.text:
                    return f"[Successfully read uploaded session file: '{target_artifact}']\n\n{part.text}"

            except Exception as e:
                return f"Error extracting text from uploaded artifact '{target_artifact}': {str(e)}"

    # ── Block C: File Not Found Handler ──────────────────────────────────────
    available_msg = (
        f" Available session files: {available_artifacts}"
        if 'available_artifacts' in locals() and available_artifacts
        else " No uploaded files found in current session."
    )
    return f"Error: Document '{cleaned_path}' was not found on disk or in uploaded session artifacts.{available_msg}"
