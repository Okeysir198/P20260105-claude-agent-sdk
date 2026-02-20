"""OCR tool implementations.

Extract text from images and PDFs using GLM-OCR service.
"""
import logging
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool
from .clients.ocr_client import OCRClient

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
    """Perform OCR on a file.

    Args:
        inputs: Dict with file_path and optional apply_vietnamese_corrections

    Returns:
        Dict with extracted text and metadata
    """
    from .mcp_server import get_username, get_session_id
    from agent.core.file_storage import FileStorage
    from api.services.file_download_token import create_download_token, build_download_url

    username = get_username()
    session_id = get_session_id()
    file_path = inputs["file_path"]
    apply_vi = inputs.get("apply_vietnamese_corrections", False)

    # Use existing FileStorage
    file_storage = FileStorage(username=username, session_id=session_id)
    full_path = file_storage.get_session_dir() / "input" / file_path

    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Call OCR service
    ocr_client = OCRClient()
    try:
        result = await ocr_client.process_file(
            file_path=full_path,
            apply_vietnamese_corrections=apply_vi
        )

        # Save transcript to output directory
        output_filename = f"{Path(file_path).stem}_ocr.txt"
        metadata = await file_storage.save_output_file(
            output_filename,
            result["text"].encode()
        )

        # Create download token and URL (24 hour expiry)
        relative_path = f"{session_id}/output/{metadata.safe_name}"
        token = create_download_token(
            username=username,
            cwd_id=session_id,
            relative_path=relative_path,
            expire_hours=24
        )
        download_url = build_download_url(token)

        return {
            "text": result["text"],
            "output_path": relative_path,
            "download_url": download_url,
            "processing_time_ms": result.get("processing_time_ms"),
            "pages": result.get("pages"),
            "has_vietnamese_corrections": apply_vi
        }
    finally:
        await ocr_client.close()


__all__ = ["perform_ocr"]
