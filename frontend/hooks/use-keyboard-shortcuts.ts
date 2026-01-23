'use client';

import { useEffect } from 'react';

export function useKeyboardShortcuts(
  shortcuts: Record<string, (e: KeyboardEvent) => void>,
  deps: React.DependencyList = []
) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = [
        e.metaKey ? 'cmd' : '',
        e.ctrlKey ? 'ctrl' : '',
        e.shiftKey ? 'shift' : '',
        e.altKey ? 'alt' : '',
        e.key.toLowerCase(),
      ]
        .filter(Boolean)
        .join('+');

      const handler = shortcuts[key];
      if (handler) {
        e.preventDefault();
        handler(e);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts, ...deps]);
}

export function useChatKeyboardShortcuts({
  onFocusInput,
  onNewChat,
  onToggleSidebar,
  isEnabled = true,
}: {
  onFocusInput: () => void;
  onNewChat: () => void;
  onToggleSidebar: () => void;
  isEnabled?: boolean;
}) {
  useKeyboardShortcuts(
    isEnabled
      ? {
          'cmd+k': onFocusInput,
          'ctrl+k': onFocusInput,
          'cmd+shift+n': onNewChat,
          'ctrl+shift+n': onNewChat,
          'cmd+[/]': onToggleSidebar,
          'ctrl+[/]': onToggleSidebar,
        }
      : {},
    [onFocusInput, onNewChat, onToggleSidebar, isEnabled]
  );
}
