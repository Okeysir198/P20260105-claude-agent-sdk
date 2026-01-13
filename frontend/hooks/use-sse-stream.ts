'use client';

import { useCallback, useRef } from 'react';
import type { ParsedSSEEvent, SSEEventType } from '@/types/events';
import { isSSEEventType } from '@/types/events';

/**
 * Options for the useSSEStream hook
 */
interface UseSSEStreamOptions {
  /** Callback when an event is parsed */
  onEvent?: (event: ParsedSSEEvent) => void;
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
            is_error: data.is_error ?? false
          }
        };
      case 'done':
        return {
          type: 'done',
          data: {
            session_id: data.session_id,
            turn_count: data.turn_count,
            total_cost_usd: data.total_cost_usd
          }
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
 * Low-level hook for parsing Server-Sent Events (SSE) streams.
 *
 * This hook handles the SSE wire format:
 * ```
 * event: <type>
 * data: <json>
 *
 * ```
 *
 * @example
 * ```typescript
 * const { processStream, reset } = useSSEStream();
 *
 * // Process a fetch response stream
 * const response = await fetch('/api/conversations', { method: 'POST' });
 * await processStream(response.body!, (event) => {
 *   switch (event.type) {
 *     case 'text_delta':
 *       console.log('Text:', event.data.text);
 *       break;
 *     case 'done':
 *       console.log('Complete!');
 *       break;
 *   }
 * });
 * ```
 */
export function useSSEStream(options: UseSSEStreamOptions = {}): UseSSEStreamReturn {
  const { onParseError } = options;

  // Buffer for incomplete lines across chunks
  const bufferRef = useRef<string>('');
  // Current event type being parsed
  const currentEventRef = useRef<string | null>(null);
  // Accumulated data lines for current event
  const currentDataRef = useRef<string[]>([]);

  /**
   * Reset the parser state for a new stream
   */
  const reset = useCallback(() => {
    bufferRef.current = '';
    currentEventRef.current = null;
    currentDataRef.current = [];
  }, []);

  /**
   * Parse a chunk of SSE data and return any complete events
   */
  const parseChunk = useCallback((chunk: string): ParsedSSEEvent[] => {
    const events: ParsedSSEEvent[] = [];

    // Add chunk to buffer
    bufferRef.current += chunk;

    // Split into lines (SSE uses \n or \r\n)
    const lines = bufferRef.current.split(/\r?\n/);

    // Keep last potentially incomplete line in buffer
    bufferRef.current = lines.pop() || '';

    for (const line of lines) {
      // Empty line signals end of event
      if (line === '') {
        if (currentEventRef.current && currentDataRef.current.length > 0) {
          const eventType = currentEventRef.current;
          const jsonData = currentDataRef.current.join('\n');

          if (isSSEEventType(eventType)) {
            const parsed = parseEventData(eventType as SSEEventType, jsonData);
            if (parsed) {
              events.push(parsed);
            } else if (onParseError) {
              onParseError(new Error(`Failed to parse event: ${eventType}`), jsonData);
            }
          }
        }
        // Reset for next event
        currentEventRef.current = null;
        currentDataRef.current = [];
        continue;
      }

      // Parse event type line: "event: <type>"
      if (line.startsWith('event:')) {
        currentEventRef.current = line.slice(6).trim();
        continue;
      }

      // Parse data line: "data: <json>"
      if (line.startsWith('data:')) {
        currentDataRef.current.push(line.slice(5).trim());
        continue;
      }

      // Handle colon-prefixed comments (ignore)
      if (line.startsWith(':')) {
        continue;
      }
    }

    return events;
  }, [onParseError]);

  /**
   * Process a ReadableStream and emit events via callback
   */
  const processStream = useCallback(async (
    stream: ReadableStream<Uint8Array>,
    onEvent: (event: ParsedSSEEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const reader = stream.getReader();
    const decoder = new TextDecoder();

    // Reset state for new stream
    reset();

    try {
      while (true) {
        // Check for abort
        if (signal?.aborted) {
          break;
        }

        const { done, value } = await reader.read();

        if (done) {
          // Process any remaining buffered data
          if (bufferRef.current) {
            const finalEvents = parseChunk('\n\n');
            for (const event of finalEvents) {
              onEvent(event);
            }
          }
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        const events = parseChunk(chunk);

        for (const event of events) {
          onEvent(event);
        }
      }
    } finally {
      reader.releaseLock();
    }
  }, [parseChunk, reset]);

  return {
    parseChunk,
    reset,
    processStream,
  };
}

/**
 * Standalone function to parse SSE events from a ReadableStream.
 * Useful when you don't need the hook pattern.
 *
 * @param stream - The ReadableStream to parse
 * @param onEvent - Callback for each parsed event
 * @param signal - Optional AbortSignal for cancellation
 */
export async function parseSSEStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: ParsedSSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();

  let buffer = '';
  let currentEvent: string | null = null;
  let currentData: string[] = [];

  const processLine = (line: string) => {
    // Empty line signals end of event
    if (line === '') {
      if (currentEvent && currentData.length > 0) {
        const eventType = currentEvent;
        const jsonData = currentData.join('\n');
        console.log('[parseSSEStream] Processing event:', eventType, jsonData.substring(0, 100));

        if (isSSEEventType(eventType)) {
          const parsed = parseEventData(eventType as SSEEventType, jsonData);
          if (parsed) {
            onEvent(parsed);
          } else {
            console.warn('[parseSSEStream] Failed to parse event:', eventType, jsonData);
          }
        } else {
          console.warn('[parseSSEStream] Unknown event type:', eventType);
        }
      }
      currentEvent = null;
      currentData = [];
      return;
    }

    if (line.startsWith('event:')) {
      currentEvent = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      currentData.push(line.slice(5).trim());
    }
    // Ignore comments (lines starting with :)
  };

  try {
    while (true) {
      if (signal?.aborted) {
        break;
      }

      const { done, value } = await reader.read();

      if (done) {
        // Process remaining buffer
        if (buffer) {
          const lines = buffer.split(/\r?\n/);
          for (const line of lines) {
            processLine(line);
          }
          processLine(''); // Flush last event
        }
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || '';

      for (const line of lines) {
        processLine(line);
      }
    }
  } finally {
    reader.releaseLock();
  }
}
