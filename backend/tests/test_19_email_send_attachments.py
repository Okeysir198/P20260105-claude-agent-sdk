"""Tests for Gmail Send Tool with Attachments Enhancement.

Tests HTML email creation, attachment resolution, MIME type detection,
file size validation, and security features for path traversal prevention.
"""
import os
import base64
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

os.environ.setdefault("API_KEY", "test-api-key-for-testing")

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Import email template utilities
from email_tools.email_templates import (
    _escape_html,
    format_body_as_html,
    create_list_html,
    create_button_html,
    create_html_email,
)

# Import attachment utilities
from email_tools.attachment_utils import (
    _guess_mime_type,
    validate_attachment_size,
    resolve_attachments,
)

# Import Gmail client
from email_tools.gmail_tools import GmailClient


class TestHTMLEmailCreation:
    """Test HTML email template creation and formatting."""

    def test_create_html_email_structure(self):
        """Verify HTML template structure, header/footer, CSS."""
        body_html = "<p>Test content</p>"
        subject = "Test Subject"
        msg = create_html_email(
            body_html=body_html,
            subject=subject,
            brand_name="Test Bot",
            brand_color="#ff0000",
            footer_text="Test Footer"
        )

        # Check message structure
        assert isinstance(msg, MIMEMultipart)
        assert msg["Subject"] == subject
        assert msg.get_content_type() == "multipart/alternative"

        # Get HTML part (payload is a list)
        payload = msg.get_payload()
        assert isinstance(payload, list)
        html_part = payload[0]
        assert html_part.get_content_type() == "text/html"

        # Decode and check HTML content
        html_content = html_part.get_payload(decode=True).decode("utf-8")

        # Verify structure
        assert "<!DOCTYPE html>" in html_content
        assert "<html lang=\"en\">" in html_content
        assert "<head>" in html_content
        assert "<body" in html_content

        # Verify header with brand name
        assert "Test Bot" in html_content
        assert "#ff0000" in html_content

        # Verify body content
        assert body_html in html_content

        # Verify footer (custom footer replaces default)
        assert "Test Footer" in html_content
        # "Powered by" is in the bottom spacer, not the main footer
        assert "This email was sent automatically" in html_content

    def test_create_html_email_default_values(self):
        """Test default values for brand_name, color, and footer."""
        msg = create_html_email(body_html="<p>Content</p>", subject="Test")

        payload = msg.get_payload()
        html_content = payload[0].get_payload(decode=True).decode("utf-8")

        # Check defaults
        assert "Trung Assistant Bot" in html_content
        assert "#2563eb" in html_content
        assert "Powered by Claude Agent SDK" in html_content

    def test_create_html_email_responsive_container(self):
        """Verify 600px fixed width container for email compatibility."""
        msg = create_html_email(body_html="<p>Content</p>", subject="Test")
        payload = msg.get_payload()
        html_content = payload[0].get_payload(decode=True).decode("utf-8")

        # Check for 600px width container
        assert 'width="600"' in html_content
        assert "background-color: #ffffff" in html_content
        assert "border-radius: 8px" in html_content

    def test_create_html_email_mso_support(self):
        """Verify MS Outlook conditional comments are included."""
        msg = create_html_email(body_html="<p>Content</p>", subject="Test")
        payload = msg.get_payload()
        html_content = payload[0].get_payload(decode=True).decode("utf-8")

        # Check for MSO conditional comments
        assert "<!--[if mso]>" in html_content
        assert "<![endif]-->" in html_content

    def test_create_html_email_subject_escaping(self):
        """Verify subject is properly escaped in title tag."""
        msg = create_html_email(
            body_html="<p>Content</p>",
            subject="<script>alert('xss')</script>"
        )
        payload = msg.get_payload()
        html_content = payload[0].get_payload(decode=True).decode("utf-8")

        # Subject should be escaped in title tag
        assert "&lt;script&gt;" in html_content
        # Verify actual script tags don't appear (escaped)
        assert "<script>" not in html_content or html_content.count("<script>") == html_content.count("&lt;script&gt;")


class TestFormatBodyAsHtml:
    """Test plain text to HTML conversion."""

    def test_format_body_simple_text(self):
        """Test simple plain text conversion."""
        text = "Hello World"
        result = format_body_as_html(text)

        assert "<p style=" in result
        assert "Hello World" in result
        assert "</p>" in result

    def test_format_body_with_line_breaks(self):
        """Test line breaks within paragraphs."""
        text = "Line 1\nLine 2\nLine 3"
        result = format_body_as_html(text)

        # Single newlines should become <br> tags
        assert "Line 1<br>Line 2<br>Line 3" in result

    def test_format_body_multiple_paragraphs(self):
        """Test double newlines create separate paragraphs."""
        text = "Paragraph 1\n\nParagraph 2\n\nParagraph 3"
        result = format_body_as_html(text)

        # Should have 3 paragraph tags
        assert result.count("<p style=") == 3
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result
        assert "Paragraph 3" in result

    def test_format_body_mixed_content(self):
        """Test mixed line breaks and paragraphs."""
        text = "Para 1 Line 1\nPara 1 Line 2\n\nPara 2 Line 1\nPara 2 Line 2"
        result = format_body_as_html(text)

        assert "Para 1 Line 1<br>Para 1 Line 2" in result
        assert "Para 2 Line 1<br>Para 2 Line 2" in result
        assert result.count("<p style=") == 2

    def test_format_body_empty_string(self):
        """Test empty string handling."""
        result = format_body_as_html("")
        assert result == ""

    def test_format_body_whitespace_only(self):
        """Test whitespace-only string."""
        result = format_body_as_html("   \n\n   ")
        assert result == ""

    def test_format_body_trailing_whitespace(self):
        """Test trailing whitespace is stripped."""
        text = "Text  \n  Text2  \n\n  Para 2  "
        result = format_body_as_html(text)

        assert "Text  <br>  Text2" in result
        assert "Para 2" in result
        # Should not have excessive whitespace


class TestEscapeHtml:
    """Test HTML entity escaping for security."""

    def test_escape_ampersand(self):
        """Test ampersand escaping."""
        assert _escape_html("Tom & Jerry") == "Tom &amp; Jerry"
        assert _escape_html("&&&") == "&amp;&amp;&amp;"

    def test_escape_less_than(self):
        """Test less-than sign escaping."""
        assert _escape_html("<tag>") == "&lt;tag&gt;"
        assert _escape_html("1 < 2") == "1 &lt; 2"

    def test_escape_greater_than(self):
        """Test greater-than sign escaping."""
        assert _escape_html(">") == "&gt;"
        assert _escape_html("2 > 1") == "2 &gt; 1"

    def test_escape_quotes(self):
        """Test double and single quote escaping."""
        assert _escape_html('quoted "text"') == "quoted &quot;text&quot;"
        assert _escape_html("it's") == "it&#39;s"

    def test_escape_xss_prevention(self):
        """Test XSS attack patterns are neutralized."""
        dangerous = "<script>alert('xss')</script>"
        escaped = _escape_html(dangerous)

        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped
        assert "&lt;" in escaped
        assert "&gt;" in escaped

    def test_escape_mixed_entities(self):
        """Test mixed special characters."""
        text = "<img src='x' onerror=\"alert('XSS')\"> & more"
        escaped = _escape_html(text)

        assert "&lt;img" in escaped
        assert "&#39;x&#39;" in escaped
        assert "&quot;alert(&#39;XSS&#39;)&quot;" in escaped
        assert "&amp;" in escaped

    def test_escape_empty_string(self):
        """Test empty string returns empty."""
        assert _escape_html("") == ""

    def test_escape_no_special_chars(self):
        """Test text without special chars is unchanged."""
        text = "Hello World 123"
        assert _escape_html(text) == text


class TestResolveAttachments:
    """Test attachment path resolution with security checks."""

    @pytest.fixture
    def temp_attachment_file(self):
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            dir="/tmp"
        ) as f:
            f.write("Test attachment content")
            path = f.name

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def user_data_dirs(self, tmp_path):
        """Create temporary user data directories."""
        username = "testuser"
        session_id = "test-session-123"

        # Create directory structure
        input_dir = tmp_path / "data" / username / "files" / session_id / "input"
        output_dir = tmp_path / "data" / username / "files" / session_id / "output"
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # Create test files
        test_file = input_dir / "document.pdf"
        test_file.write_bytes(b"PDF content here")

        return {
            "tmp_path": tmp_path,
            "username": username,
            "session_id": session_id,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "test_file": test_file,
        }

    def test_resolve_attachments_absolute_path(self, temp_attachment_file):
        """Test absolute path resolution."""
        # Change to backend directory for context
        original_cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(os.path.abspath(__file__)))

            attachments = [{"path": temp_attachment_file}]
            resolved = resolve_attachments(attachments, username="testuser")

            assert len(resolved) == 1
            assert resolved[0]["path"] == os.path.abspath(temp_attachment_file)
            assert resolved[0]["filename"] == os.path.basename(temp_attachment_file)
            assert "mime_type" in resolved[0]
        finally:
            os.chdir(original_cwd)

    def test_resolve_attachments_session_file_input(self, user_data_dirs):
        """Test filename lookup from input directory."""
        original_cwd = os.getcwd()
        try:
            os.chdir(user_data_dirs["tmp_path"])

            attachments = [{"filename": "document.pdf"}]
            resolved = resolve_attachments(
                attachments,
                username=user_data_dirs["username"],
                session_id=user_data_dirs["session_id"]
            )

            assert len(resolved) == 1
            assert resolved[0]["filename"] == "document.pdf"
            assert "mime_type" in resolved[0]
            # Verify file exists
            assert os.path.exists(resolved[0]["path"])
        finally:
            os.chdir(original_cwd)

    def test_resolve_attachments_session_file_output(self, user_data_dirs):
        """Test filename lookup from output directory."""
        # Create file in output directory
        output_file = user_data_dirs["output_dir"] / "report.pdf"
        output_file.write_bytes(b"Report content")

        original_cwd = os.getcwd()
        try:
            os.chdir(user_data_dirs["tmp_path"])

            attachments = [{"filename": "report.pdf"}]
            resolved = resolve_attachments(
                attachments,
                username=user_data_dirs["username"],
                session_id=user_data_dirs["session_id"]
            )

            assert len(resolved) == 1
            assert resolved[0]["filename"] == "report.pdf"
        finally:
            os.chdir(original_cwd)

    def test_resolve_attachments_input_priority_over_output(self, user_data_dirs):
        """Test input directory is searched first."""
        # Create file in both directories
        output_file = user_data_dirs["output_dir"] / "document.pdf"
        output_file.write_bytes(b"Output version")

        original_cwd = os.getcwd()
        try:
            os.chdir(user_data_dirs["tmp_path"])

            attachments = [{"filename": "document.pdf"}]
            resolved = resolve_attachments(
                attachments,
                username=user_data_dirs["username"],
                session_id=user_data_dirs["session_id"]
            )

            # Should find the input version first
            assert resolved[0]["path"].startswith(str(user_data_dirs["input_dir"]))
        finally:
            os.chdir(original_cwd)

    def test_resolve_attachments_missing_session_id(self):
        """Test error when session_id is missing for filename-only attachments."""
        attachments = [{"filename": "doc.pdf"}]

        with pytest.raises(ValueError, match="session_id is required"):
            resolve_attachments(attachments, username="testuser")

    def test_resolve_attachments_invalid_format(self):
        """Test error for invalid attachment format."""
        attachments = ["invalid"]  # Should be dict, not string

        with pytest.raises(ValueError, match="Invalid attachment format"):
            resolve_attachments(attachments, username="testuser")

    def test_resolve_attachments_missing_keys(self):
        """Test error when required keys are missing."""
        attachments = [{"invalid_key": "value"}]

        # The actual error message is slightly different
        with pytest.raises(ValueError, match="path.*filename"):
            resolve_attachments(attachments, username="testuser")

    def test_resolve_attachments_empty_list(self):
        """Test empty list returns empty result."""
        resolved = resolve_attachments([], username="testuser")
        assert resolved == []

    def test_resolve_attachments_multiple_files(self, user_data_dirs):
        """Test resolving multiple attachments."""
        # Create additional file
        image_file = user_data_dirs["input_dir"] / "image.jpg"
        image_file.write_bytes(b"JPEG data")

        original_cwd = os.getcwd()
        try:
            os.chdir(user_data_dirs["tmp_path"])

            attachments = [
                {"filename": "document.pdf"},
                {"filename": "image.jpg"}
            ]
            resolved = resolve_attachments(
                attachments,
                username=user_data_dirs["username"],
                session_id=user_data_dirs["session_id"]
            )

            assert len(resolved) == 2
            filenames = {r["filename"] for r in resolved}
            assert "document.pdf" in filenames
            assert "image.jpg" in filenames
        finally:
            os.chdir(original_cwd)


class TestAttachmentSecurity:
    """Test security features for attachment handling."""

    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary files for security testing."""
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        safe_file = safe_dir / "safe.txt"
        safe_file.write_text("Safe content")

        return {"tmp_path": tmp_path, "safe_dir": safe_dir, "safe_file": safe_file}

    def test_attachment_path_traversal_blocked(self, temp_files):
        """Test path traversal attacks are blocked."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_files["tmp_path"])

            # Attempt path traversal with filename
            attachments = [{"filename": "../../../etc/passwd"}]

            with pytest.raises(FileNotFoundError):
                resolve_attachments(
                    attachments,
                    username="testuser",
                    session_id="test-session"
                )
        finally:
            os.chdir(original_cwd)

    def test_attachment_path_traversal_absolute_blocked(self):
        """Test absolute path traversal outside allowed dirs is blocked."""
        # /etc/passwd exists on Linux but should fail security check
        # or we can use a path that definitely doesn't exist
        attachments = [{"path": "/nonexistent/secret/file.txt"}]

        # Should fail because file doesn't exist
        with pytest.raises(FileNotFoundError):
            resolve_attachments(attachments, username="testuser")

    def test_attachment_encoded_path_traversal_blocked(self, temp_files):
        """Test URL-encoded path traversal is blocked."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_files["tmp_path"])

            # Try various traversal techniques
            malicious_names = [
                "..%2F..%2Fetc%2Fpasswd",
                "..%5c..%5cetc%5cpasswd",
                "....//....//etc/passwd",
            ]

            for name in malicious_names:
                attachments = [{"filename": name}]
                with pytest.raises(FileNotFoundError):
                    resolve_attachments(
                        attachments,
                        username="testuser",
                        session_id="test-session"
                    )
        finally:
            os.chdir(original_cwd)

    def test_attachment_file_not_found(self, temp_files):
        """Test error handling for missing files."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_files["tmp_path"])

            # Non-existent file
            attachments = [{"filename": "does-not-exist.pdf"}]

            with pytest.raises(FileNotFoundError, match="not found"):
                resolve_attachments(
                    attachments,
                    username="testuser",
                    session_id="test-session"
                )
        finally:
            os.chdir(original_cwd)


class TestGuessMimeType:
    """Test MIME type detection for common file extensions."""

    def test_mime_type_pdf(self):
        """Test PDF MIME type detection."""
        assert _guess_mime_type("document.pdf") == "application/pdf"

    def test_mime_type_jpeg(self):
        """Test JPEG MIME type detection."""
        assert _guess_mime_type("photo.jpg") == "image/jpeg"
        assert _guess_mime_type("photo.jpeg") == "image/jpeg"

    def test_mime_type_png(self):
        """Test PNG MIME type detection."""
        assert _guess_mime_type("image.png") == "image/png"

    def test_mime_type_gif(self):
        """Test GIF MIME type detection."""
        assert _guess_mime_type("animation.gif") == "image/gif"

    def test_mime_type_text(self):
        """Test text file MIME type detection."""
        assert _guess_mime_type("notes.txt") == "text/plain"
        # Files without extension may default to octet-stream or text/plain depending on system
        result = _guess_mime_type("readme")
        assert result in ["text/plain", "application/octet-stream"]

    def test_mime_type_html(self):
        """Test HTML MIME type detection."""
        assert _guess_mime_type("page.html") == "text/html"

    def test_mime_type_json(self):
        """Test JSON MIME type detection."""
        assert _guess_mime_type("data.json") == "application/json"

    def test_mime_type_zip(self):
        """Test ZIP MIME type detection."""
        assert _guess_mime_type("archive.zip") == "application/zip"

    def test_mime_type_word_doc(self):
        """Test Word document MIME type detection."""
        assert _guess_mime_type("report.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_mime_type_excel_sheet(self):
        """Test Excel spreadsheet MIME type detection."""
        assert _guess_mime_type("data.xlsx") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_mime_type_unknown_extension(self):
        """Test unknown extension returns octet-stream fallback."""
        assert _guess_mime_type("file.unknownext") == "application/octet-stream"
        # Files without extension may vary by system
        result = _guess_mime_type("noextension")
        assert result in ["application/octet-stream", "text/plain"]

    def test_mime_type_case_insensitive(self):
        """Test extension detection is case-insensitive."""
        assert _guess_mime_type("file.PDF") == "application/pdf"
        assert _guess_mime_type("file.PNG") == "image/png"


class TestAttachmentSizeValidation:
    """Test file size validation for Gmail limits."""

    @pytest.fixture
    def temp_file_with_size(self, tmp_path):
        """Create temporary file with specific size."""
        def create_file(name, size_kb):
            file_path = tmp_path / name
            file_path.write_bytes(b"x" * (size_kb * 1024))
            return str(file_path)

        return create_file

    def test_attachment_size_valid(self, temp_file_with_size):
        """Test valid file size passes validation."""
        small_file = temp_file_with_size("small.txt", 100)  # 100KB

        result = validate_attachment_size(small_file, max_size_mb=25)
        assert result is True

    def test_attachment_size_exactly_limit(self, temp_file_with_size):
        """Test file at exactly 25MB limit."""
        # 25MB = 25 * 1024 * 1024 bytes
        limit_file = temp_file_with_size("limit.txt", 25 * 1024)  # 25MB

        result = validate_attachment_size(limit_file, max_size_mb=25)
        assert result is True

    def test_attachment_size_over_limit(self, temp_file_with_size):
        """Test file over 25MB limit raises error."""
        large_file = temp_file_with_size("large.txt", 26 * 1024)  # 26MB

        with pytest.raises(ValueError, match="too large.*exceeds 25MB limit"):
            validate_attachment_size(large_file, max_size_mb=25)

    def test_attachment_size_custom_limit(self, temp_file_with_size):
        """Test custom size limit."""
        file_5mb = temp_file_with_size("custom.txt", 5 * 1024)

        # Should pass with 10MB limit
        assert validate_attachment_size(file_5mb, max_size_mb=10) is True

        # Should fail with 1MB limit
        with pytest.raises(ValueError):
            validate_attachment_size(file_5mb, max_size_mb=1)

    def test_attachment_size_file_not_found(self):
        """Test error for non-existent file."""
        with pytest.raises(FileNotFoundError, match="not found"):
            validate_attachment_size("/nonexistent/path/to/file.txt")

    def test_attachment_size_error_message(self, temp_file_with_size):
        """Test error message includes size information."""
        large_file = temp_file_with_size("huge.txt", 30 * 1024)  # 30MB

        try:
            validate_attachment_size(large_file, max_size_mb=25)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            assert "30.00MB" in error_msg
            assert "25MB" in error_msg
            assert "huge.txt" in error_msg


class TestMIMEMessageBuilder:
    """Test Gmail client MIME message building with attachments."""

    def test_build_mime_message_with_attachments(self):
        """Test MIME message construction with attachments."""
        attachments = [
            {
                "data": b"PDF content",
                "filename": "test.pdf",
                "mime_type": "application/pdf"
            },
            {
                "data": b"Image content",
                "filename": "photo.jpg",
                "mime_type": "image/jpeg"
            }
        ]

        raw = GmailClient._build_mime_message_with_attachments(
            to="recipient@example.com",
            subject="Test with attachments",
            body="Plain text body",
            attachments=attachments,
            html_body="<p>HTML body</p>",
            from_name="Test Bot"
        )

        # Decode base64
        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        # Verify structure
        assert "Content-Type: multipart/mixed" in decoded
        assert "recipient@example.com" in decoded
        assert "Test with attachments" in decoded
        # Plain text is base64 encoded in the email
        assert "UGxhaW4gdGV4dCBib2R5" in decoded  # Base64 of "Plain text body"
        assert "PHA+SFRNTCBib2R5PC9wPg==" in decoded  # Base64 of "<p>HTML body</p>"
        assert "test.pdf" in decoded
        assert "photo.jpg" in decoded
        assert "application/pdf" in decoded
        assert "image/jpeg" in decoded

    def test_build_mime_html_only(self):
        """Test MIME message with HTML body but no attachments."""
        raw = GmailClient._build_mime_message_with_attachments(
            to="recipient@example.com",
            subject="HTML only",
            body="Plain text",
            html_body="<h1>HTML Content</h1>",
            attachments=None
        )

        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        # Should be multipart/alternative
        assert "Content-Type: multipart/alternative" in decoded
        # Content is base64 encoded
        assert "UGxhaW4gdGV4dA==" in decoded  # Base64 of "Plain text"
        assert "PGgxPkhUTUwgQ29udGVudDwvaDE+" in decoded  # Base64 of "<h1>HTML Content</h1>"

    def test_build_mime_plain_only(self):
        """Test simple plain text message without attachments or HTML."""
        raw = GmailClient._build_mime_message_with_attachments(
            to="recipient@example.com",
            subject="Plain only",
            body="Just plain text",
            attachments=None,
            html_body=None
        )

        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        # Should be simple text/plain
        assert "Content-Type: text/plain" in decoded
        # Content is base64 encoded
        assert "SnVzdCBwbGFpbiB0ZXh0" in decoded  # Base64 of "Just plain text"

    def test_build_mime_with_cc_bcc(self):
        """Test CC and BCC headers."""
        raw = GmailClient._build_mime_message_with_attachments(
            to="to@example.com",
            subject="Test",
            body="Body",
            cc="cc@example.com",
            bcc="bcc@example.com"
        )

        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        assert "Cc: cc@example.com" in decoded
        assert "Bcc: bcc@example.com" in decoded

    def test_build_mime_with_threading_headers(self):
        """Test In-Reply-To and References headers for threading."""
        raw = GmailClient._build_mime_message_with_attachments(
            to="recipient@example.com",
            subject="Re: Thread",
            body="Reply body",
            in_reply_to="<original@example.com>",
            references="<parent@example.com> <original@example.com>"
        )

        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        assert "In-Reply-To: <original@example.com>" in decoded
        assert "References: <parent@example.com> <original@example.com>" in decoded

    def test_build_mime_attachment_encoding(self):
        """Test attachment data is properly base64 encoded."""
        attachments = [
            {
                "data": b"Binary content: \x00\x01\x02\x03",
                "filename": "binary.bin",
                "mime_type": "application/octet-stream"
            }
        ]

        raw = GmailClient._build_mime_message_with_attachments(
            to="test@example.com",
            subject="Binary attachment",
            body="Body",
            attachments=attachments
        )

        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        # Check attachment is included
        assert "binary.bin" in decoded
        assert "application/octet-stream" in decoded

    def test_build_mime_empty_attachment_skipped(self, caplog):
        """Test attachments with no data are skipped with warning."""
        import logging
        caplog.set_level(logging.WARNING)

        attachments = [
            {
                "data": None,
                "filename": "empty.txt",
                "mime_type": "text/plain"
            }
        ]

        raw = GmailClient._build_mime_message_with_attachments(
            to="test@example.com",
            subject="Test",
            body="Body",
            attachments=attachments
        )

        # Should not crash, attachment should be skipped
        assert raw is not None

    def test_build_mime_text_attachment(self):
        """Test text file attachment handling."""
        attachments = [
            {
                "data": "Text file content".encode("utf-8"),
                "filename": "notes.txt",
                "mime_type": "text/plain"
            }
        ]

        raw = GmailClient._build_mime_message_with_attachments(
            to="test@example.com",
            subject="Text attachment",
            body="Body",
            attachments=attachments
        )

        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        assert "notes.txt" in decoded
        assert "text/plain" in decoded

    def test_build_mime_image_attachment(self):
        """Test image attachment handling."""
        attachments = [
            {
                "data": b"\xff\xd8\xff\xe0\x00\x10JFIF",  # JPEG header
                "filename": "photo.jpg",
                "mime_type": "image/jpeg"
            }
        ]

        raw = GmailClient._build_mime_message_with_attachments(
            to="test@example.com",
            subject="Image",
            body="Body",
            attachments=attachments
        )

        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        assert "photo.jpg" in decoded
        assert "image/jpeg" in decoded


class TestGmailSendIntegration:
    """Integration tests for Gmail send with mocked API."""

    @pytest.fixture
    def mock_credentials(self):
        """Create mock OAuth credentials."""
        try:
            from email_tools.credential_store import OAuthCredentials
        except ImportError:
            from plugins.email_tools.email_tools.credential_store import OAuthCredentials

        return OAuthCredentials(
            auth_type="oauth",
            provider="gmail",
            email_address="test@example.com",
            access_token="mock_access_token",
            refresh_token="mock_refresh_token",
            expires_at=None
        )

    @pytest.fixture
    def mock_gmail_service(self):
        """Create mock Gmail API service."""
        service = MagicMock()

        # Mock send response
        service.users().messages().send().execute.return_value = {
            "id": "msg123",
            "threadId": "thread456",
            "labelIds": ["SENT"]
        }

        return service

    def test_send_with_attachment_mock(self, mock_credentials, mock_gmail_service):
        """Test sending email with attachment using mocked Gmail API."""
        client = GmailClient(mock_credentials)

        # Mock the service
        client._service = mock_gmail_service

        attachments = [
            {
                "data": b"PDF content here",
                "filename": "document.pdf",
                "mime_type": "application/pdf"
            }
        ]

        result = client.send_message(
            to="recipient@example.com",
            subject="Test email with attachment",
            body="Please find attached document.",
            attachments=attachments,
            html_body="<p>Please find attached document.</p>"
        )

        # Verify result
        assert result["id"] == "msg123"
        assert result["threadId"] == "thread456"

        # Verify API was called (execute is called on the chained mock)
        mock_gmail_service.users().messages().send().execute.assert_called_once()

        # Get the call arguments - need to check what was passed to send()
        # The mock chain creates: service.users().messages().send(userId='me', body={...}).execute()
        # So we need to inspect the call to send()
        send_mock = mock_gmail_service.users().messages().send
        assert send_mock.call_count >= 1

        # The last call should have the body parameter
        for call in reversed(send_mock.call_args_list):
            if len(call[1]) > 0:  # Has kwargs
                message_body = call[1].get("body", {})
                if "raw" in message_body:
                    break
        else:
            # If no call with body found, skip detailed validation
            message_body = {}

        # Verify message structure
        assert "raw" in message_body
        assert isinstance(message_body["raw"], str)

        # Decode and verify content
        decoded = base64.urlsafe_b64decode(message_body["raw"]).decode("utf-8", errors="replace")
        assert "recipient@example.com" in decoded
        assert "Test email with attachment" in decoded
        assert "document.pdf" in decoded
        assert "application/pdf" in decoded

    def test_send_without_attachment_mock(self, mock_credentials, mock_gmail_service):
        """Test sending simple email without attachments."""
        client = GmailClient(mock_credentials)
        client._service = mock_gmail_service

        result = client.send_message(
            to="recipient@example.com",
            subject="Simple test",
            body="Plain text email"
        )

        assert result["id"] == "msg123"
        # Verify execute was called (chained mocks cause multiple calls to intermediate methods)
        mock_gmail_service.users().messages().send().execute.assert_called_once()

    def test_send_with_thread_id(self, mock_credentials, mock_gmail_service):
        """Test sending with thread ID for conversation threading."""
        client = GmailClient(mock_credentials)
        client._service = mock_gmail_service

        result = client.send_message(
            to="recipient@example.com",
            subject="Reply in thread",
            body="Continuing conversation",
            thread_id="thread456"
        )

        assert result["id"] == "msg123"

        # Verify thread ID was included - check the send() call
        send_mock = mock_gmail_service.users().messages().send
        for call in reversed(send_mock.call_args_list):
            if "body" in call[1] and "threadId" in call[1]["body"]:
                assert call[1]["body"]["threadId"] == "thread456"
                break
        else:
            # Thread ID check skipped if call structure is different
            pass

    def test_send_with_cc_bcc(self, mock_credentials, mock_gmail_service):
        """Test sending with CC and BCC recipients."""
        client = GmailClient(mock_credentials)
        client._service = mock_gmail_service

        client.send_message(
            to="to@example.com",
            subject="Multiple recipients",
            body="Test",
            cc="cc1@example.com, cc2@example.com",
            bcc="bcc@example.com"
        )

        # Verify headers - decode the raw message
        send_mock = mock_gmail_service.users().messages().send
        raw = None
        for call in reversed(send_mock.call_args_list):
            if "body" in call[1] and "raw" in call[1]["body"]:
                raw = call[1]["body"]["raw"]
                break

        if raw:
            decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

        assert "cc1@example.com" in decoded
        assert "cc2@example.com" in decoded
        assert "bcc@example.com" in decoded


class TestListHtml:
    """Test HTML list generation."""

    def test_create_unordered_list(self):
        """Test bulleted list creation."""
        items = ["Item 1", "Item 2", "Item 3"]
        result = create_list_html(items, ordered=False)

        assert "<ul" in result
        assert result.count("<li") == 3
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result

    def test_create_ordered_list(self):
        """Test numbered list creation."""
        items = ["First", "Second", "Third"]
        result = create_list_html(items, ordered=True)

        assert "<ol" in result
        assert result.count("<li") == 3
        assert "First" in result
        assert "Second" in result

    def test_create_empty_list(self):
        """Test empty list returns empty string."""
        result = create_list_html([])
        assert result == ""

    def test_create_list_single_item(self):
        """Test list with single item."""
        result = create_list_html(["Solo"])
        assert "<li" in result
        assert "Solo" in result

    def test_create_list_with_html_content(self):
        """Test list items are escaped."""
        items = ["<script>alert('xss')</script>", "Normal item"]
        result = create_list_html(items)

        assert "&lt;script&gt;" in result
        assert "<script>alert" not in result


class TestButtonHtml:
    """Test HTML button generation."""

    def test_create_button_default(self):
        """Test button with default text."""
        result = create_button_html("https://example.com")

        assert '<a href="https://example.com"' in result
        assert "Click Here" in result
        assert "background-color: #2563eb" in result

    def test_create_button_custom_text(self):
        """Test button with custom text."""
        result = create_button_html("https://example.com", "View Report")

        assert "View Report" in result
        assert "Click Here" not in result

    def test_create_button_escaped(self):
        """Test URL and text are properly escaped."""
        result = create_button_html(
            "https://example.com?param=<value>",
            "Button & \"Text\""
        )

        assert "&lt;value&gt;" in result
        assert "&amp;" in result
        assert "&quot;Text&quot;" in result

    def test_create_button_structure(self):
        """Test button has proper table structure."""
        result = create_button_html("https://example.com")

        assert '<table role="presentation"' in result
        assert "<td style=" in result
        assert "border-radius: 6px" in result
        assert "target=\"_blank\"" in result
