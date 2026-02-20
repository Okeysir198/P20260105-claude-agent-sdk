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

// Shared extension sets used across multiple functions
const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp']);
const CODE_EXTS = new Set(['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 'go', 'rs', 'rb', 'php', 'swift', 'kt']);
const DOC_EXTS = new Set(['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt']);
const SHEET_EXTS = new Set(['xls', 'xlsx', 'csv', 'ods', 'gsheet']);
const ARCHIVE_EXTS = new Set(['zip', 'rar', '7z', 'tar', 'gz']);
const JSON_EXTS = new Set(['json', 'yaml', 'yml']);
const AUDIO_EXTS = new Set(['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac', 'opus']);
const VIDEO_EXTS = new Set(['mp4', 'mov', 'avi', 'mkv']);
const PREVIEW_CODE_EXTS = new Set(['js', 'ts', 'jsx', 'tsx', 'py', 'html', 'css']);

function getExtension(filename: string): string {
  const parts = filename.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
}

/**
 * Get file icon component based on content type or file extension
 */
export function getFileIcon(contentType?: string, filename?: string): IconType {
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

  if (filename) {
    const ext = getExtension(filename);
    if (ext) {
      if (IMAGE_EXTS.has(ext)) return Image;
      if (CODE_EXTS.has(ext)) return FileCode;
      if (DOC_EXTS.has(ext)) return FileText;
      if (SHEET_EXTS.has(ext)) return FileSpreadsheet;
      if (ARCHIVE_EXTS.has(ext)) return Archive;
      if (JSON_EXTS.has(ext)) return FileJson;
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
 * Check if file is an image
 */
export function isImageFile(contentType?: string, filename?: string): boolean {
  if (contentType?.startsWith('image/')) return true;
  if (filename) return IMAGE_EXTS.has(getExtension(filename));
  return false;
}

/**
 * Get file preview type based on content type and extension
 */
export function getPreviewType(file: FileInfo): 'image' | 'pdf' | 'json' | 'markdown' | 'spreadsheet' | 'code' | 'text' | 'audio' | 'video' | 'binary' {
  const { content_type, original_name } = file;
  const ext = getExtension(original_name);

  // Check content type first (more reliable than extension)
  if (content_type?.startsWith('audio/')) return 'audio';
  if (content_type?.startsWith('video/')) return 'video';
  if (content_type?.startsWith('image/')) return 'image';

  // Extension-based detection
  if (IMAGE_EXTS.has(ext)) return 'image';
  if (AUDIO_EXTS.has(ext)) return 'audio';
  if (VIDEO_EXTS.has(ext)) return 'video';

  // Special handling for webm - prefer audio unless content_type says video
  if (ext === 'webm') {
    return content_type?.startsWith('video/') ? 'video' : 'audio';
  }

  if (content_type?.includes('pdf') || ext === 'pdf') return 'pdf';
  if (content_type?.includes('json') || ext === 'json') return 'json';
  if (ext === 'md') return 'markdown';
  if (content_type?.includes('sheet') || content_type?.includes('excel') || SHEET_EXTS.has(ext)) return 'spreadsheet';
  if (PREVIEW_CODE_EXTS.has(ext)) return 'code';
  if (content_type?.startsWith('text/') || ext === 'txt') return 'text';

  return 'binary';
}

/**
 * Color classes for file-type icon and background styling.
 */
const FILE_COLOR_MAP: Record<string, { iconColor: string; bgColor: string }> = {
  image:   { iconColor: 'text-purple-500 dark:text-purple-400',   bgColor: 'bg-purple-500/10 dark:bg-purple-500/5' },
  video:   { iconColor: 'text-pink-500 dark:text-pink-400',       bgColor: 'bg-pink-500/10 dark:bg-pink-500/5' },
  audio:   { iconColor: 'text-orange-500 dark:text-orange-400',   bgColor: 'bg-orange-500/10 dark:bg-orange-500/5' },
  pdf:     { iconColor: 'text-red-500 dark:text-red-400',         bgColor: 'bg-red-500/10 dark:bg-red-500/5' },
  sheet:   { iconColor: 'text-emerald-500 dark:text-emerald-400', bgColor: 'bg-emerald-500/10 dark:bg-emerald-500/5' },
  doc:     { iconColor: 'text-blue-500 dark:text-blue-400',       bgColor: 'bg-blue-500/10 dark:bg-blue-500/5' },
  archive: { iconColor: 'text-amber-500 dark:text-amber-400',     bgColor: 'bg-amber-500/10 dark:bg-amber-500/5' },
  json:    { iconColor: 'text-yellow-500 dark:text-yellow-400',   bgColor: 'bg-yellow-500/10 dark:bg-yellow-500/5' },
  code:    { iconColor: 'text-cyan-500 dark:text-cyan-400',       bgColor: 'bg-cyan-500/10 dark:bg-cyan-500/5' },
};

const DEFAULT_FILE_COLORS = { iconColor: 'text-muted-foreground', bgColor: 'bg-muted/60' };

/**
 * Get file-type color classes for icon and background.
 */
export function getFileColorClasses(
  contentType?: string,
  filename?: string
): { iconColor: string; bgColor: string } {
  if (contentType) {
    if (contentType.startsWith('image/')) return FILE_COLOR_MAP.image;
    if (contentType.startsWith('video/')) return FILE_COLOR_MAP.video;
    if (contentType.startsWith('audio/')) return FILE_COLOR_MAP.audio;
    if (contentType.includes('pdf')) return FILE_COLOR_MAP.pdf;
    if (contentType.includes('sheet') || contentType.includes('excel')) return FILE_COLOR_MAP.sheet;
    if (contentType.includes('word') || contentType.includes('document')) return FILE_COLOR_MAP.doc;
    if (contentType.includes('zip') || contentType.includes('rar') || contentType.includes('tar')) return FILE_COLOR_MAP.archive;
    if (contentType.includes('json')) return FILE_COLOR_MAP.json;
    if (contentType.includes('javascript') || contentType.includes('python') || contentType.includes('java')) return FILE_COLOR_MAP.code;
  }

  if (filename) {
    const ext = getExtension(filename);
    if (ext) {
      if (IMAGE_EXTS.has(ext)) return FILE_COLOR_MAP.image;
      if (CODE_EXTS.has(ext)) return FILE_COLOR_MAP.code;
      if (ext === 'pdf') return FILE_COLOR_MAP.pdf;
      // Exclude pdf/txt from doc check (pdf handled above, txt is plain text)
      const docOnlyExts = new Set(['doc', 'docx', 'rtf', 'odt']);
      if (docOnlyExts.has(ext)) return FILE_COLOR_MAP.doc;
      if (SHEET_EXTS.has(ext)) return FILE_COLOR_MAP.sheet;
      if (ARCHIVE_EXTS.has(ext)) return FILE_COLOR_MAP.archive;
    }
  }

  return DEFAULT_FILE_COLORS;
}

/**
 * Get syntax highlighting language from filename
 */
export function getLanguageFromFile(filename: string): string {
  const ext = getExtension(filename);
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
  return map[ext] || 'text';
}
