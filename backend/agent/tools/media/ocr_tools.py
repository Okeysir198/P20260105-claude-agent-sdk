"""OCR tool implementations.

Extract text from images and PDFs using GLM-OCR service.
"""
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from .clients.ocr_client import OCRClient
from .config import OCR_FORMATS
from .helpers import (
    get_session_context,
    handle_media_service_errors,
    make_tool_result,
    resolve_input_file,
    save_output_and_build_url,
)


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
@handle_media_service_errors("OCR")
async def perform_ocr(inputs: dict[str, Any]) -> dict[str, Any]:
    """Perform OCR on a file."""
    file_path = inputs["file_path"]
    apply_vi = inputs.get("apply_vietnamese_corrections", False)

    username, file_storage = get_session_context()
    session_id = file_storage._session_id
    full_path = resolve_input_file(file_path, file_storage, OCR_FORMATS, "OCR")

    async with OCRClient() as client:
        result = await client.process_file(
            file_path=full_path,
            apply_vietnamese_corrections=apply_vi,
        )

    output_filename = f"{Path(file_path).stem}_ocr.txt"
    relative_path, download_url = await save_output_and_build_url(
        file_storage, username, session_id, output_filename, result["text"].encode()
    )

    return make_tool_result({
        "text": result["text"],
        "output_path": relative_path,
        "download_url": download_url,
        "processing_time_ms": result.get("processing_time_ms"),
        "pages": result.get("pages"),
        "has_vietnamese_corrections": apply_vi,
    })


__all__ = ["perform_ocr"]
