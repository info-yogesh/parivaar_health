"""
vault/services/report_extractor.py

Responsibilities:
  1. Build base64 payload from uploaded file (PDF or image)
  2. Call Azure OpenAI GPT-4o with a strict structured extraction prompt
  3. Parse and validate JSON response
  4. Persist result into ReportExtraction model

PDF handling:
  Azure OpenAI Vision does NOT accept PDFs as image_url content.
  PDFs are converted page-by-page to PNG images in memory using PyMuPDF (fitz),
  then each page is sent as a separate base64 image_url block in one message.
  Only the first MAX_PDF_PAGES pages are sent to stay within token limits.

Install dependency:
  pip install PyMuPDF

Celery upgrade path (zero code change to caller):
  # tasks.py
  from celery import shared_task
  from vault.services.report_extractor import run_extraction

  @shared_task(bind=True, max_retries=3)
  def extract_report_task(self, report_id: str):
      run_extraction(report_id)

  Then in signals.py replace the threading block with:
      extract_report_task.delay(str(report.pk))
"""

import base64
import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — set via environment variables or settings.py
# ---------------------------------------------------------------------------
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")

# Max PDF pages to send — lab reports rarely need more than 15 pages
# Higher = more complete but higher token cost and latency
MAX_PDF_PAGES = 15

# PNG render DPI — 150 is sharp enough for text, 200 for dense tables
PDF_RENDER_DPI = 150

# ---------------------------------------------------------------------------
# Extraction prompt
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM_PROMPT = """
You are a precise medical report parser. Extract ALL test parameters from the provided health/lab report.

Return ONLY a valid JSON object. No markdown fences. No explanation. No preamble. Just the JSON.

Use this exact schema — include only sections that have data in the report:

{
  "patient": {
    "name": "string or null",
    "age": "string or null",
    "gender": "string or null",
    "booking_id": "string or null",
    "collection_date": "YYYY-MM-DD or null",
    "lab_name": "string or null",
    "report_title": "string or null"
  },
  "sections": {
    "complete_blood_count": {
      "haemoglobin": {
        "value": 16.3,
        "unit": "g/dL",
        "reference_range": "13.0-17.0",
        "status": "normal"
      }
    },
    "biochemistry": {},
    "liver_function_test": {},
    "kidney_function_test": {},
    "lipid_profile": {},
    "thyroid_function": {},
    "urine_routine": {},
    "vitamins_minerals": {},
    "other": {}
  },
  "health_summary": {
    "health_score": 86,
    "concern_parameters": ["cholesterol_total", "triglycerides"],
    "normal_parameters": ["haemoglobin", "fasting_blood_sugar"],
    "not_taken_parameters": ["vitamin_d", "hba1c", "vitamin_b12"]
  }
}

Parameter object rules:
  - "value": numeric (float/int) or string result, null if not taken
  - "unit": measurement unit string, null if not applicable
  - "reference_range": bio reference interval as string, null if not available
  - "status": exactly one of: "normal", "low", "high", "concern", "not_taken"
    - Use "concern" when value is borderline or slightly outside range
    - Use "high"/"low" for clearly abnormal values
    - Use "not_taken" when test was listed but not performed

Additional rules:
  1. Use snake_case for all parameter keys (e.g., "total_leucocyte_count")
  2. Only include sections with actual data — omit empty sections entirely
  3. Do NOT fabricate values — only extract what is explicitly in the report
  4. health_score: extract if shown in report, otherwise null
  5. You are receiving a multi-page report as multiple images — combine ALL pages into one response
  6. Return ONLY the JSON object. Absolutely no markdown or extra text.
"""


# ---------------------------------------------------------------------------
# PDF → list of base64 PNG images (one per page)
# ---------------------------------------------------------------------------

def _pdf_pages_to_base64_images(file_path: str) -> list[str]:
    """
    Convert each page of a PDF to a base64-encoded PNG string.

    Uses PyMuPDF (fitz) — install with: pip install PyMuPDF

    Returns:
        List of base64 strings, one per page (capped at MAX_PDF_PAGES).

    Raises:
        ImportError  if PyMuPDF is not installed
        RuntimeError if PDF cannot be opened/rendered
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF extraction. "
            "Install it with: pip install PyMuPDF"
        )

    doc = fitz.open(file_path)
    total_pages = len(doc)
    pages_to_render = min(total_pages, MAX_PDF_PAGES)

    if total_pages > MAX_PDF_PAGES:
        logger.warning(
            "PDF %s has %d pages — only first %d will be extracted.",
            file_path, total_pages, MAX_PDF_PAGES,
        )

    # fitz Matrix scales the render — 1.0 = 72 DPI, so scale = DPI/72
    zoom = PDF_RENDER_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    b64_pages = []
    for page_num in range(pages_to_render):
        page = doc.load_page(page_num)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pixmap.tobytes("png")
        b64_pages.append(base64.b64encode(png_bytes).decode("utf-8"))

    doc.close()
    logger.info(
        "Rendered %d/%d pages from PDF %s at %d DPI.",
        pages_to_render, total_pages, file_path, PDF_RENDER_DPI,
    )
    return b64_pages


# ---------------------------------------------------------------------------
# Image → single base64 string
# ---------------------------------------------------------------------------

def _image_to_base64(file_path: str) -> tuple[str, str]:
    """
    Read an image file and return (base64_string, mime_type).
    Supports: jpg, jpeg, png, webp, gif
    """
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime_type = mime_map.get(ext, "image/jpeg")
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8"), mime_type


# ---------------------------------------------------------------------------
# Message builder
# ---------------------------------------------------------------------------

def _build_messages(file_path: str) -> list:
    """
    Build the messages array for Azure OpenAI.

    PDF:   Render all pages as PNGs → send each as a separate image_url block
    Image: Send the single file as one image_url block

    Azure OpenAI Vision accepts multiple image_url blocks per user message.
    """
    ext = os.path.splitext(file_path)[1].lower()
    is_pdf = ext == ".pdf"

    # Build the image content blocks
    image_blocks = []

    if is_pdf:
        b64_pages = _pdf_pages_to_base64_images(file_path)
        for i, b64 in enumerate(b64_pages, start=1):
            image_blocks.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}",
                    "detail": "high",
                },
            })
        user_text = (
            f"This is a {len(b64_pages)}-page medical lab report. "
            f"Extract ALL health parameters from ALL pages and combine into one JSON response. "
            f"Return only the JSON object as specified."
        )
    else:
        b64, mime_type = _image_to_base64(file_path)
        image_blocks.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{b64}",
                "detail": "high",
            },
        })
        user_text = (
            "Extract all health parameters from this medical lab report image. "
            "Return only the JSON object as specified."
        )

    return [
        {
            "role": "system",
            "content": EXTRACTION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                *image_blocks,  # unpack all page image blocks
            ],
        },
    ]


def _parse_response(raw_content: str) -> dict:
    """
    Parse the model's text response into a Python dict.
    Strips markdown fences if the model ignored the instruction.
    Raises ValueError if JSON is invalid.
    """
    clean = raw_content.strip()
    # Strip ```json ... ``` or ``` ... ``` wrappers
    clean = re.sub(r"^```(?:json)?\s*", "", clean)
    clean = re.sub(r"\s*```$", "", clean).strip()
    return json.loads(clean)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_azure_extraction(file_path: str) -> dict:
    """
    Send file to Azure OpenAI and return structured extraction result.

    PDF flow:
        PDF → PyMuPDF renders each page as PNG in memory
            → each page sent as a separate base64 image_url block
            → single API call with N image blocks (one per page)

    Image flow:
        JPG/PNG → read bytes → base64 encode → single image_url block

    Returns:
        {"success": True, "data": {...}}      on success
        {"success": False, "error": "..."}    on any failure

    This function is pure — no Django model imports, fully unit-testable.
    """
    if not AZURE_OPENAI_API_KEY:
        return {"success": False, "error": "AZURE_OPENAI_API_KEY is not configured."}

    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".webp"):
        return {
            "success": False,
            "error": f"Unsupported file type '{ext}'. Supported: PDF, JPG, JPEG, PNG.",
        }

    # Build messages — this is where PDF→PNG conversion happens for PDFs
    try:
        messages = _build_messages(file_path)
    except ImportError:
        return {
            "success": False,
            "error": (
                "PyMuPDF is required to process PDF files. "
                "Run: pip install PyMuPDF"
            ),
        }
    except Exception as exc:
        logger.exception("Failed to build messages for %s: %s", file_path, exc)
        return {"success": False, "error": f"Could not read file: {exc}"}

    url = (
        f"{AZURE_OPENAI_ENDPOINT}"
        f"openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions"
        f"?api-version={AZURE_OPENAI_API_VERSION}"
    )
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY,
    }
    payload = {
        "messages": messages,
        "max_tokens": 4000,
        "temperature": 0,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        raw_content = response.json()["choices"][0]["message"]["content"]
        structured_data = _parse_response(raw_content)

        logger.info("Extraction succeeded for file: %s", file_path)
        return {"success": True, "data": structured_data}

    except requests.exceptions.Timeout:
        logger.error("Azure OpenAI request timed out for %s", file_path)
        return {"success": False, "error": "Request timed out. Please retry."}

    except requests.exceptions.HTTPError as exc:
        logger.error(
            "Azure OpenAI HTTP error %s for %s: %s",
            exc.response.status_code,
            file_path,
            exc.response.text[:500],
        )
        return {"success": False, "error": f"API returned HTTP {exc.response.status_code}."}

    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed for %s: %s", file_path, exc)
        return {"success": False, "error": "Could not parse API response as JSON."}

    except Exception as exc:
        logger.exception("Unexpected extraction error for %s: %s", file_path, exc)
        return {"success": False, "error": str(exc)}


def run_extraction(report_id: str) -> None:
    """
    Orchestration function: fetch Report → create/update ReportExtraction → call API → persist.

    Called from:
      - vault/signals.py (thread target)
      - Future: Celery @shared_task wrapping this function

    Args:
        report_id: str representation of the Report UUID PK
    """
    # Late import — avoids circular imports at module load, safe in thread/task context
    from django.utils import timezone
    from vault.models import Report, ReportExtraction

    # --- Fetch Report ---
    try:
        report = Report.objects.select_related().get(pk=report_id)
    except Report.DoesNotExist:
        logger.error("run_extraction: Report %s not found.", report_id)
        return

    if not report.file:
        logger.info("run_extraction: Report %s has no file — skipping.", report_id)
        return

    # --- Get or create ReportExtraction row ---
    extraction, created = ReportExtraction.objects.get_or_create(
        report=report,
        defaults={"status": ReportExtraction.Status.PENDING},
    )

    if not created and extraction.is_completed():
        logger.info(
            "run_extraction: Report %s already has completed extraction — skipping.", report_id
        )
        return

    # --- Mark as processing ---
    extraction.status = ReportExtraction.Status.PROCESSING
    extraction.error_message = ""
    extraction.save(update_fields=["status", "error_message", "updated_at"])

    # --- Call Azure OpenAI ---
    file_path = report.file.path
    result = call_azure_extraction(file_path)

    # --- Persist result ---
    if result["success"]:
        extraction.status = ReportExtraction.Status.COMPLETED
        extraction.raw_data = result["data"]
        extraction.extracted_at = timezone.now()
        extraction.save(update_fields=["status", "raw_data", "extracted_at", "updated_at"])
        logger.info("run_extraction: Completed for Report %s.", report_id)
    else:
        extraction.status = ReportExtraction.Status.FAILED
        extraction.error_message = result["error"]
        extraction.save(update_fields=["status", "error_message", "updated_at"])
        logger.warning(
            "run_extraction: Failed for Report %s — %s", report_id, result["error"]
        )