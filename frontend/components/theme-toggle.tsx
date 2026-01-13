'use client';

import { Moon, Sun, Monitor } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useThemeContext } from '@/components/providers/theme-provider';

export function ThemeToggle() {
  const { theme, toggleMode, isDark } = useThemeContext();

  const Icon = theme.mode === 'system' ? Monitor : isDark ? Moon : Sun;

  return (
    <Button variant="ghost" size="icon" onClick={toggleMode}>
      <Icon className="h-4 w-4" />
    </Button>
  );
}
