/**
 * File utility functions for formatting and displaying file information
 */

/**
 * File type mapping configuration
 */
const FILE_TYPE_MAP: Record<
  string,
  { icon: string; color: string; type: string }
> = {
  // Documents
  pdf: { icon: 'file-text', color: 'text-blue-500', type: 'PDF' },
  doc: { icon: 'file-edit', color: 'text-blue-600', type: 'Document' },
  docx: { icon: 'file-edit', color: 'text-blue-600', type: 'Document' },

  // Spreadsheets
  xls: { icon: 'file-spreadsheet', color: 'text-green-500', type: 'Spreadsheet' },
  xlsx: { icon: 'file-spreadsheet', color: 'text-green-500', type: 'Spreadsheet' },
  csv: { icon: 'file-spreadsheet', color: 'text-green-500', type: 'Spreadsheet' },

  // Images
  png: { icon: 'image', color: 'text-purple-500', type: 'Image' },
  jpg: { icon: 'image', color: 'text-purple-500', type: 'Image' },
  jpeg: { icon: 'image', color: 'text-purple-500', type: 'Image' },
  gif: { icon: 'image', color: 'text-purple-500', type: 'Image' },
  webp: { icon: 'image', color: 'text-purple-500', type: 'Image' },
  svg: { icon: 'image', color: 'text-purple-500', type: 'Image' },

  // Code - General
  py: { icon: 'code', color: 'text-yellow-500', type: 'Code' },
  js: { icon: 'code', color: 'text-yellow-500', type: 'Code' },
  ts: { icon: 'code', color: 'text-yellow-500', type: 'Code' },
  jsx: { icon: 'code', color: 'text-yellow-500', type: 'Code' },
  tsx: { icon: 'code', color: 'text-yellow-500', type: 'Code' },

  // Code - Web
  html: { icon: 'code', color: 'text-orange-500', type: 'Code' },
  css: { icon: 'code', color: 'text-orange-500', type: 'Code' },

  // Archives
  zip: { icon: 'archive', color: 'text-orange-500', type: 'Archive' },
  tar: { icon: 'archive', color: 'text-orange-500', type: 'Archive' },
  gz: { icon: 'archive', color: 'text-orange-500', type: 'Archive' },

  // Data
  json: { icon: 'bar-chart', color: 'text-pink-500', type: 'Data' },

  // Text
  txt: { icon: 'file-edit', color: 'text-gray-500', type: 'Text' },
  md: { icon: 'file-edit', color: 'text-gray-500', type: 'Text' },
};

/**
 * Image file extensions for quick checking
 */
const IMAGE_EXTENSIONS = new Set([
  'png',
  'jpg',
  'jpeg',
  'gif',
  'webp',
  'svg',
]);

/**
 * Convert bytes to human-readable format
 * @param bytes - Number of bytes
 * @returns Formatted string (e.g., "1.5 MB", "999 B")
 *
 * @example
 * formatBytes(0) // "0 B"
 * formatBytes(999) // "999 B"
 * formatBytes(1536) // "1.5 KB"
 * formatBytes(2359296) // "2.3 MB"
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const threshold = 1024;
  const unitIndex = Math.floor(Math.log(bytes) / Math.log(threshold));

  const value = bytes / Math.pow(threshold, unitIndex);

  // Round to whole number for bytes and KB, 1 decimal for larger units
  const formattedValue =
    unitIndex <= 1 ? Math.round(value) : value.toFixed(1).replace(/\.0$/, '');

  return `${formattedValue} ${units[unitIndex]}`;
}

/**
 * Convert ISO datetime to relative time string
 * @param isoString - ISO 8601 datetime string
 * @returns Relative time string (e.g., "2m ago", "1h ago", "Just now")
 *
 * @example
 * formatDate("2024-01-01T12:00:00Z") // "2d ago" (depending on current time)
 * formatDate(new Date().toISOString()) // "Just now"
 */
export function formatDate(isoString: string): string {
  const now = Date.now();
  const past = new Date(isoString).getTime();
  const diff = now - past;

  // Handle edge cases: future dates or invalid dates
  if (diff < 0 || isNaN(past)) {
    return 'Just now';
  }

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);

  if (seconds < 60) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  if (weeks < 4) return `${weeks}w ago`;
  return `${months}mo ago`;
}

/**
 * Get file icon and color based on filename extension
 * @param filename - Name of the file
 * @returns Object with icon name and Tailwind color class
 *
 * @example
 * getFileIcon("document.pdf") // { icon: "file-text", color: "text-blue-500" }
 * getFileIcon("script.py") // { icon: "code", color: "text-yellow-500" }
 * getFileIcon("unknown.xyz") // { icon: "file", color: "text-gray-400" }
 */
export function getFileIcon(filename: string): {
  icon: string;
  color: string;
} {
  const ext = getFileExtension(filename);
  const mapped = FILE_TYPE_MAP[ext];

  if (mapped) {
    return { icon: mapped.icon, color: mapped.color };
  }

  return { icon: 'file', color: 'text-gray-400' };
}

/**
 * Get human-readable file type based on filename extension
 * @param filename - Name of the file
 * @returns File type string (e.g., "PDF", "Image", "Code", "File")
 *
 * @example
 * getFileType("document.pdf") // "PDF"
 * getFileType("photo.png") // "Image"
 * getFileType("unknown.xyz") // "File"
 */
export function getFileType(filename: string): string {
  const ext = getFileExtension(filename);
  return FILE_TYPE_MAP[ext]?.type || 'File';
}

/**
 * Check if file is an image based on extension
 * @param filename - Name of the file
 * @returns True if file is an image
 *
 * @example
 * isImageFile("photo.png") // true
 * isImageFile("document.pdf") // false
 */
export function isImageFile(filename: string): boolean {
  const ext = getFileExtension(filename);
  return IMAGE_EXTENSIONS.has(ext);
}

/**
 * Sanitize filename for safe display
 * @param filename - Original filename
 * @returns Sanitized filename with safe characters only
 *
 * Keeps: letters, numbers, spaces, dots, hyphens, underscores
 * Replaces other characters with underscore
 *
 * @example
 * sanitizeFilename("my file.txt") // "my file.txt"
 * sanitizeFilename("file@#$%.txt") // "file_____.txt"
 * sanitizeFilename("file/name.txt") // "file_name.txt"
 */
export function sanitizeFilename(filename: string): string {
  return filename.replace(/[^a-zA-Z0-9\s._-]/g, '_');
}

/**
 * Extract file extension from filename
 * @param filename - Name of the file
 * @returns Lowercase file extension without dot
 *
 * @internal
 */
function getFileExtension(filename: string): string {
  const lastDot = filename.lastIndexOf('.');
  if (lastDot === -1 || lastDot === filename.length - 1) {
    return '';
  }
  return filename.slice(lastDot + 1).toLowerCase();
}
