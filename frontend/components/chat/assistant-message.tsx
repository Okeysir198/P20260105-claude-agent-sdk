'use client';

import type { ChatMessage, AudioContentBlock, VideoContentBlock, FileContentBlock, ImageContentBlock } from '@/types';
import { formatTime } from '@/lib/utils';
import { useMemo, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from './code-block';
import { Bot } from 'lucide-react';
import { extractText, normalizeContent } from '@/lib/content-utils';
import { InlineImage, InlineAudioPlayer, InlineVideoPlayer, InlineFileCard } from './media';
import { useLightboxStore } from '@/lib/store/lightbox-store';

// Box-drawing and tree-structure characters used to detect preformatted text
const BOX_DRAWING_RE = /[├└│─┌┐┘┤┬┴┼╔╗╚╝║═]/;
const TREE_LINE_RE = /^[\s]*[├└│|+][\s]*──|^[\s]*│\s/;

/**
 * Convert React children to string, handling all possible types robustly.
 * This prevents [object Object] rendering issues in markdown.
 */
function childrenToString(children: React.ReactNode): string {
  if (typeof children === 'string') {
    return children;
  }
  if (typeof children === 'number') {
    return String(children);
  }
  if (Array.isArray(children)) {
    return children
      .map((child) => {
        if (typeof child === 'string' || typeof child === 'number') {
          return String(child);
        }
        if (child && typeof child === 'object') {
          if ('value' in child) return String((child as any).value || '');
          if ('props' in child && (child as any).props?.children) {
            return String((child as any).props.children);
          }
        }
        return '';
      })
      .join('');
  }
  if (children && typeof children === 'object') {
    if ('value' in children) {
      return String((children as any).value || '');
    }
    if ('props' in children && (children as any).props?.children) {
      return String((children as any).props.children);
    }
    return JSON.stringify(children);
  }
  return String(children || '');
}

/**
 * Detect contiguous blocks of lines containing box-drawing/tree characters
 * and wrap them in fenced code blocks so ReactMarkdown renders them with
 * monospace font and preserved whitespace.
 */
function preprocessContent(content: string): string {
  const lines = content.split('\n');
  const result: string[] = [];
  let blockBuffer: string[] = [];
  let inCodeFence = false;

  const flushBlock = () => {
    if (blockBuffer.length > 0) {
      result.push('```text');
      result.push(...blockBuffer);
      result.push('```');
      blockBuffer = [];
    }
  };

  for (const line of lines) {
    // Track existing fenced code blocks to avoid double-wrapping
    if (/^```/.test(line.trimStart())) {
      if (!inCodeFence) {
        flushBlock();
        inCodeFence = true;
      } else {
        inCodeFence = false;
      }
      result.push(line);
      continue;
    }

    if (inCodeFence) {
      result.push(line);
      continue;
    }

    const isPreformatted = BOX_DRAWING_RE.test(line) || TREE_LINE_RE.test(line);

    if (isPreformatted) {
      blockBuffer.push(line);
    } else {
      flushBlock();
      result.push(line);
    }
  }

  flushBlock();
  return result.join('\n');
}

interface AssistantMessageProps {
  message: ChatMessage;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  const cleanContent = useMemo(() => {
    const raw = extractText(message.content) || '';
    return preprocessContent(raw);
  }, [message.content]);

  // Extract non-text media blocks
  const mediaBlocks = useMemo(() => {
    const blocks = normalizeContent(message.content);
    const images: ImageContentBlock[] = [];
    const audio: AudioContentBlock[] = [];
    const video: VideoContentBlock[] = [];
    const files: FileContentBlock[] = [];

    for (const block of blocks) {
      switch (block.type) {
        case 'image':
          images.push(block as ImageContentBlock);
          break;
        case 'audio':
          audio.push(block as AudioContentBlock);
          break;
        case 'video':
          video.push(block as VideoContentBlock);
          break;
        case 'file':
          files.push(block as FileContentBlock);
          break;
      }
    }

    return { images, audio, video, files };
  }, [message.content]);

  const hasMedia = mediaBlocks.images.length > 0 || mediaBlocks.audio.length > 0 || mediaBlocks.video.length > 0 || mediaBlocks.files.length > 0;
  const hasText = cleanContent && cleanContent.trim() !== '';

  // Collect all image URLs (from content blocks + any inline markdown images are separate)
  const imageUrls = useMemo(() => {
    return mediaBlocks.images.map((block) => {
      return block.source.type === 'url'
        ? block.source.url!
        : block.source.data
          ? `data:${block.source.media_type || 'image/jpeg'};base64,${block.source.data}`
          : '';
    }).filter(Boolean);
  }, [mediaBlocks.images]);

  const openLightbox = useLightboxStore((s) => s.open);

  const handleImageZoom = useCallback(
    (src: string) => {
      const idx = imageUrls.indexOf(src);
      if (idx >= 0) {
        openLightbox(imageUrls, idx);
      } else {
        // Single image from markdown (not in content blocks)
        openLightbox([src], 0);
      }
    },
    [imageUrls, openLightbox],
  );

  // Don't render if no content at all
  if (!hasText && !hasMedia) {
    return null;
  }

  return (
    <div
      className="group flex gap-2 sm:gap-3 py-2 px-2 sm:px-4"
      role="article"
      aria-label="Assistant message"
    >
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted border border-border"
        aria-hidden="true"
      >
        <Bot className="h-4 w-4 text-foreground/80" />
      </div>
      <div className="flex-1 min-w-0 space-y-1">
        {hasText && (
          <div
            className="prose prose-sm dark:prose-invert max-w-none min-h-[1.5em] prose-p:text-foreground prose-headings:text-foreground prose-strong:text-foreground prose-em:text-foreground prose-a:text-primary"
            aria-live="polite"
            aria-atomic="false"
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Text nodes - CRITICAL for preventing [object Object]
                text: ({ children }) => {
                  return childrenToString(children);
                },

                // Code blocks and inline code
                code: ({ className, children, ...props }) => {
                  // Determine if inline by checking if we have a language class
                  const languageMatch = className?.match(/language-(\w+)/);
                  const language = languageMatch ? languageMatch[1] : null;
                  const inline = !language;

                  // Convert children to string - handle all types robustly
                  const codeContent = childrenToString(children);

                  // Debug logging
                  if (process.env.NODE_ENV === 'development' && !inline && (!codeContent || codeContent.trim() === '')) {
                    console.warn('Empty code content detected:', { children, className, language });
                  }

                  if (!inline) {
                    return (
                      <CodeBlock
                        code={codeContent.trim()}
                        language={language}
                      />
                    );
                  }

                  return (
                    <code
                      className="px-1.5 py-0.5 rounded bg-muted/50 border border-border/50 text-xs font-mono text-foreground"
                      {...props}
                    >
                      {codeContent}
                    </code>
                  );
                },

                // Pre tags - pass through children
                pre: ({ children }) => {
                  return <>{children}</>;
                },

                // Paragraphs - check for block children
                p: ({ children }) => {
                  const hasBlocks = Array.isArray(children) &&
                    children.some((child: any) =>
                      child?.type === 'element' &&
                      ['pre', 'div', 'blockquote', 'ul', 'ol', 'table', 'img'].includes(child?.tagName)
                    );

                  if (hasBlocks) {
                    return <div>{children}</div>;
                  }
                  return <p>{children}</p>;
                },

                // Strong/bold
                strong: ({ children }) => {
                  return <strong>{childrenToString(children)}</strong>;
                },

                // Emphasis/italic
                em: ({ children }) => {
                  return <em>{childrenToString(children)}</em>;
                },

                // Links
                a: ({ children, href }) => {
                  const content = childrenToString(children);
                  return (
                    <a
                      href={href}
                      className="text-primary hover:underline"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`${content} (opens in new tab)`}
                    >
                      {content}
                    </a>
                  );
                },

                // Headings
                h1: ({ children }) => <h1 className="text-2xl font-semibold mt-6 mb-2">{children}</h1>,
                h2: ({ children }) => <h2 className="text-xl font-semibold mt-6 mb-2">{children}</h2>,
                h3: ({ children }) => <h3 className="text-lg font-semibold mt-6 mb-2">{children}</h3>,

                // Lists
                ul: ({ children }) => <ul className="list-disc pl-6 my-4 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-6 my-4 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="leading-relaxed">{children}</li>,

                // Blockquotes
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-primary pl-4 italic text-muted-foreground my-4">
                    {children}
                  </blockquote>
                ),

                // Horizontal rule
                hr: () => (
                  <hr className="my-6 border-t border-border" />
                ),

                // Tables
                table: ({ children }) => (
                  <div className="my-4 overflow-x-auto scrollbar-thin rounded-md border border-border">
                    <table className="w-full border-collapse text-sm">{children}</table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-muted/60">{children}</thead>
                ),
                tbody: ({ children }) => <tbody>{children}</tbody>,
                tr: ({ children }) => (
                  <tr className="border-b border-border last:border-b-0">{children}</tr>
                ),
                th: ({ children }) => (
                  <th className="px-3 py-2 text-left font-medium text-foreground">{children}</th>
                ),
                td: ({ children }) => (
                  <td className="px-3 py-2 text-foreground">{children}</td>
                ),

                // Images - use InlineImage component
                img: ({ src, alt }) => (
                  <InlineImage
                    src={typeof src === 'string' ? src : ''}
                    alt={typeof alt === 'string' ? alt : ''}
                    onClickZoom={handleImageZoom}
                  />
                ),

                // Strikethrough
                del: ({ children }) => (
                  <del className="text-muted-foreground line-through">{children}</del>
                ),
              }}
            >
              {cleanContent}
            </ReactMarkdown>
          </div>
        )}

        {/* Media blocks below text */}
        {hasMedia && (
          <div className="flex flex-wrap gap-2 mt-2">
            {mediaBlocks.images.map((block, index) => {
              const imageUrl = block.source.type === 'url'
                ? block.source.url
                : block.source.data
                  ? `data:${block.source.media_type || 'image/jpeg'};base64,${block.source.data}`
                  : '';
              return imageUrl ? (
                <InlineImage
                  key={`image-${index}`}
                  src={imageUrl}
                  alt={`Image ${index + 1}`}
                  onClickZoom={handleImageZoom}
                />
              ) : null;
            })}
            {mediaBlocks.audio.map((block, index) => (
              <InlineAudioPlayer
                key={`audio-${index}`}
                src={block.source.url}
                filename={block.filename}
                mimeType={block.source.mime_type}
              />
            ))}
            {mediaBlocks.video.map((block, index) => (
              <InlineVideoPlayer
                key={`video-${index}`}
                src={block.source.url}
                filename={block.filename}
                mimeType={block.source.mime_type}
              />
            ))}
            {mediaBlocks.files.map((block, index) => (
              <InlineFileCard
                key={`file-${index}`}
                filename={block.filename}
                url={block.source.url}
                size={block.size}
                mimeType={block.source.mime_type}
              />
            ))}
          </div>
        )}

        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}
