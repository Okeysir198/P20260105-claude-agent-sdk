'use client';

import { useCallback, useRef } from 'react';
import type { ParsedSSEEvent, SSEEventType } from '@/types/events';
import { isSSEEventType } from '@/types/events';

/**
 * Options for the useSSEStream hook
 */
interface UseSSEStreamOptions {
  /** Callback when an error occurs during parsing */
  onParseError?: (error: Error, rawData: string) => void;
}

/**
 * Return type for the useSSEStream hook
 */
interface UseSSEStreamReturn {
  /** Parse a chunk of SSE data and return parsed events */
  parseChunk: (chunk: string) => ParsedSSEEvent[];
  /** Reset the parser state (for new streams) */
  reset: () => void;
  /** Parse SSE from a ReadableStream */
  processStream: (
    stream: ReadableStream<Uint8Array>,
    onEvent: (event: ParsedSSEEvent) => void,
    signal?: AbortSignal
  ) => Promise<void>;
}

/**
 * Parse JSON data into a typed SSE event
 */
function parseEventData(eventType: SSEEventType, jsonData: string): ParsedSSEEvent | null {
  try {
    const data = JSON.parse(jsonData);

    switch (eventType) {
      case 'session_id':
        return { type: 'session_id', data: { session_id: data.session_id } };
      case 'text_delta':
        return { type: 'text_delta', data: { text: data.text } };
      case 'tool_use':
        return { type: 'tool_use', data: { tool_name: data.tool_name, input: data.input } };
      case 'tool_result':
        return {
          type: 'tool_result',
          data: {
            tool_use_id: data.tool_use_id,
            content: data.content,
            is_error: data.is_error ?? false,
          },
        };
      case 'done':
        return {
          type: 'done',
          data: {
            session_id: data.session_id,
            turn_count: data.turn_count,
            total_cost_usd: data.total_cost_usd,
          },
        };
      case 'error':
        return { type: 'error', data: { error: data.error } };
      default:
        return null;
    }
  } catch {
    return null;
  }
}

/**
 * Parser state for SSE processing
 */
interface SSEParserState {
  buffer: string;
  currentEvent: string | null;
  currentData: string[];
}

/**
 * Create initial parser state
 */
function createParserState(): SSEParserState {
  return {
    buffer: '',
    currentEvent: null,
    currentData: [],
  };
}

/**
 * Process SSE lines and emit parsed events
 */
function processSSELines(
  lines: string[],
  state: SSEParserState,
  onEvent?: (event: ParsedSSEEvent) => void
): ParsedSSEEvent[] {
  const events: ParsedSSEEvent[] = [];

  for (const line of lines) {
    // Empty line signals end of event
    if (line === '') {
      if (state.currentEvent && state.currentData.length > 0) {
        const eventType = state.currentEvent;
        const jsonData = state.currentData.join('\n');

        if (isSSEEventType(eventType)) {
          const parsed = parseEventData(eventType as SSEEventType, jsonData);
          if (parsed) {
            events.push(parsed);
            onEvent?.(parsed);
          }
        }
      }
      state.currentEvent = null;
      state.currentData = [];
      continue;
    }

    // Parse event type line: "event: <type>"
    if (line.startsWith('event:')) {
      state.currentEvent = line.slice(6).trim();
      continue;
    }

    // Parse data line: "data: <json>"
    if (line.startsWith('data:')) {
      state.currentData.push(line.slice(5).trim());
      continue;
    }

    // Ignore comment lines starting with ':'
  }

  return events;
}

/**
 * Low-level hook for parsing Server-Sent Events (SSE) streams.
 *
 * This hook handles the SSE wire format:
 * ```
 * event: <type>
 * data: <json>
 *
 * ```
 */
export function useSSEStream(options: UseSSEStreamOptions = {}): UseSSEStreamReturn {
  const { onParseError } = options;

  const stateRef = useRef<SSEParserState>(createParserState());

  /**
   * Reset the parser state for a new stream
   */
  const reset = useCallback((): void => {
    stateRef.current = createParserState();
  }, []);

  /**
   * Parse a chunk of SSE data and return any complete events
   */
  const parseChunk = useCallback(
    (chunk: string): ParsedSSEEvent[] => {
      const state = stateRef.current;

      // Add chunk to buffer
      state.buffer += chunk;

      // Split into lines (SSE uses \n or \r\n)
      const lines = state.buffer.split(/\r?\n/);

      // Keep last potentially incomplete line in buffer
      state.buffer = lines.pop() || '';

      const events = processSSELines(lines, state);

      // Report parse errors for failed events
      if (onParseError && state.currentEvent && state.currentData.length > 0) {
        const jsonData = state.currentData.join('\n');
        try {
          JSON.parse(jsonData);
        } catch {
          onParseError(new Error(`Failed to parse event: ${state.currentEvent}`), jsonData);
        }
      }

      return events;
    },
    [onParseError]
  );

  /**
   * Process a ReadableStream and emit events via callback
   */
  const processStream = useCallback(
    async (
      stream: ReadableStream<Uint8Array>,
      onEvent: (event: ParsedSSEEvent) => void,
      signal?: AbortSignal
    ): Promise<void> => {
      const reader = stream.getReader();
      const decoder = new TextDecoder();

      reset();

      try {
        while (true) {
          if (signal?.aborted) break;

          const { done, value } = await reader.read();

          if (done) {
            // Process any remaining buffered data
            if (stateRef.current.buffer) {
              const finalEvents = parseChunk('\n\n');
              finalEvents.forEach(onEvent);
            }
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          const events = parseChunk(chunk);
          events.forEach(onEvent);
        }
      } finally {
        reader.releaseLock();
      }
    },
    [parseChunk, reset]
  );

  return {
    parseChunk,
    reset,
    processStream,
  };
}

/**
 * Standalone function to parse SSE events from a ReadableStream.
 * Useful when you don't need the hook pattern.
 */
export async function parseSSEStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: ParsedSSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  const state = createParserState();

  try {
    while (true) {
      if (signal?.aborted) break;

      const { done, value } = await reader.read();

      if (done) {
        // Process remaining buffer
        if (state.buffer) {
          const lines = state.buffer.split(/\r?\n/);
          processSSELines(lines, state, onEvent);
          // Flush last event
          processSSELines([''], state, onEvent);
        }
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      state.buffer += chunk;

      const lines = state.buffer.split(/\r?\n/);
      state.buffer = lines.pop() || '';

      processSSELines(lines, state, onEvent);
    }
  } finally {
    reader.releaseLock();
  }
}
