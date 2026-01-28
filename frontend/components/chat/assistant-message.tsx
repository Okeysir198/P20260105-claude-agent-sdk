'use client';

import type { ChatMessage } from '@/types';
import { formatTime } from '@/lib/utils';
import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from './code-block';
import { Bot } from 'lucide-react';

interface AssistantMessageProps {
  message: ChatMessage;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  // Preprocess content to handle any serialization issues
  const cleanContent = useMemo(() => {
    if (!message.content) return '';

    let content = message.content;

    // Remove tool reference patterns like [Tool: Bash (ID: call_...)] Input: {...}
    content = content.replace(/\[Tool: [^\]]+\]\s*Input:\s*(?:\{[^}]*\}|\[.*?\]|"[^"]*")\s*/g, '');

    // Remove [object Object] artifacts
    content = content.replace(/\[object Object\]/g, '');

    // Clean up multiple consecutive spaces
    content = content.replace(/ {3,}/g, '  ');

    return content;
  }, [message.content]);

  // Don't render if content is empty
  if (!cleanContent || cleanContent.trim() === '') {
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
      <div className="max-w-[85%] flex-1 space-y-1">
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
                // Ensure we always return a string
                return typeof children === 'string' ? children : String(children || '');
              },

              // Code blocks and inline code
              code: ({ className, children, ...props }) => {
                // Determine if inline by checking if we have a language class
                const languageMatch = className?.match(/language-(\w+)/);
                const language = languageMatch ? languageMatch[1] : null;
                const inline = !language;

                // Convert children to string - handle all types robustly
                let codeContent = '';

                if (typeof children === 'string') {
                  codeContent = children;
                } else if (Array.isArray(children)) {
                  codeContent = children
                    .map((child) => {
                      if (typeof child === 'string') return child;
                      if (child && typeof child === 'object') {
                        if ('value' in child) return String(child.value || '');
                        if ('props' in child && child.props?.children) {
                          return String(child.props.children);
                        }
                      }
                      return '';
                    })
                    .join('');
                } else if (children && typeof children === 'object') {
                  if ('value' in children) {
                    codeContent = String((children as any).value || '');
                  } else if ('props' in children && (children as any).props?.children) {
                    codeContent = String((children as any).props.children);
                  } else {
                    codeContent = JSON.stringify(children);
                  }
                } else {
                  codeContent = String(children || '');
                }

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
                const content = Array.isArray(children)
                  ? children.join('')
                  : children;
                return <strong>{String(content || '')}</strong>;
              },

              // Emphasis/italic
              em: ({ children }) => {
                const content = Array.isArray(children)
                  ? children.join('')
                  : children;
                return <em>{String(content || '')}</em>;
              },

              // Links
              a: ({ children, href }) => {
                const content = Array.isArray(children)
                  ? children.join('')
                  : children;
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
            }}
          >
            {cleanContent}
          </ReactMarkdown>
        </div>
        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}
