import type { UIQuestion } from '@/types';

export interface RawQuestion {
  question: string;
  options: Array<{ label: string; description: string }>;
  multiSelect: boolean;
}

export function normalizeQuestions(
  questions: RawQuestion[] | string | unknown
): RawQuestion[] | null {
  if (Array.isArray(questions)) {
    return questions;
  }

  if (typeof questions === 'string') {
    try {
      const parsed = JSON.parse(questions);
      if (Array.isArray(parsed)) {
        return parsed;
      }
      console.error('[WebSocket] Parsed questions is not an array:', parsed);
    } catch (err) {
      console.error('[WebSocket] Failed to parse questions JSON string:', err);
    }
    return null;
  }

  console.error('[WebSocket] Unexpected questions type:', typeof questions);
  return null;
}

export function toUIQuestions(raw: RawQuestion[]): UIQuestion[] {
  return raw.map((q) => ({
    question: q.question,
    options: q.options.map((opt) => ({
      value: opt.label,
      description: opt.description,
    })),
    allowMultiple: q.multiSelect,
  }));
}
