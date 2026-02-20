/**
 * Pattern to match tool reference strings like:
 * [Tool: Bash (ID: call_abc123)] Input: {...}
 * Handles up to 2 levels of nested braces in JSON inputs.
 * Also matches trailing newlines left after removal.
 */
const TOOL_REF_PATTERN = /\[Tool: [^\]]+\]\s*Input:\s*(?:\{(?:[^{}]*|\{[^{}]*\})*\}|\[.*?\]|"[^"]*")[ \t]*\n?/g;

/**
 * Filters out tool reference patterns from text.
 *
 * Tool references like "[Tool: Bash (ID: call_abc123)] Input: {...}" are
 * displayed separately as tool_use messages, so we remove them from the
 * assistant text content to avoid duplication.
 *
 * @param text - Text to filter
 * @returns Text with tool reference patterns removed
 *
 * @example
 * filterToolReferences('Hello [Tool: Bash (ID: call_123)] Input: {"cmd": "ls"} world')
 * // Returns: 'Hello world'
 */
export function filterToolReferences(text: string): string {
  return text.replace(TOOL_REF_PATTERN, '');
}
