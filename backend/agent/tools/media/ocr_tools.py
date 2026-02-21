"""OCR tool implementations.

Extract text from images and PDFs using GLM-OCR service.
"""
import logging
from pathlib import Path
from typing import Any

import httpx
from claude_agent_sdk import tool
from .clients.ocr_client import OCRClient
from .helpers import sanitize_file_path, validate_file_format, make_tool_result, make_tool_error
from .config import OCR_FORMATS

logger = logging.getLogger(__name__)


@tool(
    name="perform_ocr",
    description=(
        "Extract text from images or PDF documents using OCR. "
        "Supports PDF, PNG, JPG, JPEG, TIFF, BMP, WEBP formats. "
        "Returns structured text with layout detection, semantic tags, and page separators. "
        "Optionally applies Vietnamese text corrections if enabled. "
        "Input files should be uploaded via the file upload API and will be processed from the session's file storage. "
        "The file path should be relative to the session's input directory (e.g., 'document.pdf')."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the image or PDF file to process (relative to session's input directory, e.g., 'document.pdf')."
            },
            "apply_vietnamese_corrections": {
                "type": "boolean",
                "description": "Apply Vietnamese text corrections (default: false).",
                "default": False
            }
        },
        "required": ["file_path"]
    }
)
async def perform_ocr(inputs: dict[str, Any]) -> dict[str, Any]:
    """Perform OCR on a file."""
    try:
        from .mcp_server import get_username, get_session_id
        from agent.core.file_storage import FileStorage
        from api.services.file_download_token import create_download_token, build_download_url

        username = get_username()
        session_id = get_session_id()
        file_path = inputs["file_path"]
        apply_vi = inputs.get("apply_vietnamese_corrections", False)

        file_storage = FileStorage(username=username, session_id=session_id)
        input_dir = file_storage.get_session_dir() / "input"
        full_path = sanitize_file_path(file_path, input_dir)
        validate_file_format(full_path, OCR_FORMATS, "OCR")

        if not full_path.exists():
            return make_tool_error(f"File not found: {file_path}")

        async with OCRClient() as client:
            result = await client.process_file(
                file_path=full_path,
                apply_vietnamese_corrections=apply_vi
            )

        # Save transcript to output directory
        output_filename = f"{Path(file_path).stem}_ocr.txt"
        metadata = await file_storage.save_output_file(
            output_filename,
            result["text"].encode()
        )

        relative_path = f"{session_id}/output/{metadata.safe_name}"
        token = create_download_token(
            username=username,
            cwd_id=session_id,
            relative_path=relative_path,
            expire_hours=24
        )
        download_url = build_download_url(token)

        return make_tool_result({
            "text": result["text"],
            "output_path": relative_path,
            "download_url": download_url,
            "processing_time_ms": result.get("processing_time_ms"),
            "pages": result.get("pages"),
            "has_vietnamese_corrections": apply_vi
        })
    except ValueError as e:
        return make_tool_error(str(e))
    except httpx.ConnectError:
        return make_tool_error("Cannot connect to OCR service at localhost:18013. Is the Docker container running?")
    except httpx.TimeoutException:
        return make_tool_error("OCR service timed out (120s). File may be too large.")
    except httpx.HTTPStatusError as e:
        return make_tool_error(f"OCR service error: {e.response.status_code}")
    except Exception as e:
        logger.exception("Unexpected error in perform_ocr")
        return make_tool_error(f"Unexpected error: {e}")


__all__ = ["perform_ocr"]
