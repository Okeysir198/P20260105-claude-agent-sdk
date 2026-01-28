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

// Custom VS Code-inspired theme with better readability
const customTheme: { [key: string]: React.CSSProperties } = {
  'code[class*="language-"]': {
    color: '#e0e0e0',
    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
    fontSize: '13px',
    lineHeight: '1.6',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    tabSize: 2,
  },
  'pre[class*="language-"]': {
    color: '#e0e0e0',
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
  'comment': { color: '#6a9955' },
  'prolog': { color: '#6a9955' },
  'doctype': { color: '#6a9955' },
  'cdata': { color: '#6a9955' },
  'punctuation': { color: '#d4d4d4' },
  'property': { color: '#9cdcfe' },
  'tag': { color: '#569cd6' },
  'boolean': { color: '#569cd6' },
  'number': { color: '#b5cea8' },
  'constant': { color: '#4fc1ff' },
  'symbol': { color: '#b5cea8' },
  'deleted': { color: '#f44747' },
  'selector': { color: '#d7ba7d' },
  'attr-name': { color: '#9cdcfe' },
  'string': { color: '#ce9178' },
  'char': { color: '#ce9178' },
  'builtin': { color: '#4ec9b0' },
  'inserted': { color: '#b5cea8' },
  'operator': { color: '#d4d4d4' },
  'entity': { color: '#569cd6' },
  'url': { color: '#4ec9b0' },
  'variable': { color: '#9cdcfe' },
  'atrule': { color: '#c586c0' },
  'attr-value': { color: '#ce9178' },
  'function': { color: '#dcdcaa' },
  'keyword': { color: '#c586c0' },
  'regex': { color: '#d16969' },
  'important': { color: '#569cd6', fontWeight: 'bold' },
  'bold': { fontWeight: 'bold' },
  'italic': { fontStyle: 'italic' },
  'class-name': { color: '#4ec9b0' },
  'parameter': { color: '#9cdcfe' },
  'interpolation': { color: '#9cdcfe' },
  'punctuation.interpolation-punctuation': { color: '#569cd6' },
  'template-string': { color: '#ce9178' },
  'property-access': { color: '#9cdcfe' },
  'imports': { color: '#9cdcfe' },
  'module': { color: '#ce9178' },
  'script': { color: '#e0e0e0' },
  'language-javascript': { color: '#e0e0e0' },
  'plain': { color: '#e0e0e0' },
  'plain-text': { color: '#e0e0e0' },
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

  const previewCode = lines.slice(0, 4).join('\n');
  const hasMoreLines = lineCount > 4;

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
    <div className="my-3 rounded-md border border-border overflow-hidden border-l-2 border-l-primary">
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between px-3 py-1.5 bg-[#1e1e1e] border-b border-[#3c3c3c] cursor-pointer hover:bg-[#252526] transition-colors"
      >
        <div className="flex items-center gap-2 text-sm">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-[#cccccc]" />
          ) : (
            <ChevronRight className="h-4 w-4 text-[#cccccc]" />
          )}
          <span className="font-medium text-[#e0e0e0]">{language || 'code'}</span>
          <span className="text-[#9d9d9d] text-xs">• {lineCount} lines</span>
        </div>

        <button
          onClick={handleCopy}
          className={cn(
            "flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors",
            copied
              ? "text-[#4ec9b0]"
              : "text-[#9d9d9d] hover:text-[#e0e0e0]"
          )}
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>

      {/* Code with syntax highlighting */}
      <div className="bg-[#1e1e1e]">
        {expanded ? (
          <SyntaxHighlighter
            language={normalizedLang}
            style={customTheme}
            customStyle={customStyle}
            showLineNumbers={showLineNumbers}
            wrapLongLines={true}
          >
            {cleanCode}
          </SyntaxHighlighter>
        ) : (
          <div className="relative">
            <SyntaxHighlighter
              language={normalizedLang}
              style={customTheme}
              customStyle={customStyle}
              showLineNumbers={showLineNumbers}
              wrapLongLines={true}
            >
              {previewCode}
            </SyntaxHighlighter>
            {hasMoreLines && (
              <div
                onClick={() => setExpanded(true)}
                className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-[#1e1e1e] to-transparent flex items-end justify-center pb-1 cursor-pointer"
              >
                <span className="text-xs text-[#9d9d9d] hover:text-[#e0e0e0] transition-colors">
                  Show {lineCount - 4} more lines...
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
