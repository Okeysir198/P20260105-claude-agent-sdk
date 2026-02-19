'use client';

import { useState, useMemo } from 'react';
import { ChevronRight, ChevronDown, Braces, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import type { PreviewerProps } from './index';

function JsonNode({ data, keyName, depth }: { data: unknown; keyName?: string; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isObject = data !== null && typeof data === 'object';
  const isArray = Array.isArray(data);

  if (!isObject) {
    const color = typeof data === 'string' ? 'text-green-600 dark:text-green-400' :
                  typeof data === 'number' ? 'text-amber-600 dark:text-amber-400' :
                  typeof data === 'boolean' ? 'text-blue-600 dark:text-blue-400' :
                  'text-muted-foreground';
    return <span className={color}>{typeof data === 'string' ? `"${data}"` : String(data)}</span>;
  }

  const entries = Object.entries(data);
  if (entries.length === 0) return <span className="text-muted-foreground">{isArray ? '[]' : '{}'}</span>;

  return (
    <div className="ml-2 sm:ml-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="hover:bg-accent rounded p-0.5 transition-colors -ml-1"
      >
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
      </button>
      {keyName && <><span className="text-blue-600 dark:text-blue-400 font-medium">"{keyName}"</span>: </>}
      <span className="text-muted-foreground text-xs">{!expanded && `${isArray ? 'Array' : 'Object'}(${entries.length})`}</span>
      {expanded && (
        <div className="border-l border-border/40 pl-3 sm:pl-4 ml-1">
          {entries.map(([k, v], i) => (
            <div key={k} className="py-0.5">
              <JsonNode data={v} keyName={isArray ? undefined : k} depth={depth + 1} />
              {i < entries.length - 1 && <span className="text-muted-foreground">,</span>}
            </div>
          ))}
          <span className="text-muted-foreground">{isArray ? ']' : '}'}</span>
        </div>
      )}
    </div>
  );
}

export function JsonPreviewer({ content }: PreviewerProps) {
  const jsonData = useMemo(() => {
    try { return JSON.parse(content as string); }
    catch { return null; }
  }, [content]);

  if (!jsonData) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-4">
          <Braces className="h-10 w-10 mx-auto mb-3 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">Invalid JSON</p>
        </div>
      </div>
    );
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(jsonData, null, 2));
    toast.success('JSON copied to clipboard');
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/40">
        <div className="flex items-center gap-2">
          <Braces className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-[11px] text-muted-foreground">JSON Viewer</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-7 px-2 gap-1.5 text-xs"
        >
          <Copy className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Copy</span>
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3 sm:p-4 bg-muted/20">
        <div className="font-mono text-xs sm:text-sm">
          <JsonNode data={jsonData} depth={0} />
        </div>
      </div>
    </div>
  );
}

export default JsonPreviewer;
