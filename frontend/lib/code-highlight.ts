/**
 * Code and JSON syntax highlighting utilities.
 * Provides simple regex-based highlighting for various languages.
 */

import type { CodeLanguage } from './tool-output-parser';

/**
 * Apply JSON syntax highlighting using CSS variables.
 * Returns an HTML string for use with dangerouslySetInnerHTML.
 */
export function highlightJsonHtml(json: string): string {
  return json
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
}

/**
 * Apply syntax highlighting to code based on language.
 * Returns an HTML string for use with dangerouslySetInnerHTML.
 */
export function highlightCodeHtml(code: string, language: CodeLanguage, keywords: string[]): string {
  if (language === 'json') {
    return highlightJsonHtml(code);
  }

  if (language === 'text') {
    return code;
  }

  let highlighted = code;

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
  if (keywords.length > 0) {
    const keywordPattern = new RegExp(`\\b(${keywords.join('|')})\\b`, 'g');
    highlighted = highlighted.replace(
      keywordPattern,
      '<span style="color: hsl(var(--syntax-keyword))">$1</span>'
    );
  }

  return highlighted;
}
