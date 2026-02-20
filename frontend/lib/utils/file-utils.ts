import {
  File,
  FileText,
  Image,
  Film,
  Music,
  Archive,
  Code,
  FileCode,
  FileJson,
  FileQuestion,
  FileSpreadsheet,
} from 'lucide-react';
import type { FileInfo } from '@/types';

export type IconType = typeof File;

/**
 * Get file icon component based on content type or file extension
 */
export function getFileIcon(contentType?: string, filename?: string): IconType {
  // Check content type first
  if (contentType) {
    if (contentType.startsWith('image/')) return Image;
    if (contentType.startsWith('video/')) return Film;
    if (contentType.startsWith('audio/')) return Music;
    if (contentType.includes('pdf')) return FileText;
    if (contentType.includes('word') || contentType.includes('document')) return FileText;
    if (contentType.includes('sheet') || contentType.includes('excel')) return FileSpreadsheet;
    if (contentType.includes('zip') || contentType.includes('rar') || contentType.includes('tar')) return Archive;
    if (contentType.includes('json')) return FileJson;
    if (contentType.includes('javascript') || contentType.includes('python') || contentType.includes('java')) return Code;
  }

  // Fallback to extension
  if (filename) {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext) {
      const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'];
      const codeExts = ['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 'go', 'rs', 'rb', 'php', 'swift', 'kt'];
      const docExts = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'];
      const sheetExts = ['xls', 'xlsx', 'csv', 'ods', 'gsheet'];
      const archiveExts = ['zip', 'rar', '7z', 'tar', 'gz'];
      const jsonExts = ['json', 'yaml', 'yml'];

      if (imageExts.includes(ext)) return Image;
      if (codeExts.includes(ext)) return FileCode;
      if (docExts.includes(ext)) return FileText;
      if (sheetExts.includes(ext)) return FileSpreadsheet;
      if (archiveExts.includes(ext)) return Archive;
      if (jsonExts.includes(ext)) return FileJson;
    }
  }

  return FileQuestion;
}

/**
 * Format file size to human-readable string
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Get file extension from filename
 */
function getFileExtension(filename: string): string {
  const parts = filename.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
}

/**
 * Check if file is an image
 */
export function isImageFile(contentType?: string, filename?: string): boolean {
  if (contentType?.startsWith('image/')) return true;
  if (filename) {
    const ext = getFileExtension(filename);
    const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'];
    return imageExts.includes(ext);
  }
  return false;
}

/**
 * Get file preview type based on content type and extension
 */
export function getPreviewType(file: FileInfo): 'image' | 'pdf' | 'json' | 'markdown' | 'spreadsheet' | 'code' | 'text' | 'audio' | 'video' | 'binary' {
  const { content_type, original_name } = file;
  const ext = original_name.split('.').pop()?.toLowerCase();

  // Check content type first (more reliable than extension)
  if (content_type?.startsWith('audio/')) {
    return 'audio';
  }

  if (content_type?.startsWith('video/')) {
    return 'video';
  }

  if (content_type?.startsWith('image/')) {
    return 'image';
  }

  // Fallback to extension-based detection
  const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'];
  if (imageExts.includes(ext!)) {
    return 'image';
  }

  // Audio-only extensions (webm can be audio or video, check content type first)
  const audioExts = ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac', 'opus'];
  if (audioExts.includes(ext!)) {
    return 'audio';
  }

  // Video-only extensions
  const videoExts = ['mp4', 'mov', 'avi', 'mkv'];
  if (videoExts.includes(ext!)) {
    return 'video';
  }

  // Special handling for webm - prefer audio for standalone audio files
  if (ext === 'webm') {
    // If content_type says video, use video. Otherwise default to audio
    return content_type?.startsWith('video/') ? 'video' : 'audio';
  }

  if (content_type?.includes('pdf') || ext === 'pdf') return 'pdf';
  if (content_type?.includes('json') || ext === 'json') return 'json';
  if (ext === 'md') return 'markdown';

  const spreadsheetExts = ['xlsx', 'xls', 'csv', 'ods', 'gsheet'];
  if (content_type?.includes('sheet') || content_type?.includes('excel') || spreadsheetExts.includes(ext!)) return 'spreadsheet';

  const codeExts = ['js', 'ts', 'jsx', 'tsx', 'py', 'html', 'css'];
  if (codeExts.includes(ext!)) return 'code';

  if (content_type?.startsWith('text/') || ext === 'txt') return 'text';

  return 'binary';
}

/**
 * Get file-type color classes for icon and background.
 * Returns { iconColor, bgColor } Tailwind class strings.
 */
export function getFileColorClasses(
  contentType?: string,
  filename?: string
): { iconColor: string; bgColor: string } {
  const colorMap: Record<string, { iconColor: string; bgColor: string }> = {
    image:   { iconColor: 'text-purple-500 dark:text-purple-400',  bgColor: 'bg-purple-500/10 dark:bg-purple-500/5' },
    video:   { iconColor: 'text-pink-500 dark:text-pink-400',      bgColor: 'bg-pink-500/10 dark:bg-pink-500/5' },
    audio:   { iconColor: 'text-orange-500 dark:text-orange-400',  bgColor: 'bg-orange-500/10 dark:bg-orange-500/5' },
    pdf:     { iconColor: 'text-red-500 dark:text-red-400',        bgColor: 'bg-red-500/10 dark:bg-red-500/5' },
    sheet:   { iconColor: 'text-emerald-500 dark:text-emerald-400', bgColor: 'bg-emerald-500/10 dark:bg-emerald-500/5' },
    doc:     { iconColor: 'text-blue-500 dark:text-blue-400',      bgColor: 'bg-blue-500/10 dark:bg-blue-500/5' },
    archive: { iconColor: 'text-amber-500 dark:text-amber-400',    bgColor: 'bg-amber-500/10 dark:bg-amber-500/5' },
    json:    { iconColor: 'text-yellow-500 dark:text-yellow-400',  bgColor: 'bg-yellow-500/10 dark:bg-yellow-500/5' },
    code:    { iconColor: 'text-cyan-500 dark:text-cyan-400',      bgColor: 'bg-cyan-500/10 dark:bg-cyan-500/5' },
  };

  const fallback = { iconColor: 'text-muted-foreground', bgColor: 'bg-muted/60' };

  // Match by content type
  if (contentType) {
    if (contentType.startsWith('image/')) return colorMap.image;
    if (contentType.startsWith('video/')) return colorMap.video;
    if (contentType.startsWith('audio/')) return colorMap.audio;
    if (contentType.includes('pdf')) return colorMap.pdf;
    if (contentType.includes('sheet') || contentType.includes('excel')) return colorMap.sheet;
    if (contentType.includes('word') || contentType.includes('document')) return colorMap.doc;
    if (contentType.includes('zip') || contentType.includes('rar') || contentType.includes('tar')) return colorMap.archive;
    if (contentType.includes('json')) return colorMap.json;
    if (contentType.includes('javascript') || contentType.includes('python') || contentType.includes('java')) return colorMap.code;
  }

  // Fallback to extension
  if (filename) {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext) {
      const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'];
      const codeExts = ['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 'go', 'rs', 'rb', 'php', 'swift', 'kt'];
      const docExts = ['doc', 'docx', 'txt', 'rtf', 'odt'];
      const sheetExts = ['xls', 'xlsx', 'csv', 'ods', 'gsheet'];
      const archiveExts = ['zip', 'rar', '7z', 'tar', 'gz'];

      if (imageExts.includes(ext)) return colorMap.image;
      if (codeExts.includes(ext)) return colorMap.code;
      if (ext === 'pdf') return colorMap.pdf;
      if (docExts.includes(ext)) return colorMap.doc;
      if (sheetExts.includes(ext)) return colorMap.sheet;
      if (archiveExts.includes(ext)) return colorMap.archive;
    }
  }

  return fallback;
}

/**
 * Get syntax highlighting language from filename
 */
export function getLanguageFromFile(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  const map: Record<string, string> = {
    js: 'javascript',
    ts: 'typescript',
    jsx: 'javascript',
    tsx: 'typescript',
    py: 'python',
    md: 'markdown',
    html: 'html',
    css: 'css',
    json: 'json',
  };
  return map[ext!] || 'text';
}

