import type { FileInfo } from '@/types/api';

export interface PreviewerProps {
  file: FileInfo;
  content: string | Blob;
}
