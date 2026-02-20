'use client';

import { useState, useRef } from 'react';
import type { ImageContentBlock } from '@/types';
import { fileToImageBlock } from '@/lib/message-utils';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

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

    // Check if compression is needed
    const needsCompression = file.size > maxFileSize;

    if (needsCompression) {
      console.log(`Compressing ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB) to fit under ${(maxFileSize / 1024 / 1024).toFixed(2)} MB limit...`);
    }

    try {
      const imageBlock = await fileToImageBlock(file, maxFileSize);

      if (needsCompression) {
        console.log(`Successfully compressed ${file.name}`);
      }

      return imageBlock;
    } catch (error) {
      console.error('Error processing image:', error);
      return null;
    }
  }

  async function addImages(files: File[]): Promise<void> {
    const validFiles = files.filter((file) => file.type.startsWith('image/'));

    if (images.length + validFiles.length > maxImages) {
      console.error(`Maximum ${maxImages} images allowed`);
      return;
    }

    const newImages: ImageContentBlock[] = [];

    for (const file of validFiles) {
      const imageBlock = await processFile(file);
      if (imageBlock) {
        newImages.push(imageBlock);
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
