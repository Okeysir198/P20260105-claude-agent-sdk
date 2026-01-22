'use client';

import { memo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { AssistantMessage as AssistantMessageType } from '@/types/messages';
import { cn, formatTime } from '@/lib/utils';
import { TypingIndicator } from './typing-indicator';
import { Check, Copy } from 'lucide-react';

interface AssistantMessageProps {
  message: AssistantMessageType;
  className?: string;
}

function ClaudeAvatar({ className }: { className?: string }): React.ReactElement {
  return (
    <div className={cn(
      'flex-shrink-0 w-8 h-8 rounded-lg',
      'bg-gradient-to-br from-claude-orange-100 to-claude-orange-200',
      'dark:from-claude-orange-900/50 dark:to-claude-orange-800/50',
      'flex items-center justify-center shadow-soft',
      className
    )}>
      <svg
        className="w-4 h-4 text-claude-orange-600 dark:text-claude-orange-400"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="12" cy="12" r="3" fill="currentColor" />
        <path
          d="M12 5C8.134 5 5 8.134 5 12M12 5C15.866 5 19 8.134 19 12M12 5V3M19 12C19 15.866 15.866 19 12 19M19 12H21M12 19C8.134 19 5 15.866 5 12M12 19V21M5 12H3"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}

// Copy button component for code blocks
function CopyButton({ text, onCopy }: { text: string; onCopy?: () => void }): React.ReactElement {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    onCopy?.();
  };

  return (
    <button
      onClick={handleCopy}
      className={cn(
        'absolute top-2 right-2 p-1.5 rounded-md',
        'bg-surface-secondary dark:bg-surface-inverse/20',
        'border border-border-primary',
        'text-text-secondary hover:text-text-primary',
        'opacity-0 group-hover:opacity-100',
        'transition-all duration-200',
        'text-xs font-medium flex items-center gap-1'
      )}
      aria-label="Copy code"
    >
      {copied ? (
        <>
          <Check className="w-3.5 h-3.5" />
          <span>Copied</span>
        </>
      ) : (
        <>
          <Copy className="w-3.5 h-3.5" />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

function MessageContent({ message }: { message: AssistantMessageType }): React.ReactElement | null {
  const hasContent = Boolean(message.content);
  const showTypingIndicator = !hasContent && message.isStreaming;
  const showStreamingCursor = hasContent && message.isStreaming;

  if (showTypingIndicator) {
    return <TypingIndicator />;
  }

  if (!hasContent) {
    return null;
  }

  return (
    <>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0 leading-7">{children}</p>,
          h1: ({ children }) => <h1 className="text-2xl font-bold mb-4 mt-6 first:mt-0 text-text-primary">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-bold mb-3 mt-5 first:mt-0 text-text-primary">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-semibold mb-3 mt-4 first:mt-0 text-text-primary">{children}</h3>,
          ul: ({ children }) => <ul className="list-disc list-inside mb-4 space-y-2 text-text-primary">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside mb-4 space-y-2 text-text-primary">{children}</ol>,
          li: ({ children }) => <li className="leading-7">{children}</li>,
          code: ({ inline, className, children }: { inline?: boolean; className?: string; children?: React.ReactNode }) => {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';
            const codeString = String(children).replace(/\n$/, '');

            if (!inline && codeString.includes('\n')) {
              return (
                <div className="relative group mb-4">
                  <div className="flex items-center justify-between bg-surface-tertiary dark:bg-surface-inverse/20 px-3 py-1.5 rounded-t-lg border-b border-border-primary">
                    <span className="text-xs font-medium text-text-secondary capitalize">{language || 'code'}</span>
                    <CopyButton text={codeString} />
                  </div>
                  <SyntaxHighlighter
                    language={language}
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      borderTopLeftRadius: 0,
                      borderTopRightRadius: 0,
                      borderBottomLeftRadius: '0.5rem',
                      borderBottomRightRadius: '0.5rem',
                      fontSize: '0.875rem',
                      lineHeight: '1.5',
                    }}
                    className="rounded-b-lg"
                  >
                    {codeString}
                  </SyntaxHighlighter>
                </div>
              );
            }

            return (
              <code className="px-1.5 py-0.5 rounded bg-surface-tertiary dark:bg-surface-inverse/10 text-sm font-mono text-text-primary">
                {children}
              </code>
            );
          },
          pre: ({ children }) => <div>{children}</div>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-claude-orange-500 dark:border-claude-orange-400 pl-4 py-2 my-4 italic text-text-secondary bg-surface-tertiary/50 dark:bg-surface-inverse/5 rounded-r">
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-claude-orange-600 dark:text-claude-orange-400 hover:underline font-medium"
            >
              {children}
            </a>
          ),
          strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
          em: ({ children }) => <em className="italic text-text-primary">{children}</em>,
          hr: () => <hr className="my-6 border-border-primary" />,
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-lg border border-border-primary">
              <table className="min-w-full">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-surface-tertiary dark:bg-surface-inverse/10">{children}</thead>
          ),
          tbody: ({ children }) => <tbody className="divide-y divide-border-primary">{children}</tbody>,
          tr: ({ children }) => <tr className="hover:bg-surface-tertiary/30 dark:hover:bg-surface-inverse/5">{children}</tr>,
          th: ({ children }) => <th className="px-4 py-2 text-left text-sm font-semibold text-text-primary">{children}</th>,
          td: ({ children }) => <td className="px-4 py-2 text-sm text-text-primary">{children}</td>,
        }}
      >
        {message.content}
      </ReactMarkdown>
      {showStreamingCursor && (
        <span className="inline-block w-0.5 h-5 ml-0.5 bg-claude-orange-500 animate-typing rounded-full" />
      )}
    </>
  );
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  className
}: AssistantMessageProps): React.ReactElement | null {
  const [isHovered, setIsHovered] = useState(false);
  const [copyClicked, setCopyClicked] = useState(false);

  const handleCopyMessage = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopyClicked(true);
    setTimeout(() => setCopyClicked(false), 2000);
  };

  const hasContent = Boolean(message.content);
  if (!hasContent && !message.isStreaming) {
    return null;
  }

  return (
    <div className={cn('flex justify-start gap-3', className)}>
      <ClaudeAvatar />

      <div className="flex flex-col items-start">
        <div
          className={cn(
            'max-w-[85%] px-4 py-3 relative',
            'bg-surface-secondary border border-border-primary',
            'rounded-lg shadow-soft group'
          )}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          {/* Copy whole message button */}
          <button
            onClick={handleCopyMessage}
            className={cn(
              'absolute top-2 right-2 p-1.5 rounded-md',
              'bg-surface-secondary dark:bg-surface-inverse/20',
              'border border-border-primary',
              'text-text-secondary hover:text-text-primary',
              'opacity-0 group-hover:opacity-100',
              'transition-all duration-200',
              'text-xs font-medium flex items-center gap-1',
              copyClicked && 'opacity-100'
            )}
            aria-label="Copy message"
          >
            {copyClicked ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          <div className="prose-claude text-text-primary break-normal text-base leading-relaxed pr-16">
            <MessageContent message={message} />
          </div>
        </div>
        <div
          className={cn(
            'flex justify-start mt-1 transition-opacity duration-200',
            isHovered ? 'opacity-100' : 'opacity-0'
          )}
        >
          <span className="text-[10px] text-text-tertiary">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
});
