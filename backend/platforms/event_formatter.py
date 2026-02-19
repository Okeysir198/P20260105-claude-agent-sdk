"""Format agent events for platform-friendly display.

Converts tool_use and tool_result events into concise, readable messages
suitable for messaging platforms (WhatsApp, Telegram, Zalo).
"""

import json
import re

# Delay between message sends to avoid platform rate limits (seconds)
MESSAGE_SEND_DELAY = 0.3

# Max chars for previews
_MAX_PREVIEW = 300
_MAX_RESULT_PREVIEW = 500


def _truncate(text: str, max_len: int = _MAX_PREVIEW) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def format_session_rotated() -> str:
    """Format a notification when an old platform session is rotated."""
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 *Claude Agent - Personal Assistant*\n\n"
        "🔄 Session rotated!\n\n"
        "Previous conversation exceeded the time limit and has been archived. "
        "I won't remember what we discussed before, but feel free to bring me up to speed!\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def format_new_session_requested() -> str:
    """Format a notification when the user explicitly requests a new session."""
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 *Claude Agent - Personal Assistant*\n\n"
        "✨ New session started!\n\n"
        "Previous conversation has been archived. "
        "I'm ready to help you with coding, writing, research, and more. "
        "How can I assist you today?\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def format_tool_use(name: str, input_data: dict | None) -> str:
    """Format a tool_use event for platform display."""
    input_data = input_data or {}

    # --- Read ---
    if name == "Read":
        path = input_data.get("file_path", "")
        parts = [f"📖 *Reading file*"]
        if path:
            parts.append(f"`{_truncate(path)}`")
        offset = input_data.get("offset")
        limit = input_data.get("limit")
        if offset or limit:
            range_info = []
            if offset:
                range_info.append(f"from line {offset}")
            if limit:
                range_info.append(f"{limit} lines")
            parts.append(f"({', '.join(range_info)})")
        return "\n".join(parts)

    # --- Write ---
    if name == "Write":
        path = input_data.get("file_path", "")
        content = input_data.get("content", "")
        line_count = content.count("\n") + 1 if content else 0
        parts = [f"📝 *Writing file*"]
        if path:
            parts.append(f"`{_truncate(path)}`")
        if line_count:
            parts.append(f"({line_count} lines)")
        return "\n".join(parts)

    # --- Edit ---
    if name == "Edit":
        path = input_data.get("file_path", "")
        old = input_data.get("old_string", "")
        new = input_data.get("new_string", "")
        replace_all = input_data.get("replace_all", False)
        parts = [f"✏️ *Editing file*"]
        if path:
            parts.append(f"`{_truncate(path)}`")
        detail = []
        if old:
            old_lines = old.strip().count("\n") + 1
            detail.append(f"replacing {old_lines} line{'s' if old_lines > 1 else ''}")
        if new:
            new_lines = new.strip().count("\n") + 1
            detail.append(f"with {new_lines} line{'s' if new_lines > 1 else ''}")
        if replace_all:
            detail.append("(all occurrences)")
        if detail:
            parts.append(" ".join(detail))
        return "\n".join(parts)

    # --- Glob ---
    if name == "Glob":
        pattern = input_data.get("pattern", "")
        path = input_data.get("path", "")
        parts = [f"🔍 *Searching files*"]
        if pattern:
            parts.append(f"Pattern: `{pattern}`")
        if path:
            parts.append(f"In: `{_truncate(path)}`")
        return "\n".join(parts)

    # --- Grep ---
    if name == "Grep":
        pattern = input_data.get("pattern", "")
        path = input_data.get("path", "")
        glob_filter = input_data.get("glob", "")
        parts = [f"🔎 *Searching content*"]
        if pattern:
            parts.append(f"Pattern: `{_truncate(pattern, 100)}`")
        if path:
            parts.append(f"In: `{_truncate(path)}`")
        if glob_filter:
            parts.append(f"Files: `{glob_filter}`")
        return "\n".join(parts)

    # --- Bash ---
    if name == "Bash":
        command = input_data.get("command", "")
        desc = input_data.get("description", "")
        lines = command.strip().split("\n") if command else []
        parts = [f"⚡ *Running command*"]
        if desc:
            parts.append(desc)
        if lines:
            preview = "\n".join(lines[:3])
            if len(lines) > 3:
                preview += f"\n  … (+{len(lines) - 3} more lines)"
            parts.append(f"```\n{_truncate(preview, _MAX_PREVIEW)}\n```")
        return "\n".join(parts)

    # --- Task ---
    if name == "Task":
        desc = input_data.get("description", "")
        prompt = input_data.get("prompt", "")
        subagent = input_data.get("subagent_type", "")
        parts = [f"🤖 *Launching sub-agent*"]
        if desc:
            parts.append(f"_{desc}_")
        if subagent:
            parts.append(f"Type: {subagent}")
        if prompt:
            parts.append(f"```\n{_truncate(prompt, 150)}\n```")
        return "\n".join(parts)

    # --- WebFetch / WebSearch ---
    if name == "WebFetch":
        url = input_data.get("url", "")
        parts = [f"🌐 *Fetching web page*"]
        if url:
            parts.append(f"`{_truncate(url)}`")
        return "\n".join(parts)

    if name == "WebSearch":
        query = input_data.get("query", "")
        parts = [f"🔎 *Searching the web*"]
        if query:
            parts.append(f'"{_truncate(query, 100)}"')
        return "\n".join(parts)

    # --- Default: show tool name + truncated JSON input ---
    parts = [f"🔧 *Using {name}*"]
    if input_data:
        try:
            preview = json.dumps(input_data, ensure_ascii=False, indent=2)
            parts.append(f"```\n{_truncate(preview, _MAX_PREVIEW)}\n```")
        except (TypeError, ValueError):
            parts.append(str(input_data)[:_MAX_PREVIEW])
    return "\n".join(parts)


def format_tool_result(tool_name: str, content: str | None, is_error: bool) -> str:
    """Format a tool_result event with a result preview."""
    content = content or ""
    content_len = len(content)

    if is_error:
        # Show error with preview
        error_lines = content.strip().split("\n")
        # Take last few lines (usually the actual error message)
        tail = error_lines[-5:] if len(error_lines) > 5 else error_lines
        error_preview = "\n".join(tail)
        parts = [f"❌ *{tool_name} failed*"]
        if error_preview:
            parts.append(f"```\n{_truncate(error_preview, _MAX_RESULT_PREVIEW)}\n```")
        return "\n".join(parts)

    # Success with content preview
    parts = [f"✅ *{tool_name}* — {_format_size(content_len)}"]

    # Add a meaningful preview of the result
    preview = _extract_result_preview(tool_name, content)
    if preview:
        parts.append(preview)

    return "\n".join(parts)


def _format_size(char_count: int) -> str:
    """Format content size in a human-readable way."""
    if char_count < 100:
        return f"{char_count} chars"
    elif char_count < 1000:
        return f"~{char_count // 100 * 100} chars"
    elif char_count < 10000:
        return f"~{char_count / 1000:.1f}K chars"
    else:
        return f"~{char_count // 1000}K chars"


def _extract_result_preview(tool_name: str, content: str) -> str:
    """Extract a short, meaningful preview from tool result content."""
    content = content.strip()
    if not content:
        return ""

    lines = content.split("\n")

    # Bash: show first and last few lines
    if tool_name == "Bash":
        if len(lines) <= 6:
            return f"```\n{_truncate(content, _MAX_RESULT_PREVIEW)}\n```"
        head = "\n".join(lines[:3])
        tail = "\n".join(lines[-2:])
        return f"```\n{head}\n  … ({len(lines)} lines total)\n{tail}\n```"

    # Glob: show matched file list
    if tool_name == "Glob":
        file_count = len(lines)
        shown = lines[:8]
        preview = "\n".join(f"  {l}" for l in shown)
        if file_count > 8:
            preview += f"\n  … (+{file_count - 8} more)"
        return f"{file_count} files found:\n{preview}"

    # Grep: show match count and first few matches
    if tool_name == "Grep":
        match_count = len(lines)
        shown = lines[:6]
        preview = "\n".join(f"  {l}" for l in shown)
        if match_count > 6:
            preview += f"\n  … (+{match_count - 6} more)"
        return f"{match_count} matches:\n{preview}"

    # Read: show first few lines
    if tool_name == "Read":
        if len(lines) <= 6:
            return f"```\n{_truncate(content, _MAX_RESULT_PREVIEW)}\n```"
        head = "\n".join(lines[:5])
        return f"```\n{head}\n  … ({len(lines)} lines total)\n```"

    # Write/Edit: brief confirmation is enough
    if tool_name in ("Write", "Edit"):
        return ""

    # WebSearch/WebFetch: show first few lines
    if tool_name in ("WebSearch", "WebFetch"):
        if len(lines) <= 4:
            return _truncate(content, _MAX_RESULT_PREVIEW)
        head = "\n".join(lines[:4])
        return _truncate(head, _MAX_RESULT_PREVIEW) + "\n…"

    # Default: show a compact preview
    if len(content) <= 100:
        return content
    if len(lines) <= 4:
        return _truncate(content, _MAX_RESULT_PREVIEW)
    head = "\n".join(lines[:3])
    return f"{_truncate(head, _MAX_RESULT_PREVIEW)}\n… ({len(lines)} lines)"


def convert_tables_for_platform(text: str) -> str:
    """Convert markdown tables to key-value list format for messaging platforms.

    WhatsApp and Telegram don't render markdown table syntax, so this converts
    tables into a readable list format using bold headers.
    """
    # Match contiguous blocks of lines that look like table rows (start with |)
    table_pattern = re.compile(
        r"((?:^[ \t]*\|.+\|[ \t]*$\n?){2,})", re.MULTILINE
    )

    def _convert_table(match: re.Match) -> str:
        block = match.group(1)
        lines = [line.strip() for line in block.strip().splitlines()]

        # Parse header row
        header_line = lines[0]
        headers = [cell.strip() for cell in header_line.strip("|").split("|")]

        # Find data rows (skip separator lines like |---|---|)
        data_rows = []
        for line in lines[1:]:
            stripped = line.strip("| \t")
            # Skip separator rows (only dashes, colons, spaces, pipes)
            if re.match(r"^[\-:\s|]+$", stripped):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            data_rows.append(cells)

        if not data_rows:
            return block  # No data rows found, return original

        # Build key-value output
        parts = []
        for row in data_rows:
            row_parts = []
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ""
                row_parts.append(f"  *{header}:* {value}")
            # Use ▫ bullet for first line of each row
            row_parts[0] = "▫" + row_parts[0][1:]  # Replace leading space with ▫
            parts.append("\n".join(row_parts))

        return "\n\n".join(parts) + "\n"

    return table_pattern.sub(_convert_table, text)


def format_file_download_message(filename: str, size_bytes: int, download_url: str, expire_hours: int = 24) -> str:
    """Format a file download link message for messaging platforms."""
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes // 1024} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"📎 {filename} ({size_str})\n{download_url}\n⏳ Link expires in {expire_hours} hours"
