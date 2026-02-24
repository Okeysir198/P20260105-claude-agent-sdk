"""HTML email template utilities for professional email generation."""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _get_default_brand_name() -> str:
    """Get default brand name from settings."""
    try:
        from core.settings import get_settings
        return get_settings().platform.bot_name
    except Exception:
        return "Trung Assistant Bot"


def _escape_html(text: str) -> str:
    """Escape HTML entities (&, <, >, ", ') for security."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#39;")
    return text


def format_body_as_html(text: str) -> str:
    """Convert plain text to styled HTML paragraphs with <br> line breaks."""
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
    """Create a styled HTML list (ordered or unordered)."""
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
    """Create a styled call-to-action button for email."""
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
    brand_name: str = "",
    brand_color: str = "#2563eb",
    footer_text: str = "Powered by Claude Agent SDK",
) -> MIMEMultipart:
    """Create a complete branded HTML email with header, body, and footer."""
    # Use default brand name from settings if not provided
    if not brand_name:
        brand_name = _get_default_brand_name()

    msg = MIMEMultipart("alternative")
    if subject:
        msg["Subject"] = subject

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

    html_part = MIMEText(html_template, "html", "utf-8")
    msg.attach(html_part)

    return msg
