export type CodeLanguage = 'bash' | 'python' | 'javascript' | 'typescript' | 'json' | 'text';
export type ContentType = 'code' | 'json' | 'error' | 'text';

export function extractJsonContent(content: string): string | null {
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

  // Check for Python dict pattern
  const pythonDictPatterns = [
    /['"]text['"]\s*:\s*'((?:[^'\\]|\\.)*)'/,
    /['"]text['"]\s*:\s*"((?:[^"\\]|\\.)*)"/,
    /['"]content['"]\s*:\s*'((?:[^'\\]|\\.)*)'/,
    /['"]content['"]\s*:\s*"((?:[^"\\]|\\.)*)"/,
  ];

  for (const pattern of pythonDictPatterns) {
    const match = trimmed.match(pattern);
    if (match && match[1]) {
      let extracted = match[1];

      // Unescape Python string escapes
      extracted = extracted.replace(/\\\\/g, '\u0000');
      extracted = extracted.replace(/\\n/g, '\n');
      extracted = extracted.replace(/\\r/g, '\r');
      extracted = extracted.replace(/\\t/g, '\t');
      extracted = extracted.replace(/\\'/g, "'");
      extracted = extracted.replace(/\\"/g, '"');
      extracted = extracted.replace(/\u0000/g, '\\');

      try {
        const parsed = JSON.parse(extracted);
        return JSON.stringify(parsed, null, 2);
      } catch {
        if (extracted.trim().startsWith('{') || extracted.trim().startsWith('[')) {
          return extracted;
        }
      }
    }
  }

  // Try to find any JSON object in the text
  const firstBrace = trimmed.indexOf('{');
  if (firstBrace !== -1) {
    let depth = 0;
    let inString = false;
    let stringChar = '';
    let i = firstBrace;

    for (; i < trimmed.length; i++) {
      const ch = trimmed[i];

      if (!inString && (ch === '"' || ch === "'")) {
        inString = true;
        stringChar = ch;
      } else if (inString && ch === stringChar) {
        if (i > 0 && trimmed[i - 1] !== '\\') {
          inString = false;
          stringChar = '';
        }
      } else if (!inString) {
        if (ch === '{') depth++;
        else if (ch === '}') {
          depth--;
          if (depth === 0) {
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

export function detectLanguage(
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
      py: 'python',
      js: 'javascript',
      jsx: 'javascript',
      ts: 'typescript',
      tsx: 'typescript',
      json: 'json',
      sh: 'bash',
      bash: 'bash',
      zsh: 'bash',
    };
    if (ext && extMap[ext]) return extMap[ext];
  }

  const trimmed = content.trim();

  // JSON check
  if ((trimmed.startsWith('{') || trimmed.startsWith('[')) &&
      (trimmed.endsWith('}') || trimmed.endsWith(']'))) {
    try {
      JSON.parse(trimmed);
      return 'json';
    } catch {
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

export function detectContentType(content: string): ContentType {
  if (!content) return 'text';

  // Try to extract JSON content
  const extractedJson = extractJsonContent(content);
  if (extractedJson) {
    return 'json';
  }

  // Check for error patterns
  const errorPatterns = ['error:', 'exception', 'traceback', 'failed:', 'errno'];
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

