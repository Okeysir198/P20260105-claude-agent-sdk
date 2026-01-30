'use client';

import { useState, useRef } from 'react';
import type { ImageContentBlock } from '@/types';
import { fileToImageBlock } from '@/lib/message-utils';

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

interface UseImageUploadOptions {
  maxFileSize?: number;
  maxImages?: number;
}

interface UseImageUploadReturn {
  images: ImageContentBlock[];
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  addImages: (files: File[]) => Promise<void>;
  removeImage: (index: number) => void;
  clearImages: () => void;
  hasImages: boolean;
  canAddMore: boolean;
}

export function useImageUpload(options: UseImageUploadOptions = {}): UseImageUploadReturn {
  const { maxFileSize = MAX_FILE_SIZE, maxImages = 10 } = options;
  const [images, setImages] = useState<ImageContentBlock[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function processFile(file: File): Promise<ImageContentBlock | null> {
    if (!file.type.startsWith('image/')) {
      console.error('Invalid file type:', file.type);
      return null;
    }

    if (file.size > maxFileSize) {
      console.error('File too large:', file.size);
      return null;
    }

    return fileToImageBlock(file);
  }

  async function addImages(files: File[]): Promise<void> {
    const validFiles = files.filter((file) => file.type.startsWith('image/'));

    if (images.length + validFiles.length > maxImages) {
      console.error(`Maximum ${maxImages} images allowed`);
      return;
    }

    const newImages: ImageContentBlock[] = [];

    for (const file of validFiles) {
      try {
        const imageBlock = await processFile(file);
        if (imageBlock) {
          newImages.push(imageBlock);
        }
      } catch (error) {
        console.error('Error processing image:', error);
      }
    }

    if (newImages.length > 0) {
      setImages((prev) => [...prev, ...newImages]);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  function removeImage(index: number): void {
    setImages((prev) => prev.filter((_, i) => i !== index));
  }

  function clearImages(): void {
    setImages([]);
  }

  return {
    images,
    fileInputRef,
    addImages,
    removeImage,
    clearImages,
    hasImages: images.length > 0,
    canAddMore: images.length < maxImages
  };
}
