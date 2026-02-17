'use client';

import { useState, useMemo } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import type { PreviewerProps } from './index';

function JsonNode({ data, keyName, depth }: { data: unknown; keyName?: string; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isObject = data !== null && typeof data === 'object';
  const isArray = Array.isArray(data);

  if (!isObject) {
    const color = typeof data === 'string' ? 'text-green-500' : typeof data === 'number' ? 'text-green-600' : 'text-yellow-500';
    return <span className={color}>{typeof data === 'string' ? `"${data}"` : String(data)}</span>;
  }

  const entries = Object.entries(data);
  if (entries.length === 0) return <span className="text-muted-foreground">{isArray ? '[]' : '{}'}</span>;

  return (
    <div className="ml-4">
      <button onClick={() => setExpanded(!expanded)} className="hover:bg-accent rounded p-0.5">
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
      </button>
      {keyName && <><span className="text-blue-500">"{keyName}"</span>: </>}
      <span className="text-muted-foreground text-xs">{!expanded && `${isArray ? 'Array' : 'Object'}(${entries.length})`}</span>
      {expanded && (
        <div className="border-l border-border/50 pl-4 ml-1">
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

  if (!jsonData) return <div className="p-4 text-destructive">Invalid JSON</div>;

  return <div className="p-4 font-mono text-sm bg-muted rounded-lg"><JsonNode data={jsonData} depth={0} /></div>;
}

export default JsonPreviewer;
