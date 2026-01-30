'use client';

import { useState, useCallback, memo } from 'react';
import type { ChatMessage } from '@/types';
import { formatTime, cn } from '@/lib/utils';
import { extractText } from '@/lib/content-utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
} from 'lucide-react';

// Extracted utilities and sub-components
import {
  detectLanguage,
  detectContentType,
  formatJson,
  KEYWORDS,
  type CodeLanguage,
  type ContentType,
} from '@/lib/tool-output-parser';
import { highlightCodeHtml } from '@/lib/code-highlight';
import {
  CONTENT_TYPE_CONFIG,
  COLLAPSED_PREVIEW_LINES,
  EXPANDED_INITIAL_LINES,
  MAX_LINE_LENGTH,
  truncateLine,
  CopyButton,
  LineNumbers,
} from './tool-output-parts';

interface ToolResultMessageProps {
  message: ChatMessage;
  toolName?: string;
  input?: Record<string, unknown>;
}

// Memoize to prevent unnecessary re-renders
export const ToolResultMessage = memo(ToolResultMessageInner);

function ToolResultMessageInner({
  message,
  toolName,
  input,
}: ToolResultMessageProps): React.ReactNode {
  const [expanded, setExpanded] = useState(false);
  const [showAllLines, setShowAllLines] = useState(false);
  const [showLineNumbers, setShowLineNumbers] = useState(false);

  const effectiveToolName = toolName || message.toolName;
  const textContent = extractText(message.content);
  const language = detectLanguage(textContent, effectiveToolName, input);
  const contentType: ContentType = message.isError ? 'error' : detectContentType(textContent);
  const config = CONTENT_TYPE_CONFIG[contentType];
  const ContentIcon = config.icon;

  const formattedContent = contentType === 'json' ? formatJson(textContent) : textContent;
  const lines = formattedContent.split('\n');
  const lineCount = lines.length;

  // Collapsed preview
  const collapsedPreview = lines
    .slice(0, COLLAPSED_PREVIEW_LINES)
    .map((line) => truncateLine(line, MAX_LINE_LENGTH))
    .join('\n');
  const hasMoreThanCollapsed = lineCount > COLLAPSED_PREVIEW_LINES;

  // Expanded view
  const expandedLinesToShow = showAllLines ? lineCount : Math.min(EXPANDED_INITIAL_LINES, lineCount);
  const hasMoreThanExpanded = lineCount > EXPANDED_INITIAL_LINES;
  const remainingLines = lineCount - EXPANDED_INITIAL_LINES;

  const toggleShowAllLines = useCallback(() => {
    setShowAllLines((prev) => !prev);
  }, []);

  const keywords = KEYWORDS[language] || [];

  return (
    <div
      className="group flex gap-2 sm:gap-3 py-1.5 px-2 sm:px-4"
      role="article"
      aria-label={`${effectiveToolName || 'Tool'} output, ${message.isError ? 'error' : 'success'}, ${lineCount} lines`}
    >
      {/* Status icon */}
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border"
        style={{ color: message.isError ? 'hsl(var(--destructive))' : 'hsl(var(--progress-high))' }}
        aria-hidden="true"
      >
        {message.isError ? (
          <XCircle className="h-3.5 w-3.5" />
        ) : (
          <CheckCircle2 className="h-3.5 w-3.5" />
        )}
      </div>

      {/* Content card */}
      <div className="min-w-0 flex-1 overflow-hidden">
        <Card
          className={cn(
            'overflow-hidden rounded-lg shadow-sm w-full md:max-w-2xl bg-muted/30 border-l-2 max-w-full',
            message.isError ? 'border-l-destructive' : ''
          )}
          style={message.isError ? {} : { borderLeftColor: 'hsl(var(--progress-high))' }}
          role={message.isError ? 'alert' : undefined}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border/50 px-2 sm:px-3 py-1.5 flex-wrap gap-y-1">
            <Button
              variant="ghost"
              size="sm"
              className="justify-start font-mono text-[11px] hover:bg-muted/50 p-0 h-auto"
              onClick={() => setExpanded(!expanded)}
              aria-expanded={expanded}
              aria-controls={`tool-result-content-${message.toolUseId || message.timestamp}`}
            >
              {expanded ? (
                <ChevronDown className="mr-2 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              ) : (
                <ChevronRight className="mr-2 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              )}
              <ContentIcon className="mr-2 h-3 w-3 text-muted-foreground" aria-hidden="true" />
              <span className="text-foreground">
                {message.isError
                  ? 'Error Output'
                  : effectiveToolName
                    ? `${effectiveToolName} Output`
                    : 'Tool Output'}
              </span>
              {message.isError && (
                <span
                  className="ml-2 px-1.5 py-0.5 text-xs sm:text-[10px] font-medium rounded bg-destructive/20 text-destructive"
                  aria-hidden="true"
                >
                  ERROR
                </span>
              )}
            </Button>

            {/* Header actions */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <ContentTypeBadge config={config} />
              <LineCountBadge lineCount={lineCount} />

              {expanded &&
                (contentType === 'code' || contentType === 'json') &&
                lineCount > 1 && (
                  <LineNumbersButton
                    showLineNumbers={showLineNumbers}
                    onClick={() => setShowLineNumbers(!showLineNumbers)}
                  />
                )}

              <CopyButton content={formattedContent} />
            </div>
          </div>

          {/* Content area */}
          <ContentArea
            expanded={expanded}
            showAllLines={showAllLines}
            showLineNumbers={showLineNumbers}
            contentType={contentType}
            language={language}
            keywords={keywords}
            formattedContent={formattedContent}
            lines={lines}
            collapsedPreview={collapsedPreview}
            expandedLinesToShow={expandedLinesToShow}
            hasMoreThanCollapsed={hasMoreThanCollapsed}
            lineCount={lineCount}
            contentBgVar={config.bgVar}
            contentFgVar={config.fgVar}
            isError={message.isError ?? false}
            toolUseId={message.toolUseId}
            timestamp={message.timestamp}
          />

          {/* Show more/less button */}
          {expanded && hasMoreThanExpanded && (
            <div className="border-t border-border/30 px-3 py-2 bg-muted/20">
              <Button
                variant="ghost"
                size="sm"
                className="w-full h-7 text-xs text-muted-foreground hover:text-foreground transition-colors"
                onClick={toggleShowAllLines}
                aria-expanded={showAllLines}
              >
                <ChevronsUpDown className="h-3.5 w-3.5 mr-2" aria-hidden="true" />
                {showAllLines ? (
                  <>Show less (first {EXPANDED_INITIAL_LINES} lines)</>
                ) : (
                  <>Show {remainingLines} more {remainingLines === 1 ? 'line' : 'lines'}</>
                )}
              </Button>
            </div>
          )}
        </Card>

        {/* Timestamp */}
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs sm:text-[11px] text-muted-foreground">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
}

// Sub-components

function ContentTypeBadge({
  config,
}: {
  config: (typeof CONTENT_TYPE_CONFIG)[ContentType];
}) {
  const style = config.badgeBgVar
    ? {
        backgroundColor: `hsl(var(${config.badgeBgVar}) / 0.2)`,
        color: `hsl(var(${config.badgeFgVar}))`,
      }
    : {};

  return (
    <span
      className="text-[10px] font-medium px-1.5 py-0.5 rounded uppercase"
      style={style}
      aria-hidden="true"
    >
      {config.label}
    </span>
  );
}

function LineCountBadge({ lineCount }: { lineCount: number }) {
  return (
    <span className="hidden sm:inline text-[11px] text-muted-foreground" aria-hidden="true">
      {lineCount} {lineCount === 1 ? 'line' : 'lines'}
    </span>
  );
}

function LineNumbersButton({
  showLineNumbers,
  onClick,
}: {
  showLineNumbers: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className="hidden sm:flex h-6 px-2 text-[10px] text-muted-foreground hover:text-foreground"
      onClick={onClick}
      title="Toggle line numbers"
      aria-label={showLineNumbers ? 'Hide line numbers' : 'Show line numbers'}
      aria-pressed={showLineNumbers}
    >
      #
    </Button>
  );
}

interface ContentAreaProps {
  expanded: boolean;
  showAllLines: boolean;
  showLineNumbers: boolean;
  contentType: ContentType;
  language: CodeLanguage;
  keywords: string[];
  formattedContent: string;
  lines: string[];
  collapsedPreview: string;
  expandedLinesToShow: number;
  hasMoreThanCollapsed: boolean;
  lineCount: number;
  contentBgVar: string;
  contentFgVar: string;
  isError: boolean;
  toolUseId?: string;
  timestamp: Date;
}

function ContentArea({
  expanded,
  showAllLines,
  showLineNumbers,
  contentType,
  language,
  keywords,
  formattedContent,
  lines,
  collapsedPreview,
  expandedLinesToShow,
  hasMoreThanCollapsed,
  lineCount,
  contentBgVar,
  contentFgVar,
  isError,
  toolUseId,
  timestamp,
}: ContentAreaProps) {
  const contentStyle: React.CSSProperties = {
    backgroundColor: `hsl(var(${contentBgVar}))`,
    color: `hsl(var(${contentFgVar}))`,
  };

  if (isError) {
    contentStyle.borderLeft = '2px solid hsl(var(--error-border) / 0.5)';
  }

  const maxHeight = expanded
    ? showAllLines
      ? 'none'
      : 'min(32rem, 60vh)'
    : 'min(10rem, 30vh)';

  const preMaxHeight = expanded
    ? showAllLines
      ? 'none'
      : 'min(30rem, 60vh)'
    : 'min(8rem, 30vh)';

  const shouldHighlight = contentType === 'json' || contentType === 'code';

  return (
    <div
      className="overflow-hidden transition-all duration-300 ease-in-out"
      style={{ maxHeight }}
      id={`tool-result-content-${toolUseId || timestamp}`}
    >
      <pre
        className="overflow-auto p-3 text-xs font-mono leading-relaxed bg-background/30"
        style={{ ...contentStyle, maxHeight: preMaxHeight }}
        tabIndex={0}
        aria-label={`${contentType} output content`}
      >
        {expanded ? (
          <ExpandedContent
            showLineNumbers={showLineNumbers}
            shouldHighlight={shouldHighlight}
            language={language}
            keywords={keywords}
            formattedContent={formattedContent}
            lines={lines}
            expandedLinesToShow={expandedLinesToShow}
          />
        ) : (
          <CollapsedContent
            shouldHighlight={shouldHighlight}
            language={language}
            keywords={keywords}
            collapsedPreview={collapsedPreview}
            hasMoreThanCollapsed={hasMoreThanCollapsed}
            lineCount={lineCount}
          />
        )}
      </pre>
    </div>
  );
}

function ExpandedContent({
  showLineNumbers,
  shouldHighlight,
  language,
  keywords,
  formattedContent,
  lines,
  expandedLinesToShow,
}: {
  showLineNumbers: boolean;
  shouldHighlight: boolean;
  language: CodeLanguage;
  keywords: string[];
  formattedContent: string;
  lines: string[];
  expandedLinesToShow: number;
}) {
  const displayContent = lines.slice(0, expandedLinesToShow).join('\n');

  return (
    <div className="flex">
      {showLineNumbers && <LineNumbers count={expandedLinesToShow} />}
      {shouldHighlight ? (
        <code
          className="flex-1 whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: highlightCodeHtml(displayContent, language, keywords) }}
        />
      ) : (
        <code className="flex-1 whitespace-pre-wrap break-words">{displayContent}</code>
      )}
    </div>
  );
}

function CollapsedContent({
  shouldHighlight,
  language,
  keywords,
  collapsedPreview,
  hasMoreThanCollapsed,
  lineCount,
}: {
  shouldHighlight: boolean;
  language: CodeLanguage;
  keywords: string[];
  collapsedPreview: string;
  hasMoreThanCollapsed: boolean;
  lineCount: number;
}) {
  return (
    <>
      {shouldHighlight ? (
        <code
          className="whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: highlightCodeHtml(collapsedPreview, language, keywords) }}
        />
      ) : (
        <code className="whitespace-pre-wrap break-words">{collapsedPreview}</code>
      )}
      {hasMoreThanCollapsed && (
        <span className="block mt-2 text-muted-foreground/70 italic text-xs sm:text-[11px]">
          ... {lineCount - COLLAPSED_PREVIEW_LINES} more{' '}
          {lineCount - COLLAPSED_PREVIEW_LINES === 1 ? 'line' : 'lines'}
        </span>
      )}
    </>
  );
}
