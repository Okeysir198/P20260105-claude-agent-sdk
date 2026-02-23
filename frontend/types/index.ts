export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UIQuestionOption {
  value: string;
  description?: string;
}

export interface UIQuestion {
  question: string;
  options: UIQuestionOption[];
  allowMultiple?: boolean;
}

export type ContentBlock =
  | TextContentBlock
  | ImageContentBlock
  | AudioContentBlock
  | VideoContentBlock
  | FileContentBlock;

export interface TextContentBlock {
  type: 'text';
  text: string;
}

export interface ImageContentBlock {
  type: 'image';
  source: {
    type: 'base64' | 'url';
    media_type?: string;
    data?: string;
    url?: string;
  };
}

export interface AudioContentBlock {
  type: 'audio';
  source: {
    url: string;
    mime_type?: string;
  };
  filename?: string;
  duration?: number;
}

export interface VideoContentBlock {
  type: 'video';
  source: {
    url: string;
    mime_type?: string;
  };
  filename?: string;
  duration?: number;
}

export interface FileContentBlock {
  type: 'file';
  source: {
    url: string;
    mime_type?: string;
  };
  filename: string;
  size?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool_use' | 'tool_result';
  content: string | ContentBlock[];
  timestamp: Date;
  toolName?: string;
  toolInput?: Record<string, any>;
  toolUseId?: string;
  isError?: boolean;
  parentToolUseId?: string;
}

export * from './api';
export * from './websocket';
