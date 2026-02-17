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
      const sheetExts = ['xls', 'xlsx', 'csv', 'ods'];
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
export function getPreviewType(file: FileInfo): 'image' | 'pdf' | 'json' | 'markdown' | 'code' | 'text' | 'binary' {
  const { content_type, original_name } = file;
  const ext = original_name.split('.').pop()?.toLowerCase();

  if (content_type?.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext!)) {
    return 'image';
  }
  if (content_type?.includes('pdf') || ext === 'pdf') return 'pdf';
  if (content_type?.includes('json') || ext === 'json') return 'json';
  if (ext === 'md') return 'markdown';

  const codeExts = ['js', 'ts', 'jsx', 'tsx', 'py', 'html', 'css'];
  if (codeExts.includes(ext!)) return 'code';

  if (content_type?.startsWith('text/') || ext === 'txt') return 'text';

  return 'binary';
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

