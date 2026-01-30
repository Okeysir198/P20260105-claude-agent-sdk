/**
 * Message preparation utilities for multi-part content support.
 * Provides helpers for creating, validating, and transforming message content.
 *
 * @module message-utils
 */

/*
 * MIGRATION GUIDE: Multi-Part Message Support
 * =============================================
 *
 * This file enables the frontend to send multi-part messages (text + images)
 * via WebSocket while maintaining backward compatibility with string messages.
 *
 * KEY CHANGES:
 * ------------
 *
 * 1. Type System:
 *    - ContentBlock[] type represents multi-part content
 *    - ChatMessage.content accepts: string | ContentBlock[]
 *    - ClientMessage.content accepts: string | ContentBlock[]
 *
 * 2. Message Sending:
 *    OLD: sendMessage('Hello world')
 *    NEW: sendMessage('Hello world') // Still works!
 *         sendMessage([{ type: 'text', text: 'Hello' }]) // Also works!
 *         sendMessage([
 *           { type: 'text', text: 'What do you see?' },
 *           { type: 'image', source: { type: 'url', url: 'https://...' } }
 *         ]) // Multi-part!
 *
 * 3. Validation:
 *    - All content is validated before sending
 *    - Validation errors are displayed to user via toast
 *    - Both string and ContentBlock[] formats are validated
 *
 * 4. Helper Functions:
 *    - createTextBlock(text) - Create text content block
 *    - createImageUrlBlock(url) - Create image block from URL
 *    - createImageBase64Block(data) - Create image block from base64
 *    - createMultipartMessage(text, images) - Create multi-part message
 *    - fileToImageBlock(file) - Convert File object to image block
 *    - validateMessageContent(content) - Validate any content
 *    - prepareMessageContent(content) - Validate and prepare content
 *
 * IMPLEMENTATION STATUS:
 * ----------------------
 * ✅ Type definitions (types/index.ts, types/websocket.ts)
 * ✅ Validation utilities (this file)
 * ✅ WebSocket message sending (lib/websocket-manager.ts)
 * ✅ Chat hook integration (hooks/use-chat.ts)
 * ✅ Chat input infrastructure (components/chat/chat-input.tsx)
 * ⏳ Image upload UI (infrastructure ready, commented out)
 * ⏳ Image preview component (infrastructure ready, commented out)
 *
 * BACKWARD COMPATIBILITY:
 * -----------------------
 * ✅ String messages still work everywhere
 * ✅ No breaking changes to existing code
 * ✅ Backend can handle both formats (ContentBlock[] or string)
 *
 * NEXT STEPS (Future Enhancement):
 * ---------------------------------
 * 1. Uncomment image upload button in chat-input.tsx
 * 2. Implement handleImageSelect with proper file reading
 * 3. Add image preview component below textarea
 * 4. Add loading states for image uploads
 * 5. Add error handling for invalid image files
 * 6. Consider image size limits and compression
 * 7. Add drag-and-drop support for images
 *
 * TESTING:
 * ---------
 * Test string messages: sendMessage('Hello')
 * Test multi-part: sendMessage([createTextBlock('Hi'), createImageUrlBlock(url)])
 * Test validation: sendMessage('') should show error
 * Test validation: sendMessage([]) should show error
 *
 * DEPENDENCIES:
 * -------------
 * - types/index.ts (ContentBlock types)
 * - hooks/use-chat.ts (sendMessage function)
 * - components/ui/toast (error display)
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
 * Creates a text content block.
 *
 * @param text - Text content
 * @returns Text content block
 *
 * @example
 * createTextBlock('Hello, world!') // { type: 'text', text: 'Hello, world!' }
 */
export function createTextBlock(text: string): TextContentBlock {
  return { type: 'text', text };
}

/**
 * Creates an image content block from a URL.
 *
 * @param url - Image URL
 * @returns Image content block
 *
 * @example
 * createImageUrlBlock('https://example.com/image.png')
 * // { type: 'image', source: { type: 'url', url: '...' } }
 */
export function createImageUrlBlock(url: string): ImageContentBlock {
  return {
    type: 'image',
    source: { type: 'url', url }
  };
}

/**
 * Creates an image content block from base64 data.
 *
 * @param data - Base64-encoded image data (without data URI prefix)
 * @returns Image content block
 *
 * @example
 * createImageBase64Block('iVBORw0KGgo...')
 * // { type: 'image', source: { type: 'base64', data: 'iVBORw0KGgo...' } }
 */
export function createImageBase64Block(data: string): ImageContentBlock {
  return {
    type: 'image',
    source: { type: 'base64', data }
  };
}

/**
 * Creates a multi-part message with text and optional images.
 *
 * @param text - Text content
 * @param images - Optional array of image URLs or base64 data
 * @returns Array of content blocks
 *
 * @example
 * createMultipartMessage('What do you see?', ['https://example.com/image.png'])
 * // [
 * //   { type: 'text', text: 'What do you see?' },
 * //   { type: 'image', source: { type: 'url', url: '...' } }
 * // ]
 */
export function createMultipartMessage(
  text: string,
  images?: Array<{ type: 'url'; url: string } | { type: 'base64'; data: string }>
): ContentBlock[] {
  const blocks: ContentBlock[] = [createTextBlock(text)];

  if (images && images.length > 0) {
    for (const image of images) {
      if (image.type === 'url') {
        blocks.push(createImageUrlBlock(image.url));
      } else {
        blocks.push(createImageBase64Block(image.data));
      }
    }
  }

  return blocks;
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
 * Type guard to check if content is a ContentBlock array.
 *
 * @param content - Message content to check
 * @returns True if content is a ContentBlock array
 */
export function isContentBlockArray(content: string | ContentBlock[]): content is ContentBlock[] {
  return Array.isArray(content);
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
