/**
 * Auto-resize Hook for Textareas
 *
 * Automatically adjusts textarea height based on content,
 * with configurable min and max height constraints.
 *
 * @module hooks/use-auto-resize
 */

import { useEffect, RefObject } from 'react';

/**
 * Hook that automatically resizes a textarea based on its content.
 *
 * @param ref - React ref to the textarea element
 * @param value - Current value of the textarea (triggers resize on change)
 * @param minHeight - Minimum height in pixels (default: 44)
 * @param maxHeight - Maximum height in pixels (default: 200)
 *
 * @example
 * ```tsx
 * const textareaRef = useRef<HTMLTextAreaElement>(null);
 * const [value, setValue] = useState('');
 *
 * useAutoResize(textareaRef, value, 44, 200);
 *
 * return (
 *   <textarea
 *     ref={textareaRef}
 *     value={value}
 *     onChange={(e) => setValue(e.target.value)}
 *   />
 * );
 * ```
 */
export function useAutoResize(
  ref: RefObject<HTMLTextAreaElement | null>,
  value: string,
  minHeight: number = 44,
  maxHeight: number = 200
): void {
  useEffect(() => {
    const textarea = ref.current;
    if (!textarea) return;

    // Reset height to auto to get accurate scrollHeight
    textarea.style.height = 'auto';

    // Calculate new height within bounds
    const scrollHeight = textarea.scrollHeight;
    const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);

    // Apply the calculated height
    textarea.style.height = `${newHeight}px`;

    // Add overflow behavior based on content size
    textarea.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden';
  }, [ref, value, minHeight, maxHeight]);
}
