'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { Check, Copy, ChevronRight, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';

interface CodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  defaultExpanded?: boolean;
}

// Map common language aliases
const languageMap: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  sh: 'bash',
  shell: 'bash',
  yml: 'yaml',
  md: 'markdown',
};

// Custom theme using CSS variables for theme-aware syntax highlighting
const customTheme: { [key: string]: React.CSSProperties } = {
  'code[class*="language-"]': {
    color: 'hsl(var(--codeblock-text))',
    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
    fontSize: '13px',
    lineHeight: '1.6',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    tabSize: 2,
  },
  'pre[class*="language-"]': {
    color: 'hsl(var(--codeblock-text))',
    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
    fontSize: '13px',
    lineHeight: '1.6',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    tabSize: 2,
    margin: 0,
    padding: '12px',
    overflow: 'auto',
    background: 'transparent',
  },
  'comment': { color: 'hsl(var(--syntax-comment))' },
  'prolog': { color: 'hsl(var(--syntax-comment))' },
  'doctype': { color: 'hsl(var(--syntax-comment))' },
  'cdata': { color: 'hsl(var(--syntax-comment))' },
  'punctuation': { color: 'hsl(var(--syntax-operator))' },
  'property': { color: 'hsl(var(--syntax-variable))' },
  'tag': { color: 'hsl(var(--syntax-keyword))' },
  'boolean': { color: 'hsl(var(--syntax-keyword))' },
  'number': { color: 'hsl(var(--syntax-number))' },
  'constant': { color: 'hsl(var(--syntax-builtin))' },
  'symbol': { color: 'hsl(var(--syntax-number))' },
  'deleted': { color: 'hsl(var(--status-error))' },
  'selector': { color: 'hsl(var(--syntax-function))' },
  'attr-name': { color: 'hsl(var(--syntax-variable))' },
  'string': { color: 'hsl(var(--syntax-string))' },
  'char': { color: 'hsl(var(--syntax-string))' },
  'builtin': { color: 'hsl(var(--syntax-builtin))' },
  'inserted': { color: 'hsl(var(--syntax-number))' },
  'operator': { color: 'hsl(var(--syntax-operator))' },
  'entity': { color: 'hsl(var(--syntax-keyword))' },
  'url': { color: 'hsl(var(--syntax-builtin))' },
  'variable': { color: 'hsl(var(--syntax-variable))' },
  'atrule': { color: 'hsl(var(--syntax-keyword))' },
  'attr-value': { color: 'hsl(var(--syntax-string))' },
  'function': { color: 'hsl(var(--syntax-function))' },
  'keyword': { color: 'hsl(var(--syntax-keyword))' },
  'regex': { color: 'hsl(var(--syntax-string))' },
  'important': { color: 'hsl(var(--syntax-keyword))', fontWeight: 'bold' },
  'bold': { fontWeight: 'bold' },
  'italic': { fontStyle: 'italic' },
  'class-name': { color: 'hsl(var(--syntax-builtin))' },
  'parameter': { color: 'hsl(var(--syntax-variable))' },
  'interpolation': { color: 'hsl(var(--syntax-variable))' },
  'punctuation.interpolation-punctuation': { color: 'hsl(var(--syntax-keyword))' },
  'template-string': { color: 'hsl(var(--syntax-string))' },
  'property-access': { color: 'hsl(var(--syntax-variable))' },
  'imports': { color: 'hsl(var(--syntax-variable))' },
  'module': { color: 'hsl(var(--syntax-string))' },
  'script': { color: 'hsl(var(--codeblock-text))' },
  'language-javascript': { color: 'hsl(var(--codeblock-text))' },
  'plain': { color: 'hsl(var(--codeblock-text))' },
  'plain-text': { color: 'hsl(var(--codeblock-text))' },
};

export function CodeBlock({ code, language = 'text', showLineNumbers = false, defaultExpanded = true }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(defaultExpanded);
  const announcementTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const cleanCode = typeof code === 'string' ? code : String(code || '');
  const lines = useMemo(() => cleanCode.split('\n'), [cleanCode]);
  const lineCount = lines.length;

  // Normalize language
  const normalizedLang = languageMap[language.toLowerCase()] || language.toLowerCase();

  // Auto-collapse long code blocks
  useEffect(() => {
    if (lineCount > 15) {
      setExpanded(false);
    }
  }, [lineCount]);

  useEffect(() => {
    return () => {
      if (announcementTimeoutRef.current) {
        clearTimeout(announcementTimeoutRef.current);
      }
    };
  }, []);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(cleanCode);
      setCopied(true);
      announcementTimeoutRef.current = setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  if (!cleanCode || cleanCode.trim() === '') {
    return null;
  }

  const previewLines = Math.min(4, lineCount);
  const previewCode = lines.slice(0, previewLines).join('\n');
  const hiddenLines = lineCount - previewLines;

  // Custom style overrides
  const customStyle: React.CSSProperties = {
    margin: 0,
    padding: '12px',
    fontSize: '13px',
    lineHeight: '1.6',
    borderRadius: 0,
    background: 'transparent',
  };

  return (
    <div className="my-3 rounded-md border border-border overflow-hidden border-l-2 border-l-primary max-w-full overflow-x-auto">
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "flex items-center justify-between px-3 py-1.5 bg-codeblock-bg cursor-pointer hover:bg-codeblock-header transition-colors min-w-0",
          expanded && "border-b border-codeblock-border"
        )}
      >
        <div className="flex items-center gap-2 text-sm">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-codeblock-muted" />
          ) : (
            <ChevronRight className="h-4 w-4 text-codeblock-muted" />
          )}
          <span className="font-medium text-codeblock-text">{language || 'code'}</span>
          <span className="text-codeblock-muted text-xs">
            • {lineCount} {lineCount === 1 ? 'line' : 'lines'}
          </span>
        </div>

        <button
          onClick={handleCopy}
          className={cn(
            "flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors",
            copied
              ? "text-status-success"
              : "text-codeblock-muted hover:text-codeblock-text"
          )}
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>

      {/* Code with syntax highlighting — hidden entirely when collapsed */}
      {expanded ? (
        <div className="bg-codeblock-bg">
          <SyntaxHighlighter
            language={normalizedLang}
            style={customTheme}
            customStyle={customStyle}
            showLineNumbers={showLineNumbers}
            wrapLongLines={true}
          >
            {cleanCode}
          </SyntaxHighlighter>
        </div>
      ) : hiddenLines > 0 ? (
        <div className="bg-codeblock-bg relative">
          <SyntaxHighlighter
            language={normalizedLang}
            style={customTheme}
            customStyle={customStyle}
            showLineNumbers={showLineNumbers}
            wrapLongLines={true}
          >
            {previewCode}
          </SyntaxHighlighter>
          <div
            onClick={() => setExpanded(true)}
            className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-codeblock-bg to-transparent flex items-end justify-center pb-1 cursor-pointer"
          >
            <span className="text-xs text-codeblock-muted hover:text-codeblock-text transition-colors">
              Show {hiddenLines} more {hiddenLines === 1 ? 'line' : 'lines'}...
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
