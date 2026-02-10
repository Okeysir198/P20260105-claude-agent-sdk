/**
 * Message preparation utilities for multi-part content support.
 * Provides helpers for creating, validating, and transforming message content.
 *
 * @module message-utils
 */

import type { ContentBlock, TextContentBlock, ImageContentBlock } from '@/types';

/**
 * Result of message validation.
 */
export interface ValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * Validates message content (string or ContentBlock array).
 *
 * @param content - Message content to validate
 * @returns Validation result with error message if invalid
 *
 * @example
 * validateMessageContent('Hello') // { valid: true }
 * validateMessageContent([{ type: 'text', text: 'Hello' }]) // { valid: true }
 * validateMessageContent([]) // { valid: false, error: '...' }
 */
export function validateMessageContent(content: string | ContentBlock[]): ValidationResult {
  try {
    // Validate string content
    if (typeof content === 'string') {
      if (!content.trim()) {
        return { valid: false, error: 'Message content cannot be empty' };
      }
      return { valid: true };
    }

    // Validate ContentBlock array
    if (!Array.isArray(content) || content.length === 0) {
      return { valid: false, error: 'Content blocks must be a non-empty array' };
    }

    for (let i = 0; i < content.length; i++) {
      const block = content[i] as ContentBlock;

      if (!block || typeof block !== 'object') {
        return { valid: false, error: `Content block at index ${i} must be an object` };
      }

      if (!block.type || typeof block.type !== 'string') {
        return { valid: false, error: `Content block at index ${i} must have a valid type` };
      }

      if (block.type === 'text') {
        const textBlock = block as TextContentBlock;
        if (typeof textBlock.text !== 'string') {
          return { valid: false, error: `Text content block at index ${i} must have a text property` };
        }
      } else if (block.type === 'image') {
        const imageBlock = block as ImageContentBlock;
        if (!imageBlock.source || typeof imageBlock.source !== 'object') {
          return { valid: false, error: `Image content block at index ${i} must have a source object` };
        }

        if (!imageBlock.source.type || !['base64', 'url'].includes(imageBlock.source.type)) {
          return { valid: false, error: `Image source type at index ${i} must be either "base64" or "url"` };
        }

        if (imageBlock.source.type === 'base64' && !imageBlock.source.data) {
          return { valid: false, error: `Base64 image at index ${i} must include data property` };
        }

        if (imageBlock.source.type === 'url' && !imageBlock.source.url) {
          return { valid: false, error: `URL image at index ${i} must include url property` };
        }
      } else {
        // Type narrowing - this should never happen with proper types
        const _exhaustiveCheck: never = block;
        return { valid: false, error: `Unknown content block type at index ${i}` };
      }
    }

    return { valid: true };
  } catch (error) {
    return {
      valid: false,
      error: error instanceof Error ? error.message : 'Unknown validation error'
    };
  }
}

/**
 * Converts a File object to a base64 content block.
 * Useful for handling file uploads from input elements.
 *
 * @param file - File object (typically from <input type="file">)
 * @returns Promise that resolves to an image content block
 *
 * @example
 * const fileInput = document.querySelector('input[type="file"]');
 * const file = fileInput.files[0];
 * const imageBlock = await fileToImageBlock(file);
 */
export async function fileToImageBlock(file: File): Promise<ImageContentBlock> {
  if (!file.type.startsWith('image/')) {
    throw new Error('File must be an image');
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      const result = reader.result as string;
      // Extract base64 data from data URL (remove prefix like "data:image/png;base64,")
      const base64Data = result.split(',')[1];

      // Create image block with media_type (required by Claude SDK)
      resolve({
        type: 'image',
        source: {
          type: 'base64',
          media_type: file.type,  // e.g., "image/png", "image/jpeg"
          data: base64Data
        }
      });
    };

    reader.onerror = () => {
      reject(new Error('Failed to read file'));
    };

    reader.readAsDataURL(file);
  });
}

/**
 * Prepares message content for sending.
 * Ensures content is properly formatted and validated.
 *
 * @param content - Raw message content (string, ContentBlock[], or object)
 * @returns Validated and normalized content ready for sending
 * @throws Error if content is invalid
 *
 * @example
 * prepareMessageContent('Hello') // 'Hello'
 * prepareMessageContent([{ type: 'text', text: 'Hello' }]) // [{ type: 'text', text: 'Hello' }]
 */
export function prepareMessageContent(content: string | ContentBlock[]): string | ContentBlock[] {
  const validation = validateMessageContent(content);

  if (!validation.valid) {
    throw new Error(validation.error);
  }

  return content;
}
