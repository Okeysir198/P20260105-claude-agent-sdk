import type { ContentBlock, TextContentBlock, FileContentBlock } from '@/types';

export function normalizeContent(content: string | ContentBlock[]): ContentBlock[] {
  if (typeof content === 'string') {
    return [{ type: 'text', text: content }];
  }
  return content;
}

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
        // Audio, video, image blocks are rendered as players - no text representation needed
        if (block.type === 'audio') return '';
        if (block.type === 'video') return '';
        if (block.type === 'image') return '';
        // File blocks still show text representation
        if (block.type === 'file') {
          const fb = block as FileContentBlock;
          return `[File: ${fb.filename}]`;
        }
      }
      // Fallback: extract text from any object with a text property
      if (block && typeof block === 'object' && 'text' in block) {
        return String((block as Record<string, unknown>).text ?? '');
      }
      return '';
    })
    .join('');
}

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
