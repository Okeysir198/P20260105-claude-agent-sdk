'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Search, X, Table } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { PreviewerProps } from './index';

type WorkbookData = {
  sheetNames: string[];
  sheets: Record<string, string[][]>;
};

function parseSpreadsheet(content: string | Blob): Promise<WorkbookData> {
  return new Promise(async (resolve, reject) => {
    try {
      console.log('[ExcelPreviewer] Parsing spreadsheet, content type:', typeof content, 'is Blob:', content instanceof Blob);
      // Try both named export and default export
      const xlsxModule = await import('xlsx');
      const XLSX = xlsxModule.default || xlsxModule;
      console.log('[ExcelPreviewer] XLSX module loaded:', !!XLSX, 'has read:', typeof XLSX.read === 'function');

      if (!XLSX || typeof XLSX.read !== 'function') {
        throw new Error('XLSX library did not load correctly');
      }

      let workbook;

      if (content instanceof Blob) {
        console.log('[ExcelPreviewer] Content is Blob, size:', content.size, 'type:', content.type);
        const buffer = await content.arrayBuffer();
        console.log('[ExcelPreviewer] ArrayBuffer size:', buffer.byteLength);
        workbook = XLSX.read(buffer, { type: 'array' });
      } else {
        // CSV or text-based spreadsheet
        console.log('[ExcelPreviewer] Content is string, length:', content.length);
        workbook = XLSX.read(content, { type: 'string' });
      }

      console.log('[ExcelPreviewer] Workbook loaded, sheets:', workbook.SheetNames);

      const sheets: Record<string, string[][]> = {};
      for (const name of workbook.SheetNames) {
        sheets[name] = XLSX.utils.sheet_to_json<string[]>(workbook.Sheets[name], {
          header: 1,
          defval: '',
          raw: false,
        });
      }

      console.log('[ExcelPreviewer] Successfully parsed', workbook.SheetNames.length, 'sheets');
      resolve({ sheetNames: workbook.SheetNames, sheets });
    } catch (err) {
      console.error('[ExcelPreviewer] Parse error:', err);
      reject(err);
    }
  });
}

export function ExcelPreviewer({ file, content }: PreviewerProps) {
  const [data, setData] = useState<WorkbookData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSheet, setActiveSheet] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    parseSpreadsheet(content)
      .then((result) => {
        setData(result);
        setActiveSheet(0);
      })
      .catch((err) => {
        console.error('[ExcelPreviewer] Parse error:', err);
        setError(err instanceof Error ? err.message : 'Failed to parse spreadsheet');
      })
      .finally(() => setLoading(false));
  }, [content]);

  const currentSheet = data ? data.sheets[data.sheetNames[activeSheet]] || [] : [];

  const filteredRows = useMemo(() => {
    if (!searchQuery.trim()) return currentSheet;
    const q = searchQuery.toLowerCase();
    return currentSheet.filter((row) =>
      row.some((cell) => String(cell).toLowerCase().includes(q))
    );
  }, [currentSheet, searchQuery]);

  // Get max columns across all rows
  const maxCols = useMemo(() => {
    return currentSheet.reduce((max, row) => Math.max(max, row.length), 0);
  }, [currentSheet]);

  const getColumnLabel = useCallback((index: number): string => {
    let label = '';
    let n = index;
    while (n >= 0) {
      label = String.fromCharCode(65 + (n % 26)) + label;
      n = Math.floor(n / 26) - 1;
    }
    return label;
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <div className="h-8 w-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Parsing spreadsheet…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-4">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!data || currentSheet.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Table className="h-10 w-10 mx-auto mb-3 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">Empty spreadsheet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Modern toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b bg-muted/40">
        <div className="flex items-center gap-1.5">
          <Table className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-[11px] text-muted-foreground hidden xs:inline">
            {currentSheet.length} rows × {maxCols} cols
          </span>
        </div>
        <div className="flex-1" />
        {showSearch ? (
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search cells…"
              className="h-7 w-32 sm:w-40 px-2 text-xs rounded-md border bg-background focus:outline-none focus:ring-1 focus:ring-ring"
              autoFocus
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => { setShowSearch(false); setSearchQuery(''); }}
              className="h-7 w-7"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowSearch(true)}
            className="h-7 w-7"
            title="Search"
          >
            <Search className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto min-h-0" style={{ WebkitOverflowScrolling: 'touch' }}>
        <table className="w-full border-collapse text-xs font-mono">
          <thead className="sticky top-0 z-10">
            <tr className="bg-muted border-b">
              <th className="sticky left-0 z-20 bg-muted w-10 min-w-[40px] px-2 py-1.5 text-[10px] text-muted-foreground font-medium border-r text-center">
                #
              </th>
              {Array.from({ length: maxCols }, (_, i) => (
                <th
                  key={i}
                  className="px-2.5 py-1.5 text-[10px] text-muted-foreground font-medium border-r text-left whitespace-nowrap min-w-[80px]"
                >
                  {getColumnLabel(i)}
                </th>
              ))}
            </tr>
            {/* Header row (first data row) */}
            {currentSheet.length > 0 && !searchQuery && (
              <tr className="bg-muted/70 border-b font-semibold">
                <td className="sticky left-0 z-20 bg-muted/70 px-2 py-1.5 text-[10px] text-muted-foreground text-center border-r">
                  1
                </td>
                {Array.from({ length: maxCols }, (_, i) => (
                  <td
                    key={i}
                    className="px-2.5 py-1.5 border-r text-foreground truncate max-w-[200px]"
                    title={String(currentSheet[0]?.[i] ?? '')}
                  >
                    {String(currentSheet[0]?.[i] ?? '')}
                  </td>
                ))}
              </tr>
            )}
          </thead>
          <tbody>
            {(searchQuery ? filteredRows : currentSheet.slice(1)).map((row, rowIdx) => {
              const displayRowNum = searchQuery
                ? currentSheet.indexOf(row) + 1
                : rowIdx + 2;
              return (
                <tr
                  key={rowIdx}
                  className={rowIdx % 2 === 0 ? 'bg-background' : 'bg-muted/20'}
                >
                  <td className="sticky left-0 z-10 bg-inherit px-2 py-1 text-[10px] text-muted-foreground text-center border-r">
                    {displayRowNum}
                  </td>
                  {Array.from({ length: maxCols }, (_, colIdx) => (
                    <td
                      key={colIdx}
                      className="px-2.5 py-1 border-r text-foreground truncate max-w-[200px]"
                      title={String(row[colIdx] ?? '')}
                    >
                      {String(row[colIdx] ?? '')}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Sheet tabs */}
      {data.sheetNames.length > 1 && (
        <div className="flex items-center gap-0.5 px-2 py-1.5 border-t bg-muted/30 overflow-x-auto shrink-0" style={{ WebkitOverflowScrolling: 'touch' }}>
          {data.sheetNames.map((name, i) => (
            <button
              key={name}
              onClick={() => setActiveSheet(i)}
              className={`px-2.5 py-1 text-[11px] rounded-md whitespace-nowrap transition-colors ${
                i === activeSheet
                  ? 'bg-background text-foreground font-medium shadow-sm border'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default ExcelPreviewer;
