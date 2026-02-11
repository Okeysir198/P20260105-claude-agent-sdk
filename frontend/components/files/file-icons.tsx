'use client';

import {
  FileText,
  FileEdit,
  FileSpreadsheet,
  Image,
  Code,
  Archive,
  BarChart,
  File as FileDefault,
} from 'lucide-react';
import { getFileIcon } from '@/lib/file-utils';

/**
 * Props for FileIcon component
 */
interface FileIconProps {
  /** Name of the file (used to determine extension) */
  filename: string;
  /** Icon size in pixels (default: 24) */
  size?: number;
  /** Additional Tailwind CSS classes */
  className?: string;
}

/**
 * Icon component mapping from icon name strings to Lucide React components
 */
const iconMap = {
  'file-text': FileText,
  'file-edit': FileEdit,
  'file-spreadsheet': FileSpreadsheet,
  'image': Image,
  'code': Code,
  'archive': Archive,
  'bar-chart': BarChart,
  'file': FileDefault,
} as const;

/**
 * FileIcon - Displays an appropriate icon for a file type with proper coloring
 *
 * @example
 * ```tsx
 * <FileIcon filename="document.pdf" size={24} />
 * <FileIcon filename="image.png" size={32} className="ml-2" />
 * <FileIcon filename="script.py" />
 * ```
 */
export function FileIcon({
  filename,
  size = 24,
  className = '',
}: FileIconProps): React.JSX.Element {
  const { icon, color } = getFileIcon(filename);

  const IconComponent = iconMap[icon as keyof typeof iconMap] || FileDefault;

  return <IconComponent size={size} className={`${color} ${className}`} />;
}

/**
 * Props for FileTypeBadge component
 */
interface FileTypeBadgeProps {
  /** Type of file to display badge for */
  fileType: 'input' | 'output';
}

/**
 * Badge styles for input/output file types
 */
const badgeStyles = {
  input:
    'bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-medium px-2 py-0.5 rounded',
  output:
    'bg-green-500/10 text-green-600 dark:text-green-400 text-xs font-medium px-2 py-0.5 rounded',
} as const;

/**
 * FileTypeBadge - Displays a styled badge for input or output file type
 *
 * @example
 * ```tsx
 * <FileTypeBadge fileType="input" />  // Displays: [INPUT]
 * <FileTypeBadge fileType="output" /> // Displays: [OUTPUT]
 * ```
 */
export function FileTypeBadge({
  fileType,
}: FileTypeBadgeProps): React.JSX.Element {
  return (
    <span className={badgeStyles[fileType]}>
      {fileType.toUpperCase()}
    </span>
  );
}
