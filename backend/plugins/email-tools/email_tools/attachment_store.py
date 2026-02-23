"""Per-user attachment store for downloaded email files with auto PDF decryption."""
import logging
import os
from pathlib import Path
from typing import Generator

from .credential_store import _sanitize_for_filesystem

logger = logging.getLogger(__name__)


class AttachmentStore:
    """Per-user attachment storage for downloaded email files.

    Stores attachments in: data/{username}/email_attachments/{provider}/{message_id}/{filename}
    """

    def __init__(self, username: str, data_dir: Path | None = None):
        if not username:
            raise ValueError("Username is required for attachment storage")

        if data_dir is None:
            data_dir_env = os.environ.get("DATA_DIR")
            if not data_dir_env:
                raise ValueError("DATA_DIR environment variable is required for email tools")
            data_dir = Path(data_dir_env)

        self._username = username
        self._user_dir = data_dir / username
        self._attachments_dir = self._user_dir / "email_attachments"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create attachment directories if they don't exist."""
        self._attachments_dir.mkdir(parents=True, exist_ok=True)

    def _get_provider_dir(self, provider: str) -> Path:
        """Get or create the attachment directory for a provider."""
        safe_provider = _sanitize_for_filesystem(provider)
        if not safe_provider:
            raise ValueError(f"Invalid provider name: {provider}")
        provider_dir = self._attachments_dir / safe_provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        return provider_dir

    def get_message_dir(self, provider: str, message_id: str) -> Path:
        """Get or create the attachment directory for a specific message."""
        provider_dir = self._get_provider_dir(provider)
        safe_id = _sanitize_for_filesystem(message_id)
        message_dir = provider_dir / safe_id
        message_dir.mkdir(parents=True, exist_ok=True)
        return message_dir

    def save_attachment(
        self,
        provider: str,
        message_id: str,
        filename: str,
        content: bytes,
        decrypt_pdf: bool = True,
    ) -> Path:
        """Save an attachment, auto-decrypting PDFs for admin users."""
        message_dir = self.get_message_dir(provider, message_id)
        safe_filename = _sanitize_for_filesystem(filename, allowed_extra="._-")
        filepath = message_dir / safe_filename

        if decrypt_pdf and self._username == "admin" and filename.lower().endswith(".pdf"):
            content = self._try_decrypt_pdf(content, filename) or content

        try:
            with open(filepath, "wb") as f:
                f.write(content)
            logger.info(f"Saved attachment: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Failed to save attachment {filename}: {e}")
            raise

    def _try_decrypt_pdf(self, content: bytes, filename: str) -> bytes | None:
        """Attempt to decrypt a PDF attachment. Returns None on failure."""
        try:
            import tempfile
            from .pdf_decrypt import decrypt_pdf_with_passwords

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            try:
                success, message, decrypted = decrypt_pdf_with_passwords(tmp_path)
                if success and decrypted:
                    logger.info(f"Decrypted PDF attachment: {filename} - {message}")
                    return decrypted
                elif message and message != "PDF is not password-protected":
                    logger.debug(f"PDF decryption ({filename}): {message}")
            finally:
                tmp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.debug(f"PDF decryption attempt failed ({filename}): {e}")

        return None

    def get_attachment_path(
        self,
        provider: str,
        message_id: str,
        filename: str,
    ) -> Path | None:
        """Get path to a saved attachment, or None if not found."""
        message_dir = self.get_message_dir(provider, message_id)
        safe_filename = _sanitize_for_filesystem(filename, allowed_extra="._-")
        filepath = message_dir / safe_filename
        return filepath if filepath.exists() else None

    def list_attachments(self, provider: str, message_id: str) -> list[Path]:
        """List all attachment file paths for a message."""
        message_dir = self.get_message_dir(provider, message_id)
        if not message_dir.exists():
            return []
        return [f for f in message_dir.iterdir() if f.is_file()]

    def delete_message_attachments(self, provider: str, message_id: str) -> bool:
        """Delete all attachments for a message. Returns True if deleted."""
        message_dir = self.get_message_dir(provider, message_id)

        if not message_dir.exists():
            return False

        try:
            for filepath in message_dir.iterdir():
                if filepath.is_file():
                    filepath.unlink()
            message_dir.rmdir()
            logger.info(f"Deleted attachments for message {message_id}")
            return True
        except IOError as e:
            logger.error(f"Failed to delete attachments: {e}")
            return False

    def get_total_size(self) -> int:
        """Get total size of all attachments in bytes."""
        try:
            return sum(
                f.stat().st_size
                for f in self._attachments_dir.rglob("*")
                if f.is_file()
            )
        except OSError as e:
            logger.error(f"Failed to calculate total size: {e}")
            return 0

    def list_all_attachments(self) -> Generator[tuple[str, str, Path], None, None]:
        """Yield (provider, message_id, filepath) for all stored attachments."""
        if not self._attachments_dir.exists():
            return

        for provider_dir in self._attachments_dir.iterdir():
            if not provider_dir.is_dir():
                continue
            provider = provider_dir.name
            for message_dir in provider_dir.iterdir():
                if not message_dir.is_dir():
                    continue
                message_id = message_dir.name
                for filepath in message_dir.iterdir():
                    if filepath.is_file():
                        yield (provider, message_id, filepath)


def get_attachment_store(username: str, data_dir: Path | None = None) -> AttachmentStore:
    """Get an attachment store for a user."""
    return AttachmentStore(username, data_dir)
