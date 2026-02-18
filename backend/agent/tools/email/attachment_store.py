"""Attachment store for downloaded email attachments.

Stores downloaded email attachments in per-user directories.
"""
import logging
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)


class AttachmentStore:
    """Per-user attachment storage for downloaded email files.

    Stores attachments in: data/{username}/email_attachments/{provider}/{message_id}/{filename}
    """

    def __init__(self, username: str, data_dir: Path | None = None):
        """Initialize attachment store for a user.

        Args:
            username: Username for data isolation
            data_dir: Optional data directory path
        """
        if not username:
            raise ValueError("Username is required for attachment storage")

        if data_dir is None:
            from agent.core.storage import get_data_dir
            data_dir = get_data_dir()

        self._username = username
        self._user_dir = data_dir / username
        self._attachments_dir = self._user_dir / "email_attachments"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create attachment directories if they don't exist."""
        self._attachments_dir.mkdir(parents=True, exist_ok=True)

    def _get_provider_dir(self, provider: str) -> Path:
        """Get the attachment directory for a provider.

        Args:
            provider: Provider name (e.g., "gmail", "yahoo", "outlook", "icloud", "zoho", "custom")

        Returns:
            Path to the provider's attachment directory
        """
        # Sanitize provider name for filesystem safety (same pattern as credential store)
        safe_provider = "".join(c for c in provider if c.isalnum() or c in "-_")
        if not safe_provider:
            raise ValueError(f"Invalid provider name: {provider}")
        provider_dir = self._attachments_dir / safe_provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        return provider_dir

    def get_message_dir(self, provider: str, message_id: str) -> Path:
        """Get the attachment directory for a specific message.

        Args:
            provider: Provider name (e.g., "gmail", "yahoo", "outlook")
            message_id: Message ID from email provider

        Returns:
            Path to the message's attachment directory
        """
        provider_dir = self._get_provider_dir(provider)
        # Sanitize message ID for filesystem safety
        safe_id = "".join(c for c in message_id if c.isalnum() or c in "-_")
        message_dir = provider_dir / safe_id
        message_dir.mkdir(parents=True, exist_ok=True)
        return message_dir

    def save_attachment(
        self,
        provider: str,
        message_id: str,
        filename: str,
        content: bytes
    ) -> Path:
        """Save an attachment to storage.

        Args:
            provider: Provider name (e.g., "gmail", "yahoo", "outlook")
            message_id: Message ID from email provider
            filename: Original filename of the attachment
            content: Attachment content as bytes

        Returns:
            Path to the saved attachment file
        """
        message_dir = self.get_message_dir(provider, message_id)
        # Sanitize filename for filesystem safety
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        filepath = message_dir / safe_filename

        try:
            with open(filepath, "wb") as f:
                f.write(content)
            logger.info(f"Saved attachment: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Failed to save attachment {filename}: {e}")
            raise

    def get_attachment_path(
        self,
        provider: str,
        message_id: str,
        filename: str
    ) -> Path | None:
        """Get the path to a saved attachment.

        Args:
            provider: Provider name (e.g., "gmail", "yahoo", "outlook")
            message_id: Message ID from email provider
            filename: Original filename of the attachment

        Returns:
            Path to the attachment file, or None if not found
        """
        message_dir = self.get_message_dir(provider, message_id)
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        filepath = message_dir / safe_filename

        if filepath.exists():
            return filepath
        return None

    def list_attachments(
        self,
        provider: str,
        message_id: str
    ) -> list[Path]:
        """List all attachments for a message.

        Args:
            provider: Provider name (e.g., "gmail", "yahoo", "outlook")
            message_id: Message ID from email provider

        Returns:
            List of paths to attachment files
        """
        message_dir = self.get_message_dir(provider, message_id)
        if not message_dir.exists():
            return []
        return [f for f in message_dir.iterdir() if f.is_file()]

    def delete_message_attachments(self, provider: str, message_id: str) -> bool:
        """Delete all attachments for a message.

        Args:
            provider: Provider name (e.g., "gmail", "yahoo", "outlook")
            message_id: Message ID from email provider

        Returns:
            True if attachments were deleted, False if directory not found
        """
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
        """Get total size of all attachments in bytes.

        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for filepath in self._attachments_dir.rglob("*"):
                if filepath.is_file():
                    total_size += filepath.stat().st_size
        except OSError as e:
            logger.error(f"Failed to calculate total size: {e}")
        return total_size

    def list_all_attachments(self) -> Generator[tuple[str, str, Path], None, None]:
        """List all attachments across all messages and providers.

        Yields:
            Tuples of (provider, message_id, filepath)
        """
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
    """Get an attachment store for a user.

    Args:
        username: Username for data isolation
        data_dir: Optional data directory path

    Returns:
        AttachmentStore instance for the user

    Raises:
        ValueError: If username is empty or None
    """
    return AttachmentStore(username, data_dir)
