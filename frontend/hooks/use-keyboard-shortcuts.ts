'use client';

import { useEffect, useCallback } from 'react';

interface ShortcutConfig {
  /** Keyboard shortcut (e.g., 'cmd+k', 'ctrl+n', 'arrowdown') */
  key: string;
  /** Callback when shortcut is triggered */
  handler: (e: KeyboardEvent) => void;
  /** Description for accessibility/help */
  description?: string;
  /** Prevent default browser behavior */
  preventDefault?: boolean;
}

interface KeyboardShortcutsOptions {
  /** Whether shortcuts are enabled */
  enabled?: boolean;
  /** Log shortcuts in development */
  debug?: boolean;
}

/**
 * Global keyboard shortcuts hook.
 *
 * Handles keyboard shortcuts with proper modifier key detection
 * across platforms (Mac uses Cmd/⌘, Windows/Linux use Ctrl).
 *
 * Supported modifiers:
 * - cmd/ctrl: Command on Mac, Control on Windows/Linux
 * - shift: Shift key
 * - alt/option: Alt on Windows/Linux, Option on Mac
 *
 * Special keys: arrowup, arrowdown, arrowleft, arrowright, enter, escape, space, tab
 *
 * @example
 * ```tsx
 * useKeyboardShortcuts([
 *   { key: 'cmd+k', handler: () => console.log('Command menu'), description: 'Open command menu' },
 *   { key: 'ctrl+n', handler: () => console.log('New chat'), description: 'New chat' },
 *   { key: 'arrowdown', handler: (e) => console.log('Navigate down'), preventDefault: true },
 * ], { enabled: true });
 * ```
 */
export function useKeyboardShortcuts(
  shortcuts: ShortcutConfig[],
  options: KeyboardShortcutsOptions = {}
) {
  const { enabled = true, debug = false } = options;

  const normalizeKey = useCallback((key: string): string => {
    return key.toLowerCase().replace(/key$/, '');
  }, []);

  const parseShortcut = useCallback((shortcut: string) => {
    const parts = shortcut.toLowerCase().split('+');
    const key = parts[parts.length - 1];
    const modifiers = parts.slice(0, -1);

    return {
      key: normalizeKey(key || ''),
      cmd: modifiers.includes('cmd') || modifiers.includes('ctrl'),
      ctrl: modifiers.includes('ctrl') || modifiers.includes('cmd'),
      shift: modifiers.includes('shift'),
      alt: modifiers.includes('alt') || modifiers.includes('option'),
    };
  }, [normalizeKey]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger in input fields unless it's Escape or specific shortcuts
      const target = e.target as HTMLElement;
      const isInputField =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.contentEditable === 'true' ||
        target.getAttribute('role') === 'textbox';

      if (isInputField && e.key !== 'Escape') {
        return;
      }

      const eventKey = normalizeKey(e.key);
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const cmdOrCtrl = isMac ? e.metaKey : e.ctrlKey;

      for (const shortcut of shortcuts) {
        const parsed = parseShortcut(shortcut.key);

        // Check if all modifiers match
        const modifiersMatch =
          parsed.cmd === cmdOrCtrl &&
          parsed.ctrl === e.ctrlKey &&
          parsed.shift === e.shiftKey &&
          parsed.alt === e.altKey;

        // Check if key matches
        const keyMatches = parsed.key === eventKey;

        if (modifiersMatch && keyMatches) {
          if (debug) {
            console.log(`[Keyboard Shortcut] Triggered: ${shortcut.key}`, shortcut.description);
          }

          if (shortcut.preventDefault !== false) {
            e.preventDefault();
          }

          shortcut.handler(e);
          break; // Only trigger first matching shortcut
        }
      }
    },
    [enabled, shortcuts, parseShortcut, normalizeKey, debug]
  );

  useEffect(() => {
    if (enabled) {
      document.addEventListener('keydown', handleKeyDown);

      return () => {
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
    return undefined;
  }, [enabled, handleKeyDown]);

  // Return shortcuts for help/keyboard shortcut dialog
  return {
    shortcuts: shortcuts.map((s) => ({
      ...s,
      // Format for display (e.g., "Cmd+K" on Mac, "Ctrl+N" on Windows)
      displayKey: s.key
        .replace('cmd', '⌘')
        .replace('ctrl', 'Ctrl')
        .replace('shift', 'Shift')
        .replace('alt', 'Alt')
        .replace('option', '⌥')
        .split('+')
        .map((part, i, arr) => {
          // Capitalize first letter, keep arrows lowercase
          const formatted =
            part.startsWith('arrow') && part.length > 5
              ? part.charAt(5).toUpperCase() + part.slice(6)
              : part.charAt(0).toUpperCase() + part.slice(1);
          // Join with + for modifiers
          return arr.length > 1 && i < arr.length - 1 ? `${formatted}+` : formatted;
        })
        .join(''),
    })),
  };
}
