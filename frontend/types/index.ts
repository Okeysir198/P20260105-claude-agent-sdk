// types/index.ts
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// UI-transformed question types for AskUserQuestion modal
// These are transformed from WebSocket Question/QuestionOption types in use-chat.ts
export interface UIQuestionOption {
  value: string;
  description?: string;
}

export interface UIQuestion {
  question: string;
  options: UIQuestionOption[];
  allowMultiple?: boolean;
}

/**
 * Represents a single content block in a message.
 * Messages can contain multiple content blocks of different types.
 *
 * @example
 * // Text content
 * { type: 'text'; text: 'Hello, world!' }
 *
 * // Image content from URL
 * { type: 'image'; source: { type: 'url'; url: 'https://example.com/image.png' } }
 *
 * // Image content from base64 data
 * { type: 'image'; source: { type: 'base64'; data: 'iVBORw0KGgo...' } }
 */
export type ContentBlock = TextContentBlock | ImageContentBlock;

/**
 * Text content block containing plain text.
 */
export interface TextContentBlock {
  type: 'text';
  text: string;
}

/**
 * Image content block with source data.
 * The source can be either a base64-encoded string or a URL.
 */
export interface ImageContentBlock {
  type: 'image';
  source: {
    type: 'base64' | 'url';
    /** MIME type of the image (e.g., "image/png", "image/jpeg") */
    media_type?: string;
    /** Base64-encoded image data (without data URI prefix) */
    data?: string;
    /** URL to the image */
    url?: string;
  };
}

/**
 * Chat message with support for multi-part content.
 *
 * The content field can be either:
 * - A plain string (for backward compatibility)
 * - An array of ContentBlock objects (for multi-part content with images and text)
 *
 * @example
 * // Simple text message (legacy format)
 * const message1: ChatMessage = {
 *   id: 'msg-1',
 *   role: 'user',
 *   content: 'Hello, how are you?',
 *   timestamp: new Date(),
 * };
 *
 * @example
 * // Multi-part message with text and image
 * const message2: ChatMessage = {
 *   id: 'msg-2',
 *   role: 'user',
 *   content: [
 *     { type: 'text', text: 'What do you see in this image?' },
 *     { type: 'image', source: { type: 'url', url: 'https://example.com/image.png' } }
 *   ],
 *   timestamp: new Date(),
 * };
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool_use' | 'tool_result';
  /** Message content - either plain string or array of content blocks */
  content: string | ContentBlock[];
  timestamp: Date;
  toolName?: string;
  toolInput?: Record<string, any>;
  toolUseId?: string;
  isError?: boolean;
  parentToolUseId?: string;
}

// Re-export API types
export * from './api';
export * from './websocket';
