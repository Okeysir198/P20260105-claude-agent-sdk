"""
Email template utilities for HTML email generation.

Provides functions to create responsive, HTML emails with inline CSS
for maximum email client compatibility. Uses table-based layout with
a fixed width of 600px and brand-consistent styling.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal


def _escape_html(text: str) -> str:
    """
    Escape HTML entities for security.

    Prevents XSS and ensures proper rendering by converting special
    characters to their HTML entity equivalents.

    Args:
        text: Plain text to escape

    Returns:
        Text with HTML entities escaped (&, <, >, ", ')

    Examples:
        >>> _escape_html("Hello & goodbye <script>")
        'Hello &amp; goodbye &lt;script&gt;'
    """
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#39;")
    return text


def format_body_as_html(text: str) -> str:
    """
    Convert plain text to HTML paragraph format.

    Preserves line breaks by converting them to <br> tags and wraps
    the content in paragraph tags with proper styling.

    Args:
        text: Plain text content to convert

    Returns:
        HTML formatted string with paragraphs and line breaks

    Examples:
        >>> format_body_as_html("Line 1\\nLine 2\\n\\nNew paragraph")
        '<p style="...">Line 1<br>Line 2</p><p style="...">New paragraph</p>'
    """
    escaped_text = _escape_html(text)
    paragraphs = escaped_text.split("\n\n")

    html_parts = []
    for para in paragraphs:
        if para.strip():
            # Convert single newlines to <br> within paragraphs
            lines = para.strip().split("\n")
            para_content = "<br>".join(lines)
            html_parts.append(
                f'<p style="margin: 0 0 16px 0; color: #1f2937; font-size: 16px; line-height: 1.6; font-family: Arial, sans-serif;">{para_content}</p>'
            )

    return "".join(html_parts)


def create_list_html(items: list[str], ordered: bool = False) -> str:
    """
    Create HTML ordered or unordered lists.

    Generates styled lists with proper spacing and indentation for
    email compatibility. Each item is properly escaped.

    Args:
        items: List of strings to include as list items
        ordered: True for <ol> (numbered), False for <ul> (bulleted)

    Returns:
        HTML string containing the complete list

    Examples:
        >>> create_list_html(["Item 1", "Item 2"])
        '<ul style="..."><li style="...">Item 1</li><li style="...">Item 2</li></ul>'
    """
    if not items:
        return ""

    tag = "ol" if ordered else "ul"
    list_style = "margin: 0 0 16px 0; padding-left: 24px; color: #1f2937; font-size: 16px; line-height: 1.6; font-family: Arial, sans-serif;"
    item_style = "margin: 0 0 8px 0;"

    list_items = []
    for item in items:
        escaped_item = _escape_html(item)
        list_items.append(f"<li style=\"{item_style}\">{escaped_item}</li>")

    return f"<{tag} style=\"{list_style}\">{''.join(list_items)}</{tag}>"


def create_button_html(url: str, text: str = "Click Here") -> str:
    """
    Create a call-to-action button HTML.

    Generates a button with inline CSS that works across most email
    clients. Uses the brand color (#2563eb) with hover effect on
    supported clients.

    Args:
        url: The link target URL
        text: Button text (default: "Click Here")

    Returns:
        HTML string containing the button element

    Examples:
        >>> create_button_html("https://example.com", "View Report")
        '<table...><a href="https://example.com"...>View Report</a></table>'
    """
    escaped_text = _escape_html(text)
    escaped_url = _escape_html(url)

    return f"""
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
            <tr>
                <td style="background-color: #2563eb; border-radius: 6px; text-align: center;">
                    <a href="{escaped_url}" style="background-color: #2563eb; border: 1px solid #2563eb; border-radius: 6px; color: #ffffff; display: inline-block; font-size: 16px; font-weight: bold; line-height: 1.5; padding: 12px 24px; text-align: center; text-decoration: none; font-family: Arial, sans-serif; -webkit-text-size-adjust: none; mso-hide: all;" target="_blank">
                        {escaped_text}
                    </a>
                </td>
            </tr>
        </table>
    """


def create_html_email(
    body_html: str,
    subject: str = "",
    brand_name: str = "Trung Assistant Bot",
    brand_color: str = "#2563eb",
    footer_text: str = "Powered by Claude Agent SDK"
) -> MIMEMultipart:
    """
    Create a complete HTML email with header, body, and footer.

    Generates a responsive HTML email with table-based layout, inline CSS
    for maximum email client compatibility, and proper MIME structure.

    Args:
        body_html: HTML content for the email body (main content area)
        subject: Email subject line
        brand_name: Name to display in header (default: "Trung Assistant Bot")
        brand_color: Hex color for branding (default: "#2563eb")
        footer_text: Text to display in footer (default: "Powered by Claude Agent SDK")

    Returns:
        MIMEMultipart message object ready to send via SMTP

    Examples:
        >>> body = "<p>Hello!</p>" + create_button_html("https://example.com")
        >>> msg = create_html_email(body, subject="Welcome")
        >>> # Send via SMTP server
    """
    # Create multipart message
    msg = MIMEMultipart("alternative")
    if subject:
        msg["Subject"] = subject

    # Complete HTML email template
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{_escape_html(subject)}</title>
        <!--[if mso]>
        <style type="text/css">
            body, table, td {{font-family: Arial, sans-serif !important;}}
        </style>
        <![endif]-->
    </head>
    <body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: Arial, sans-serif;">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f3f4f6;">
            <tr>
                <td style="padding: 40px 20px;">
                    <!-- Main Container 600px -->
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background-color: {brand_color}; padding: 24px 32px; border-radius: 8px 8px 0 0; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: bold; font-family: Arial, sans-serif;">
                                    {_escape_html(brand_name)}
                                </h1>
                            </td>
                        </tr>

                        <!-- Body Content -->
                        <tr>
                            <td style="padding: 32px; background-color: #ffffff;">
                                {body_html}
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; background-color: #f9fafb; border-radius: 0 0 8px 8px; border-top: 1px solid #e5e7eb;">
                                <p style="margin: 0; color: #6b7280; font-size: 14px; text-align: center; font-family: Arial, sans-serif;">
                                    {_escape_html(footer_text)}
                                </p>
                            </td>
                        </tr>
                    </table>
                    <!-- End Main Container -->

                    <!-- Bottom Spacer -->
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="margin: 20px auto 0;">
                        <tr>
                            <td style="text-align: center; padding: 20px 0;">
                                <p style="margin: 0; color: #9ca3af; font-size: 12px; font-family: Arial, sans-serif;">
                                    This email was sent automatically. Please do not reply.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Attach HTML part
    html_part = MIMEText(html_template, "html", "utf-8")
    msg.attach(html_part)

    return msg
