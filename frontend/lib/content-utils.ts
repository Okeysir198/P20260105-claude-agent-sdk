/**
 * Utility functions for handling multi-part message content.
 * These helpers maintain backward compatibility with string-based content
 * while supporting the new ContentBlock array format.
 */

import type { ContentBlock, TextContentBlock, ImageContentBlock } from '@/types';

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

/**
 * Extracts all image content blocks from a message.
 * @param content - Message content (string or ContentBlock array)
 * @returns Array of image content blocks
 *
 * @example
 * extractImages('Hello') // []
 * extractImages([{ type: 'text', text: 'Hello' }, { type: 'image', source: { type: 'url', url: '...' } }])
 * // [{ type: 'image', source: { type: 'url', url: '...' } }]
 */
export function extractImages(content: string | ContentBlock[]): ImageContentBlock[] {
  if (typeof content === 'string') {
    return [];
  }

  return content.filter((block): block is ImageContentBlock => block.type === 'image');
}

/**
 * Checks if message contains image content.
 * @param content - Message content (string or ContentBlock array)
 * @returns True if content includes images
 */
export function hasImages(content: string | ContentBlock[]): boolean {
  return extractImages(content).length > 0;
}

/**
 * Checks if message has multi-part content (ContentBlock array vs string).
 * @param content - Message content (string or ContentBlock array)
 * @returns True if content is an array of blocks
 */
export function isMultipartContent(content: string | ContentBlock[]): content is ContentBlock[] {
  return Array.isArray(content);
}

/**
 * Converts content to a plain text representation (for display in previews, etc.).
 * @param content - Message content (string or ContentBlock array)
 * @param maxLength - Optional maximum length (default: 100)
 * @returns Text representation of content
 *
 * @example
 * toPreviewText('Hello World') // 'Hello World'
 * toPreviewText([{ type: 'text', text: 'Hello' }, { type: 'image', source: {...} }]) // 'Hello [Image]'
 */
export function toPreviewText(content: string | ContentBlock[], maxLength = 100): string {
  if (typeof content === 'string') {
    return content.length > maxLength ? content.slice(0, maxLength) + '...' : content;
  }

  const text = content
    .map(block => {
      if (block.type === 'text') {
        return block.text;
      } else if (block.type === 'image') {
        return '[Image]';
      }
      return '';
    })
    .join(' ');

  return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
}
