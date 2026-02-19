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
 * Compresses an image file to fit within the specified size limit.
 * Uses canvas to resize the image while maintaining aspect ratio.
 *
 * @param file - The image file to compress
 * @param maxSizeBytes - Maximum allowed file size in bytes (default: 10MB)
 * @param maxDimension - Maximum width/height dimension (default: 2048)
 * @returns Promise that resolves to a compressed File object
 *
 * @example
 * const compressed = await compressImage(file, 10 * 1024 * 1024);
 */
export async function compressImage(
  file: File,
  maxSizeBytes: number = 10 * 1024 * 1024,
  maxDimension: number = 2048
): Promise<File> {
  // If file is already small enough, return as-is
  if (file.size <= maxSizeBytes) {
    return file;
  }

  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(url);

      // Calculate new dimensions while maintaining aspect ratio
      let { width, height } = img;
      const aspectRatio = width / height;

      if (width > height) {
        if (width > maxDimension) {
          width = maxDimension;
          height = Math.round(width / aspectRatio);
        }
      } else {
        if (height > maxDimension) {
          height = maxDimension;
          width = Math.round(height * aspectRatio);
        }
      }

      // Create canvas and resize
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Failed to get canvas context'));
        return;
      }

      // Draw resized image
      ctx.drawImage(img, 0, 0, width, height);

      // Try different quality levels until we fit under the size limit
      let quality = 0.92;
      const minQuality = 0.1;
      const qualityStep = 0.05;

      const tryCompress = () => {
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error('Failed to compress image'));
              return;
            }

            // If size is acceptable or quality is too low, use this result
            if (blob.size <= maxSizeBytes || quality <= minQuality) {
              // Create new File object with compressed data
              const compressedFile = new File([blob], file.name, {
                type: file.type,
                lastModified: Date.now(),
              });
              resolve(compressedFile);
            } else {
              // Reduce quality and try again
              quality = Math.max(minQuality, quality - qualityStep);
              tryCompress();
            }
          },
          file.type,
          quality
        );
      };

      tryCompress();
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image'));
    };

    img.src = url;
  });
}

/**
 * Converts a File object to a base64 content block.
 * Automatically compresses images that exceed the size limit.
 *
 * @param file - File object (typically from <input type="file">)
 * @param maxSizeBytes - Maximum allowed file size in bytes (default: 10MB)
 * @returns Promise that resolves to an image content block
 *
 * @example
 * const fileInput = document.querySelector('input[type="file"]');
 * const file = fileInput.files[0];
 * const imageBlock = await fileToImageBlock(file);
 */
export async function fileToImageBlock(
  file: File,
  maxSizeBytes: number = 10 * 1024 * 1024
): Promise<ImageContentBlock> {
  if (!file.type.startsWith('image/')) {
    throw new Error('File must be an image');
  }

  // Compress image if needed
  const processedFile = await compressImage(file, maxSizeBytes);

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
          media_type: processedFile.type,  // e.g., "image/png", "image/jpeg"
          data: base64Data
        }
      });
    };

    reader.onerror = () => {
      reject(new Error('Failed to read file'));
    };

    reader.readAsDataURL(processedFile);
  });
}

