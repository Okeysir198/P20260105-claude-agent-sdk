"""PDF decryption utility for password-protected PDFs.

Supports multiple password attempts from environment variables.
Used primarily for bank statements downloaded from email attachments.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# PDF passwords from environment variables (for bank statements)
_PDF_PASSWORDS: list[str] = []


def load_pdf_passwords() -> None:
    """Load PDF passwords from environment variables."""
    global _PDF_PASSWORDS
    import os

    passwords = [
        os.getenv("PDF_PASSWORD_HSBC", ""),
        os.getenv("PDF_PASSWORD_VIB_CASHBACK", ""),
        os.getenv("PDF_PASSWORD_VIB_BOUNDLESS", ""),
        os.getenv("PDF_PASSWORD_DEFAULT", ""),
    ]
    _PDF_PASSWORDS = [p for p in passwords if p]
    if _PDF_PASSWORDS:
        logger.debug(f"Loaded {len(_PDF_PASSWORDS)} PDF password(s) from environment")


def get_pdf_passwords() -> list[str]:
    """Get list of configured PDF passwords.

    Returns:
        List of non-empty password strings
    """
    if not _PDF_PASSWORDS:
        load_pdf_passwords()
    return _PDF_PASSWORDS.copy()


def decrypt_pdf_with_passwords(
    pdf_path: Path,
    passwords: list[str] | None = None,
) -> tuple[bool, str, bytes | None]:
    """Attempt to decrypt a PDF using provided or configured passwords.

    Args:
        pdf_path: Path to the PDF file
        passwords: Optional list of passwords to try. If None, uses env var passwords.

    Returns:
        Tuple of (success: bool, message: str, decrypted_content: bytes|None)
    """
    if passwords is None:
        passwords = get_pdf_passwords()

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))

        # Check if PDF is encrypted
        if not reader.is_encrypted:
            # Not encrypted - return original content
            with open(pdf_path, "rb") as f:
                content = f.read()
            return True, "PDF is not password-protected", content

        # PDF is encrypted - try to decrypt
        if not passwords:
            return False, "PDF is password-protected but no passwords configured", None

        # Try each password
        for i, password in enumerate(passwords, 1):
            try:
                result = reader.decrypt(password)
                # result: 0=failed, 1=user password, 2=owner password
                if result > 0:
                    # Successfully decrypted - write to bytes
                    from io import BytesIO

                    output = BytesIO()
                    from pypdf import PdfWriter

                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)

                    writer.write(output)
                    decrypted_content = output.getvalue()

                    logger.info(f"Decrypted PDF with password #{i} (first 2 chars: {password[:2]}**)")
                    return True, f"Decrypted with password #{i}", decrypted_content

            except Exception as e:
                logger.debug(f"Password #{i} failed: {e}")
                continue

        return False, f"Failed to decrypt with {len(passwords)} password(s)", None

    except ImportError:
        return False, "pypdf not installed - run: pip install pypdf", None
    except Exception as e:
        return False, f"Error decrypting PDF: {e}", None


def is_pdf_encrypted(pdf_path: Path) -> bool:
    """Check if a PDF file is encrypted.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        True if PDF is encrypted, False otherwise
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        return reader.is_encrypted
    except Exception:
        return False


def decrypt_pdf_to_file(
    pdf_path: Path,
    output_path: Path,
    passwords: list[str] | None = None,
) -> tuple[bool, str]:
    """Decrypt a PDF and save to a new file.

    Args:
        pdf_path: Path to the encrypted PDF
        output_path: Path to save the decrypted PDF
        passwords: Optional list of passwords to try

    Returns:
        Tuple of (success: bool, message: str)
    """
    success, message, content = decrypt_pdf_with_passwords(pdf_path, passwords)

    if success and content:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(content)
            return True, message
        except Exception as e:
            return False, f"Failed to save decrypted PDF: {e}"

    return success, message


# Auto-load passwords on module import
load_pdf_passwords()
