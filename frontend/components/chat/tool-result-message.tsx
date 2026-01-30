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
  Copy,
  Check,
  AlertTriangle,
  Code2,
  FileJson,
  FileText,
  ChevronsUpDown,
} from 'lucide-react';
import { toast } from 'sonner';

type ContentType = 'code' | 'json' | 'error' | 'text';
type CodeLanguage = 'bash' | 'python' | 'javascript' | 'typescript' | 'json' | 'text';

/**
 * Parse a Python-style string value (handles escaped quotes)
 */
function parsePythonString(str: string, quote: string): { value: string; rest: string } | null {
  let result = '';
  let i = 0;

  while (i < str.length) {
    const char = str[i];

    if (char === '\\') {
      // Escape sequence - in Python repr(), \\ represents a single backslash
      if (i + 1 < str.length) {
        const next = str[i + 1];
        switch (next) {
          case 'n': result += '\n'; break;
          case 'r': result += '\r'; break;
          case 't': result += '\t'; break;
          case '\\': result += '\\'; break;  // \\ becomes \
          case "'": result += "'"; break;
          case '"': result += '"'; break;
          default: result += next; break;
        }
        i += 2;
      } else {
        result += char;
        i++;
      }
    } else if (char === quote) {
      // End of string
      return { value: result, rest: str.slice(i + 1) };
    } else {
      result += char;
      i++;
    }
  }

  // Unclosed string - return what we have
  return { value: result, rest: '' };
}

/**
 * Extract JSON content from various formats:
 * - Python dict with 'text' field: {'type': 'text', 'text': '{...}'}
 * - Direct JSON string
 * - Embedded JSON objects
 */
function extractJsonContent(content: string): string | null {
  const trimmed = content.trim();

  // Try direct JSON parse first
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      const parsed = JSON.parse(trimmed);
      return JSON.stringify(parsed, null, 2);
    } catch {
      // Not valid JSON, continue
    }
  }

  // Check for Python dict pattern: {...'text': '...'...}
  // The text field contains the actual JSON we want to display
  const pythonDictPatterns = [
    /['"]text['"]\s*:\s*'((?:[^'\\]|\\.)*)'/,  // single quotes
    /['"]text['"]\s*:\s*"((?:[^"\\]|\\.)*)"/,  // double quotes
    /['"]content['"]\s*:\s*'((?:[^'\\]|\\.)*)'/,
    /['"]content['"]\s*:\s*"((?:[^"\\]|\\.)*)"/,
  ];

  for (const pattern of pythonDictPatterns) {
    const match = trimmed.match(pattern);
    if (match && match[1]) {
      let extracted = match[1];

      // Unescape Python string escapes
      // Process \\n -> \n (actual newline)
      // But \n in the Python repr means newline, while \\n means literal backslash + n
      // So we need to be careful about the order

      // First, handle double-backslash escapes (\\ -> \)
      extracted = extracted.replace(/\\\\/g, '\u0000');  // Temp placeholder
      // Then handle single-backslash escapes
      extracted = extracted.replace(/\\n/g, '\n');
      extracted = extracted.replace(/\\r/g, '\r');
      extracted = extracted.replace(/\\t/g, '\t');
      extracted = extracted.replace(/\\'/g, "'");
      extracted = extracted.replace(/\\"/g, '"');
      // Restore the placeholder
      extracted = extracted.replace(/\u0000/g, '\\');

      // Try to parse and format as JSON
      try {
        const parsed = JSON.parse(extracted);
        return JSON.stringify(parsed, null, 2);
      } catch {
        // If it looks like JSON but parse failed, return as-is
        if (extracted.trim().startsWith('{') || extracted.trim().startsWith('[')) {
          return extracted;
        }
      }
    }
  }

  // Try to find any JSON object in the text
  // Find opening brace and try to find matching closing brace
  const firstBrace = trimmed.indexOf('{');
  if (firstBrace !== -1) {
    let depth = 0;
    let inString = false;
    let stringChar = '';
    let i = firstBrace;

    for (; i < trimmed.length; i++) {
      const ch = trimmed[i];

      // Handle string boundaries
      if (!inString && (ch === '"' || ch === "'")) {
        inString = true;
        stringChar = ch;
      } else if (inString && ch === stringChar) {
        // Check if escaped
        if (i > 0 && trimmed[i - 1] !== '\\') {
          inString = false;
          stringChar = '';
        }
      } else if (!inString) {
        if (ch === '{') depth++;
        else if (ch === '}') {
          depth--;
          if (depth === 0) {
            // Found matching brace
            const jsonStr = trimmed.slice(firstBrace, i + 1);
            try {
              const parsed = JSON.parse(jsonStr);
              return JSON.stringify(parsed, null, 2);
            } catch {
              // Not valid JSON
            }
            break;
          }
        }
      }
    }
  }

  return null;
}

/**
 * Detect the programming language from tool context or content patterns.
 */
function detectLanguage(
  content: string,
  toolName?: string,
  input?: Record<string, unknown>
): CodeLanguage {
  // From tool type
  if (toolName === 'Bash') return 'bash';

  // From file extension
  const filePath = (input?.file_path as string) || '';
  if (filePath) {
    const ext = filePath.split('.').pop()?.toLowerCase();
    const extMap: Record<string, CodeLanguage> = {
      'py': 'python',
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'json': 'json',
      'sh': 'bash',
      'bash': 'bash',
      'zsh': 'bash',
    };
    if (ext && extMap[ext]) return extMap[ext];
  }

  // From content patterns
  const trimmed = content.trim();

  // JSON check - direct parse
  if ((trimmed.startsWith('{') || trimmed.startsWith('[')) &&
      (trimmed.endsWith('}') || trimmed.endsWith(']'))) {
    try {
      JSON.parse(trimmed);
      return 'json';
    } catch {
      // Not direct JSON, check if it contains extractable JSON
      if (extractJsonContent(trimmed)) {
        return 'json';
      }
    }
  }

  // Python patterns
  if (content.match(/^\s*(def |class |import |from .+ import|if __name__|async def )/m)) {
    return 'python';
  }

  // TypeScript/JavaScript patterns
  if (content.match(/^\s*(const |let |var |function |import |export |interface |type |=>)/m)) {
    return content.match(/:\s*(string|number|boolean|void|any|unknown)\b/) ? 'typescript' : 'javascript';
  }

  // Bash patterns
  if (content.match(/^\s*(#!\/|export |alias |echo |cd |ls |grep |chmod |chown |mkdir |rm |mv |cp )/m)) {
    return 'bash';
  }

  return 'text';
}

function detectContentType(content: string): ContentType {
  if (!content) return 'text';

  // Try to extract JSON content
  const extractedJson = extractJsonContent(content);
  if (extractedJson) {
    return 'json';
  }

  const trimmed = content.trim();

  // Check for error patterns
  const errorPatterns = [
    'error:',
    'exception',
    'traceback',
    'failed:',
    'errno',
  ];
  const lowerContent = content.toLowerCase();
  const hasErrorPattern =
    errorPatterns.some((pattern) => lowerContent.includes(pattern)) ||
    content.match(/^(fatal|error|warning):/im);

  if (hasErrorPattern) {
    return 'error';
  }

  // Check for common code patterns
  const codePatterns = [
    'function ',
    'const ',
    'import ',
    'export ',
    'def ',
    'class ',
    'async ',
    'await ',
    'return ',
  ];
  const hasCodePattern =
    codePatterns.some((pattern) => content.includes(pattern)) ||
    content.match(/^(import|from|package|using|#include)/m);

  if (hasCodePattern) {
    return 'code';
  }

  return 'text';
}

const CONTENT_TYPE_CONFIG: Record<
  ContentType,
  {
    icon: typeof Code2;
    label: string;
    bgVar: string;
    fgVar: string;
    badgeBgVar?: string;
    badgeFgVar?: string;
  }
> = {
  code: {
    icon: Code2,
    label: 'Code',
    bgVar: '--code-bg',
    fgVar: '--code-fg',
    badgeBgVar: '--badge-code-bg',
    badgeFgVar: '--badge-code-fg',
  },
  json: {
    icon: FileJson,
    label: 'JSON',
    bgVar: '--json-bg',
    fgVar: '--json-fg',
    badgeBgVar: '--badge-json-bg',
    badgeFgVar: '--badge-json-fg',
  },
  error: {
    icon: AlertTriangle,
    label: 'Error',
    bgVar: '--error-bg',
    fgVar: '--error-fg',
    badgeBgVar: '--badge-error-bg',
    badgeFgVar: '--badge-error-fg',
  },
  text: {
    icon: FileText,
    label: 'Output',
    bgVar: '--muted',
    fgVar: '--foreground',
  },
};

const COLLAPSED_PREVIEW_LINES = 5;
const EXPANDED_INITIAL_LINES = 20;
const MAX_LINE_LENGTH = 120;

function truncateLine(line: string, maxLength: number): string {
  if (line.length <= maxLength) return line;
  return line.slice(0, maxLength - 3) + '...';
}

function formatJson(content: string): string {
  // First try to extract JSON content if embedded
  const extracted = extractJsonContent(content);
  if (extracted) {
    // If already formatted (has newlines), return as-is
    if (extracted.includes('\n')) {
      return extracted;
    }
    // Otherwise format it
    try {
      const parsed = JSON.parse(extracted);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return extracted;
    }
  }

  // Try direct parse
  try {
    const parsed = JSON.parse(content.trim());
    return JSON.stringify(parsed, null, 2);
  } catch {
    return content;
  }
}

/**
 * Simple JSON syntax highlighting using CSS variables.
 */
function highlightJson(json: string): React.ReactNode {
  const highlighted = json
    .replace(
      /"([^"]+)":/g,
      '<span style="color: hsl(var(--json-key))">"$1"</span>:'
    )
    .replace(
      /: "((?:[^"\\]|\\.)*)"/g,
      ': <span style="color: hsl(var(--json-string))">"$1"</span>'
    )
    .replace(
      /: (\d+\.?\d*)/g,
      ': <span style="color: hsl(var(--json-number))">$1</span>'
    )
    .replace(
      /: (true|false)/g,
      ': <span style="color: hsl(var(--json-keyword))">$1</span>'
    )
    .replace(
      /: (null)/g,
      ': <span style="color: hsl(var(--json-keyword))">$1</span>'
    );

  return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
}

/**
 * Apply syntax highlighting to code based on language.
 */
function highlightCode(code: string, language: CodeLanguage): React.ReactNode {
  if (language === 'json') {
    return highlightJson(code);
  }

  if (language === 'text') {
    return code;
  }

  let highlighted = code;

  // Common patterns for all languages
  // Strings (both single and double quoted)
  highlighted = highlighted.replace(
    /(["'])(?:(?!\1)[^\\]|\\.)*\1/g,
    '<span style="color: hsl(var(--syntax-string))">$&</span>'
  );

  // Comments
  if (language === 'python' || language === 'bash') {
    highlighted = highlighted.replace(
      /(#[^\n]*)/g,
      '<span style="color: hsl(var(--syntax-comment))">$1</span>'
    );
  } else {
    // JS/TS comments
    highlighted = highlighted.replace(
      /(\/\/[^\n]*|\/\*[\s\S]*?\*\/)/g,
      '<span style="color: hsl(var(--syntax-comment))">$&</span>'
    );
  }

  // Numbers
  highlighted = highlighted.replace(
    /\b(\d+\.?\d*)\b/g,
    '<span style="color: hsl(var(--syntax-number))">$1</span>'
  );

  // Language-specific keywords
  const keywords: Record<string, string[]> = {
    python: ['def', 'class', 'import', 'from', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 'with', 'as', 'return', 'yield', 'raise', 'pass', 'break', 'continue', 'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False', 'async', 'await', 'lambda', 'global', 'nonlocal'],
    javascript: ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue', 'try', 'catch', 'finally', 'throw', 'new', 'class', 'extends', 'import', 'export', 'default', 'async', 'await', 'this', 'super', 'null', 'undefined', 'true', 'false', 'typeof', 'instanceof'],
    typescript: ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue', 'try', 'catch', 'finally', 'throw', 'new', 'class', 'extends', 'import', 'export', 'default', 'async', 'await', 'this', 'super', 'null', 'undefined', 'true', 'false', 'typeof', 'instanceof', 'interface', 'type', 'enum', 'implements', 'private', 'public', 'protected', 'readonly', 'static', 'abstract', 'as', 'is', 'keyof', 'never', 'unknown', 'any', 'void', 'string', 'number', 'boolean', 'object'],
    bash: ['if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done', 'case', 'esac', 'function', 'return', 'exit', 'export', 'local', 'readonly', 'declare', 'typeset', 'source', 'alias', 'unalias', 'cd', 'echo', 'printf', 'read', 'set', 'unset', 'shift', 'test', 'true', 'false'],
  };

  const langKeywords = keywords[language] || [];
  if (langKeywords.length > 0) {
    const keywordPattern = new RegExp(`\\b(${langKeywords.join('|')})\\b`, 'g');
    highlighted = highlighted.replace(
      keywordPattern,
      '<span style="color: hsl(var(--syntax-keyword))">$1</span>'
    );
  }

  return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
}

function CopyButton({ content }: { content: string }): React.ReactNode {
  const [copied, setCopied] = useState(false);
  const [announcement, setAnnouncement] = useState('');

  async function handleCopy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setAnnouncement('Output copied to clipboard');
      toast.success('Copied to clipboard');
      setTimeout(() => {
        setCopied(false);
        setAnnouncement('');
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      setAnnouncement('Failed to copy to clipboard');
      toast.error('Failed to copy to clipboard');
      setTimeout(() => setAnnouncement(''), 2000);
    }
  }

  return (
    <>
      {/* Screen reader announcement */}
      <span role="status" aria-live="polite" className="sr-only">
        {announcement}
      </span>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 hover:bg-muted/80"
        onClick={handleCopy}
        title="Copy output to clipboard"
        aria-label={copied ? 'Output copied to clipboard' : 'Copy output to clipboard'}
        aria-pressed={copied}
      >
        {copied ? (
          <Check className="h-3.5 w-3.5" style={{ color: 'hsl(var(--progress-high))' }} aria-hidden="true" />
        ) : (
          <Copy className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
        )}
      </Button>
    </>
  );
}

function LineNumbers({
  count,
  startLine = 1,
}: {
  count: number;
  startLine?: number;
}): React.ReactNode {
  return (
    <div
      className="select-none pr-3 text-right mr-3 min-w-[2.5rem]"
      style={{
        color: 'hsl(var(--json-line-number))',
        borderRight: '1px solid hsl(var(--json-border))',
      }}
    >
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="leading-relaxed">
          {startLine + i}
        </div>
      ))}
    </div>
  );
}

interface ToolResultMessageProps {
  message: ChatMessage;
  toolName?: string;
  input?: Record<string, unknown>;
}

// Memoize the component to prevent unnecessary re-renders
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
  // Extract text from content (handles both string and ContentBlock[])
  const textContent = extractText(message.content);
  const language = detectLanguage(textContent, effectiveToolName, input);
  const contentType = message.isError ? 'error' : detectContentType(textContent);
  const config = CONTENT_TYPE_CONFIG[contentType];
  const ContentIcon = config.icon;

  const formattedContent =
    contentType === 'json' ? formatJson(textContent) : textContent;

  const lines = formattedContent.split('\n');
  const lineCount = lines.length;

  // Determine how many lines to show based on state
  const collapsedPreviewLines = lines
    .slice(0, COLLAPSED_PREVIEW_LINES)
    .map((line) => truncateLine(line, MAX_LINE_LENGTH));
  const collapsedPreview = collapsedPreviewLines.join('\n');
  const hasMoreThanCollapsed = lineCount > COLLAPSED_PREVIEW_LINES;

  // For expanded view: show 20 lines initially, or all if showAllLines is true
  const expandedLinesToShow = showAllLines ? lineCount : Math.min(EXPANDED_INITIAL_LINES, lineCount);
  const hasMoreThanExpanded = lineCount > EXPANDED_INITIAL_LINES;
  const remainingLines = lineCount - EXPANDED_INITIAL_LINES;

  const toggleShowAllLines = useCallback(() => {
    setShowAllLines((prev) => !prev);
  }, []);

  const contentStyle: React.CSSProperties = {
    backgroundColor: `hsl(var(${config.bgVar}))`,
    color: `hsl(var(${config.fgVar}))`,
  };

  if (contentType === 'error') {
    contentStyle.borderLeft = '2px solid hsl(var(--error-border) / 0.5)';
  }

  function getBadgeStyle(): React.CSSProperties {
    if (config.badgeBgVar && config.badgeFgVar) {
      return {
        backgroundColor: `hsl(var(${config.badgeBgVar}) / 0.2)`,
        color: `hsl(var(${config.badgeFgVar}))`,
      };
    }
    return {};
  }

  const getAriaLabel = () => {
    const toolLabel = effectiveToolName || 'Tool';
    const statusLabel = message.isError ? 'error' : 'success';
    return `${toolLabel} output, ${statusLabel}, ${lineCount} ${lineCount === 1 ? 'line' : 'lines'}, ${config.label} format`;
  };

  return (
    <div
      className="group flex gap-2 sm:gap-3 py-1.5 px-2 sm:px-4"
      role="article"
      aria-label={getAriaLabel()}
    >
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

      <div className="min-w-0 flex-1 overflow-hidden">
        <Card
          className={cn(
            'overflow-hidden rounded-lg shadow-sm w-full md:max-w-2xl bg-muted/30 border-l-2 max-w-full',
            message.isError ? 'border-l-destructive' : ''
          )}
          style={message.isError ? {} : { borderLeftColor: 'hsl(var(--progress-high))' }}
          role={message.isError ? 'alert' : undefined}
        >
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
                  className="ml-2 px-1.5 py-0.5 text-xs sm:text-[10px] font-medium rounded"
                  style={getBadgeStyle()}
                  aria-hidden="true"
                >
                  ERROR
                </span>
              )}
            </Button>

            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span
                className="text-[10px] font-medium px-1.5 py-0.5 rounded uppercase"
                style={getBadgeStyle()}
                aria-hidden="true"
              >
                {config.label}
              </span>

              <span className="hidden sm:inline text-[11px] text-muted-foreground" aria-hidden="true">
                {lineCount} {lineCount === 1 ? 'line' : 'lines'}
              </span>

              {expanded &&
                (contentType === 'code' || contentType === 'json') &&
                lineCount > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="hidden sm:flex h-6 px-2 text-[10px] text-muted-foreground hover:text-foreground"
                    onClick={() => setShowLineNumbers(!showLineNumbers)}
                    title="Toggle line numbers"
                    aria-label={showLineNumbers ? 'Hide line numbers' : 'Show line numbers'}
                    aria-pressed={showLineNumbers}
                  >
                    #
                  </Button>
                )}

              <CopyButton content={formattedContent} />
            </div>
          </div>

          <div
            className="overflow-hidden transition-all duration-300 ease-in-out"
            style={{
              maxHeight: expanded ? (showAllLines ? 'none' : 'min(32rem, 60vh)') : 'min(10rem, 30vh)',
            }}
            id={`tool-result-content-${message.toolUseId || message.timestamp}`}
          >
            <pre
              className="overflow-auto p-3 text-xs font-mono leading-relaxed bg-background/30"
              style={{
                ...contentStyle,
                maxHeight: expanded ? (showAllLines ? 'none' : 'min(30rem, 60vh)') : 'min(8rem, 30vh)',
              }}
              tabIndex={0}
              aria-label={`${config.label} output content`}
            >
              {expanded ? (
                <div className="flex">
                  {showLineNumbers &&
                    (contentType === 'code' || contentType === 'json') && (
                      <LineNumbers count={expandedLinesToShow} />
                    )}
                  <code className="flex-1 whitespace-pre-wrap break-words">
                    {contentType === 'json' || contentType === 'code'
                      ? highlightCode(
                          showAllLines
                            ? formattedContent
                            : lines.slice(0, expandedLinesToShow).join('\n'),
                          language
                        )
                      : showAllLines
                        ? formattedContent
                        : lines.slice(0, expandedLinesToShow).join('\n')}
                  </code>
                </div>
              ) : (
                <>
                  <code className="whitespace-pre-wrap break-words">
                    {contentType === 'json' || contentType === 'code'
                      ? highlightCode(collapsedPreview, language)
                      : collapsedPreview}
                  </code>
                  {hasMoreThanCollapsed && (
                    <span className="block mt-2 text-muted-foreground/70 italic text-xs sm:text-[11px]">
                      ... {lineCount - COLLAPSED_PREVIEW_LINES} more{' '}
                      {lineCount - COLLAPSED_PREVIEW_LINES === 1 ? 'line' : 'lines'}
                    </span>
                  )}
                </>
              )}
            </pre>
          </div>

          {/* Show more/less button for large outputs */}
          {expanded && hasMoreThanExpanded && (
            <div className="border-t border-border/30 px-3 py-2 bg-muted/20">
              <Button
                variant="ghost"
                size="sm"
                className="w-full h-7 text-xs text-muted-foreground hover:text-foreground transition-colors"
                onClick={toggleShowAllLines}
                aria-expanded={showAllLines}
                aria-label={showAllLines ? `Show less, display first ${EXPANDED_INITIAL_LINES} lines` : `Show ${remainingLines} more lines`}
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

        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs sm:text-[11px] text-muted-foreground">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
}
