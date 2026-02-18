/**
 * Utility for normalizing AskUserQuestion data from WebSocket events.
 *
 * Handles the case where the backend sends questions as a JSON string
 * instead of a parsed array.
 */
import type { UIQuestion } from '@/types';

export interface RawQuestion {
  question: string;
  options: Array<{ label: string; description: string }>;
  multiSelect: boolean;
}

/**
 * Parse and normalize questions from WebSocket event data.
 *
 * @param questions - Raw questions data (array or JSON string)
 * @returns Parsed array of RawQuestion, or null if invalid
 */
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

/**
 * Transform raw WebSocket questions to UI format.
 */
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
