'use client';

import { useCallback, useEffect, useState } from 'react';
import type {
  ThemeConfig,
  ThemeContextValue,
  ClaudeThemeColors,
  ThemeMode,
} from '@/types/theme';
import {
  DEFAULT_THEME_CONFIG,
  resolveThemeColors,
  isThemeDark,
  BORDER_RADIUS_VALUES,
  FONT_FAMILY_VALUES,
  BorderRadiusPreset,
  FontFamilyPreset,
} from '@/types/theme';

/**
 * Default storage key for persisting theme preferences
 */
const DEFAULT_STORAGE_KEY = 'claude-chat-theme';

/**
 * Apply CSS custom properties to the document root
 */
function applyCSSVariables(colors: ClaudeThemeColors): void {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;

  // Apply all color variables
  Object.entries(colors).forEach(([key, value]) => {
    // Convert from '--background' to '--claude-background' CSS variable naming
    const cssVarName = key.replace('--', '--claude-');
    root.style.setProperty(cssVarName, value);
  });
}

/**
 * Apply additional theme settings (border radius, font family)
 */
function applyThemeSettings(config: ThemeConfig): void {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;

  // Apply border radius
  if (config.borderRadius) {
    const radiusValue =
      config.borderRadius in BORDER_RADIUS_VALUES
        ? BORDER_RADIUS_VALUES[config.borderRadius as BorderRadiusPreset]
        : config.borderRadius;
    root.style.setProperty('--claude-radius', radiusValue);
  }

  // Apply font family
  if (config.fontFamily) {
    const fontValue =
      config.fontFamily in FONT_FAMILY_VALUES
        ? FONT_FAMILY_VALUES[config.fontFamily as FontFamilyPreset]
        : config.fontFamily;
    root.style.setProperty('--claude-font-family', fontValue);
  }

  // Apply custom class name if provided
  if (config.customClassName) {
    root.classList.add(config.customClassName);
  }
}

/**
 * Get system color scheme preference
 */
function getSystemPreference(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * Load theme from localStorage
 */
function loadThemeFromStorage(storageKey: string): ThemeConfig | null {
  if (typeof localStorage === 'undefined') return null;

  try {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      return JSON.parse(stored) as ThemeConfig;
    }
  } catch (error) {
    console.warn('Failed to load theme from localStorage:', error);
  }

  return null;
}

/**
 * Save theme to localStorage
 */
function saveThemeToStorage(storageKey: string, config: ThemeConfig): void {
  if (typeof localStorage === 'undefined') return;

  try {
    localStorage.setItem(storageKey, JSON.stringify(config));
  } catch (error) {
    console.warn('Failed to save theme to localStorage:', error);
  }
}

/**
 * Custom hook for managing theme state and CSS variables.
 *
 * This hook manages:
 * - Theme mode (light/dark/system)
 * - CSS variable application to document root
 * - System preference detection via matchMedia
 * - Color overrides support
 * - Mode toggling
 *
 * @param initialTheme - Optional initial theme configuration
 * @param storageKey - localStorage key for persisting preferences
 * @returns Theme context value with state and actions
 *
 * @example
 * ```tsx
 * const { theme, isDark, toggleMode, setMode, colors } = useTheme();
 *
 * // Toggle between light and dark
 * <button onClick={toggleMode}>Toggle Theme</button>
 *
 * // Set specific mode
 * <button onClick={() => setMode('dark')}>Dark Mode</button>
 * ```
 */
export function useTheme(
  initialTheme?: Partial<ThemeConfig>,
  storageKey: string = DEFAULT_STORAGE_KEY
): ThemeContextValue {
  // Track system preference
  const [systemIsDark, setSystemIsDark] = useState<boolean>(() => getSystemPreference());

  // Initialize theme from storage or defaults
  const [theme, setThemeState] = useState<ThemeConfig>(() => {
    // First try to load from storage
    const storedTheme = loadThemeFromStorage(storageKey);
    if (storedTheme) {
      return { ...DEFAULT_THEME_CONFIG, ...storedTheme };
    }

    // Fall back to initial theme or defaults
    return { ...DEFAULT_THEME_CONFIG, ...initialTheme };
  });

  // Calculate derived values
  const isDark = isThemeDark(theme.mode, systemIsDark);
  const colors = resolveThemeColors(theme.mode);

  // Apply CSS variables and dark class whenever theme changes
  useEffect(() => {
    applyCSSVariables(colors);
    applyThemeSettings(theme);

    // Toggle dark class on document
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', isDark);
    }
  }, [colors, theme, isDark]);

  // Listen for system preference changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (event: MediaQueryListEvent) => {
      setSystemIsDark(event.matches);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }

    // Fallback for older browsers
    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  // Persist theme changes to localStorage
  useEffect(() => {
    saveThemeToStorage(storageKey, theme);
  }, [theme, storageKey]);

  // Theme setter with function support
  const setTheme = useCallback(
    (newTheme: ThemeMode | ThemeConfig | ((prev: ThemeConfig) => ThemeConfig)) => {
      setThemeState((prev) => {
        // If it's a string (ThemeMode), convert to config
        if (typeof newTheme === 'string') {
          return { ...prev, mode: newTheme };
        }
        // If it's a function, call it
        if (typeof newTheme === 'function') {
          return newTheme(prev);
        }
        // Otherwise it's a full config object
        return newTheme;
      });
    },
    []
  );

  // Toggle between light and dark modes
  const toggleMode = useCallback(() => {
    setThemeState((prev) => {
      // If currently in system mode, toggle to explicit light or dark
      if (prev.mode === 'system') {
        return { ...prev, mode: systemIsDark ? 'light' : 'dark' };
      }
      // Otherwise toggle between light and dark
      return { ...prev, mode: prev.mode === 'dark' ? 'light' : 'dark' };
    });
  }, [systemIsDark]);

  // Set specific mode
  const setMode = useCallback((mode: ThemeMode) => {
    setThemeState((prev) => ({ ...prev, mode }));
  }, []);

  return {
    theme,
    mode: theme.mode,
    setTheme,
    toggleMode,
    isDark,
    colors,
    setMode,
  };
}

export default useTheme;
