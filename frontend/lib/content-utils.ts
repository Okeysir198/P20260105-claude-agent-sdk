/**
 * Utility functions for handling multi-part message content.
 * Maintains backward compatibility with string-based content while
 * supporting the ContentBlock array format.
 */

import type { ContentBlock, TextContentBlock, AudioContentBlock, VideoContentBlock, FileContentBlock } from '@/types';

/**
 * Normalizes message content to always return a ContentBlock array.
 * @param content - Message content (string or ContentBlock array)
 * @returns Array of ContentBlock objects
 *
 * @example
 * normalizeContent('Hello') // [{ type: 'text', text: 'Hello' }]
 * normalizeContent([{ type: 'text', text: 'Hello' }]) // [{ type: 'text', text: 'Hello' }]
 */
export function normalizeContent(content: string | ContentBlock[]): ContentBlock[] {
  if (typeof content === 'string') {
    return [{ type: 'text', text: content }];
  }
  return content;
}

/**
 * Extracts all text content from a message, concatenating multiple text blocks.
 * @param content - Message content (string or ContentBlock array)
 * @returns Concatenated text content
 *
 * @example
 * extractText('Hello') // 'Hello'
 * extractText([{ type: 'text', text: 'Hello' }, { type: 'text', text: ' World' }]) // 'Hello World'
 */
export function extractText(content: string | ContentBlock[]): string {
  if (typeof content === 'string') {
    return content;
  }

  // Runtime safety: content might not be an array despite the type signature
  if (!Array.isArray(content)) {
    if (content && typeof content === 'object' && 'text' in content) {
      return String((content as Record<string, unknown>).text ?? '');
    }
    return String(content ?? '');
  }

  return content
    .map(block => {
      if (block && typeof block === 'object' && 'type' in block) {
        if (block.type === 'text' && 'text' in block) {
          return (block as TextContentBlock).text;
        }
        if (block.type === 'audio') {
          const ab = block as AudioContentBlock;
          return `[Audio: ${ab.filename || 'audio'}]`;
        }
        if (block.type === 'video') {
          const vb = block as VideoContentBlock;
          return `[Video: ${vb.filename || 'video'}]`;
        }
        if (block.type === 'file') {
          const fb = block as FileContentBlock;
          return `[File: ${fb.filename}]`;
        }
        // image blocks produce no text
        if (block.type === 'image') return '';
      }
      // Fallback: extract text from any object with a text property
      if (block && typeof block === 'object' && 'text' in block) {
        return String((block as Record<string, unknown>).text ?? '');
      }
      return '';
    })
    .join('');
}

/**
 * Normalizes tool result content to string.
 * Backend may send content as string, array of content blocks, or other types.
 * @param content - Tool result content (unknown type from backend)
 * @returns Normalized string content
 *
 * @example
 * normalizeToolResultContent('Hello') // 'Hello'
 * normalizeToolResultContent([{ text: 'Hello' }, { text: 'World' }]) // 'Hello\nWorld'
 * normalizeToolResultContent(null) // ''
 */
export function normalizeToolResultContent(content: unknown): string {
  if (typeof content === 'string') {
    return content;
  }
  if (content == null) {
    return '';
  }
  if (Array.isArray(content)) {
    return content
      .map((block) => {
        if (typeof block === 'string') {
          return block;
        }
        if (block && typeof block === 'object' && 'text' in block) {
          return String(block.text ?? '');
        }
        if (block && typeof block === 'object') {
          try {
            return JSON.stringify(block);
          } catch {
            // Fall through to final fallback
          }
        }
        return String(block);
      })
      .join('\n');
  }
  if (typeof content === 'object' && content !== null && 'text' in content) {
    return String((content as Record<string, unknown>).text ?? '');
  }
  try {
    return JSON.stringify(content);
  } catch {
    return String(content);
  }
}
