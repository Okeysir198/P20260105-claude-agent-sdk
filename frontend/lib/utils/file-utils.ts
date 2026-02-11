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
export function getFileExtension(filename: string): string {
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
 * Check if file is a code file
 */
export function isCodeFile(contentType?: string, filename?: string): boolean {
  if (contentType?.includes('javascript') || contentType?.includes('python') || contentType?.includes('java')) return true;
  if (filename) {
    const ext = getFileExtension(filename);
    const codeExts = ['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 'go', 'rs', 'rb', 'php', 'swift', 'kt', 'sh', 'bash'];
    return codeExts.includes(ext);
  }
  return false;
}
