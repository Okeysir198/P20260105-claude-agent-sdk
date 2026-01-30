/**
 * Text processing utilities for chat message handling.
 * Provides functions for filtering and transforming text content.
 *
 * @module chat-text-utils
 */

/**
 * Pattern to match tool reference strings like:
 * [Tool: Bash (ID: call_abc123)] Input: {...}
 * These are filtered out from assistant text deltas to avoid duplicate display.
 */
const TOOL_REF_PATTERN = /\[Tool: [^\]]+\] Input:\s*(?:\{[^}]*\}|\[.*?\]|"[^"]*")\s*/g;

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
 * // Returns: 'Hello  world'
 */
export function filterToolReferences(text: string): string {
  return text.replace(TOOL_REF_PATTERN, '');
}
