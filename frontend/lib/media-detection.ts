export interface DetectedMedia {
  type: 'audio' | 'video' | 'image' | 'file';
  url: string;
  filename: string;
  mimeType?: string;
}

const AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.opus'];
const VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv'];
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico', '.tiff'];

function getExtension(url: string): string {
  try {
    const pathname = new URL(url, 'http://localhost').pathname;
    const dotIndex = pathname.lastIndexOf('.');
    if (dotIndex === -1) return '';
    return pathname.slice(dotIndex).toLowerCase();
  } catch {
    return '';
  }
}

function extractFilename(url: string, fallbackFilename?: string): string {
  if (fallbackFilename) return fallbackFilename;
  try {
    const pathname = new URL(url, 'http://localhost').pathname;
    const segments = pathname.split('/').filter(Boolean);
    return segments[segments.length - 1] || 'file';
  } catch {
    return 'file';
  }
}

function determineMediaType(
  ext: string,
  mimeType?: string,
  toolName?: string,
): 'audio' | 'video' | 'image' | 'file' {
  // Check mime type first
  if (mimeType) {
    if (mimeType.startsWith('audio/')) return 'audio';
    if (mimeType.startsWith('video/')) return 'video';
    if (mimeType.startsWith('image/')) return 'image';
  }

  // Check extension
  if (AUDIO_EXTENSIONS.includes(ext)) return 'audio';
  if (VIDEO_EXTENSIONS.includes(ext)) return 'video';
  if (IMAGE_EXTENSIONS.includes(ext)) return 'image';

  // Check tool name hint
  if (toolName) {
    const lower = toolName.toLowerCase();
    if (lower.includes('tts') || lower.includes('speech') || lower.includes('audio')) return 'audio';
    if (lower.includes('image') || lower.includes('ocr') || lower.includes('vision')) return 'image';
    if (lower.includes('video')) return 'video';
  }

  return 'file';
}

function extractUrlFromObject(obj: Record<string, unknown>): {
  url: string;
  filename?: string;
  mimeType?: string;
} | null {
  // Direct URL fields (in priority order)
  const urlFields = ['download_url', 'url', 'file_url', 'media_url', 'output_url'];
  const pathFields = ['file_path', 'output_path', 'path', 'output_file'];

  for (const field of urlFields) {
    const val = obj[field];
    if (typeof val === 'string' && (val.startsWith('http://') || val.startsWith('https://') || val.startsWith('/'))) {
      return {
        url: val,
        filename: (obj.filename as string) || undefined,
        mimeType: (obj.mime_type as string) || (obj.mimeType as string) || (obj.content_type as string) || undefined,
      };
    }
  }

  for (const field of pathFields) {
    const val = obj[field];
    if (typeof val === 'string' && val.length > 0) {
      const ext = getExtension(val);
      // Only treat paths as media if they have a known media extension
      if (AUDIO_EXTENSIONS.includes(ext) || VIDEO_EXTENSIONS.includes(ext) || IMAGE_EXTENSIONS.includes(ext)) {
        return {
          url: val,
          filename: (obj.filename as string) || undefined,
          mimeType: (obj.mime_type as string) || (obj.mimeType as string) || (obj.content_type as string) || undefined,
        };
      }
    }
  }

  return null;
}

export function detectMediaInToolResult(
  content: string,
  toolName?: string,
): DetectedMedia | null {
  if (!content) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch {
    return null;
  }

  if (typeof parsed !== 'object' || parsed === null) return null;

  const obj = parsed as Record<string, unknown>;

  // Try top-level first
  let found = extractUrlFromObject(obj);

  // Try nested `result` field
  if (!found && typeof obj.result === 'object' && obj.result !== null) {
    found = extractUrlFromObject(obj.result as Record<string, unknown>);
  }

  // Try nested `data` field
  if (!found && typeof obj.data === 'object' && obj.data !== null) {
    found = extractUrlFromObject(obj.data as Record<string, unknown>);
  }

  if (!found) return null;

  const ext = getExtension(found.url);
  const mediaType = determineMediaType(ext, found.mimeType, toolName);
  const filename = extractFilename(found.url, found.filename);

  return {
    type: mediaType,
    url: found.url,
    filename,
    mimeType: found.mimeType,
  };
}
