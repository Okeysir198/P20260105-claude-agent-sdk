/**
 * Utility functions for handling multi-part message content.
 * These helpers maintain backward compatibility with string-based content
 * while supporting the new ContentBlock array format.
 */

import type { ContentBlock, TextContentBlock } from '@/types';

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

  return content
    .filter((block): block is TextContentBlock => block.type === 'text')
    .map(block => block.text)
    .join('');
}


