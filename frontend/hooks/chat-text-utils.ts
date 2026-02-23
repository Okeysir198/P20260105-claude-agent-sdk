/**
 * Matches tool reference strings like [Tool: Bash (ID: call_abc123)] Input: {...}
 * These are displayed separately as tool_use messages, so we strip them from assistant text.
 */
const TOOL_REF_PATTERN = /\[Tool: [^\]]+\]\s*Input:\s*(?:\{(?:[^{}]*|\{[^{}]*\})*\}|\[.*?\]|"[^"]*")[ \t]*\n?/g;

export function filterToolReferences(text: string): string {
  return text.replace(TOOL_REF_PATTERN, '');
}
