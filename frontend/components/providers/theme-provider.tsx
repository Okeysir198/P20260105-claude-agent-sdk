'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from 'react';
import type {
  ThemeConfig,
  ThemeContextValue,
  ClaudeThemeColors,
  ThemeMode,
  BorderRadiusPreset,
  FontFamilyPreset,
} from '@/types/theme';
import {
  DEFAULT_THEME_CONFIG,
  LIGHT_THEME_COLORS,
  DARK_THEME_COLORS,
  resolveThemeColors,
  isThemeDark,
  BORDER_RADIUS_VALUES,
  FONT_FAMILY_VALUES,
} from '@/types/theme';
import { CLAUDE_COLORS } from '@/lib/constants';

/**
 * Theme context for providing theme state throughout the component tree
 */
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

/**
 * Apply CSS custom properties to the document root element
 */
function applyCSSVariables(colors: ClaudeThemeColors): void {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;

  // Apply all color variables with claude prefix
  Object.entries(colors).forEach(([key, value]) => {
    // Convert from '--background' to '--claude-background' CSS variable naming
    const cssVarName = key.replace('--', '--claude-');
    root.style.setProperty(cssVarName, value);
  });
}

/**
 * Apply additional theme settings like border radius and font family
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
 * Remove custom class from document root
 */
function removeCustomClassName(className?: string): void {
  if (typeof document === 'undefined' || !className) return;
  document.documentElement.classList.remove(className);
}

/**
 * Get system color scheme preference
 */
function getSystemPreference(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * Load theme configuration from localStorage
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
 * Save theme configuration to localStorage
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
 * Props for the ThemeProvider component
 */
interface ThemeProviderProps {
  /** Child components that will have access to theme context */
  children: ReactNode;
  /** Initial theme configuration to use before localStorage is checked */
  initialTheme?: Partial<ThemeConfig>;
  /** localStorage key for persisting theme preferences */
  storageKey?: string;
  /** Whether to apply default CLAUDE_COLORS as base theme */
  useClaudeColors?: boolean;
}

/**
 * ThemeProvider component that manages theme state and provides context.
 *
 * This provider:
 * 1. Initializes theme from localStorage or initialTheme prop
 * 2. Applies CSS variables on theme change
 * 3. Adds/removes 'dark' class on document root
 * 4. Persists theme preferences to localStorage
 * 5. Listens to system preference changes
 *
 * @example
 * ```tsx
 * // In your layout or app wrapper
 * <ThemeProvider initialTheme={{ mode: 'system' }}>
 *   <App />
 * </ThemeProvider>
 *
 * // In child components
 * const { isDark, toggleMode } = useThemeContext();
 * ```
 */
export function ThemeProvider({
  children,
  initialTheme,
  storageKey = 'claude-chat-theme',
  useClaudeColors = true,
}: ThemeProviderProps) {
  // Track system preference for dark mode
  const [systemIsDark, setSystemIsDark] = useState<boolean>(() => {
    // Check system preference on initial render (client-side only)
    if (typeof window !== 'undefined') {
      return getSystemPreference();
    }
    return false;
  });

  // Track if we're mounted (for SSR hydration)
  const [mounted, setMounted] = useState(false);

  // Initialize theme state
  const [theme, setThemeState] = useState<ThemeConfig>(() => {
    return { ...DEFAULT_THEME_CONFIG, ...initialTheme };
  });

  // Track previous custom class name for cleanup
  const [prevCustomClass, setPrevCustomClass] = useState<string | undefined>();

  // Load theme from localStorage after mount (to avoid SSR mismatch)
  useEffect(() => {
    setMounted(true);
    const storedTheme = loadThemeFromStorage(storageKey);
    if (storedTheme) {
      setThemeState((prev) => ({ ...prev, ...storedTheme }));
    }
    // Also update system preference now that we're on the client
    setSystemIsDark(getSystemPreference());
  }, [storageKey]);

  // Calculate derived values
  const isDark = isThemeDark(theme, systemIsDark);
  const colors = resolveThemeColors(theme, systemIsDark);

  // Apply CSS variables and dark class whenever theme changes
  useEffect(() => {
    if (!mounted) return;

    // Apply CSS variables
    applyCSSVariables(colors);
    applyThemeSettings(theme);

    // Clean up previous custom class
    if (prevCustomClass && prevCustomClass !== theme.customClassName) {
      removeCustomClassName(prevCustomClass);
    }
    setPrevCustomClass(theme.customClassName);

    // Toggle dark class on document root
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', isDark);
    }
  }, [colors, theme, isDark, mounted, prevCustomClass]);

  // Listen for system preference changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (event: MediaQueryListEvent) => {
      setSystemIsDark(event.matches);
    };

    // Modern browsers use addEventListener
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
    if (!mounted) return;
    saveThemeToStorage(storageKey, theme);
  }, [theme, storageKey, mounted]);

  // Theme setter with support for function updates
  const setTheme = useCallback(
    (newTheme: ThemeConfig | ((prev: ThemeConfig) => ThemeConfig)) => {
      setThemeState((prev) => {
        const updated = typeof newTheme === 'function' ? newTheme(prev) : newTheme;
        return updated;
      });
    },
    []
  );

  // Toggle between light and dark modes
  const toggleMode = useCallback(() => {
    setThemeState((prev) => {
      // If currently in system mode, switch to explicit mode opposite of current
      if (prev.mode === 'system') {
        return { ...prev, mode: systemIsDark ? 'light' : 'dark' };
      }
      // Otherwise toggle between light and dark
      return { ...prev, mode: prev.mode === 'dark' ? 'light' : 'dark' };
    });
  }, [systemIsDark]);

  // Set a specific theme mode
  const setMode = useCallback((mode: ThemeMode) => {
    setThemeState((prev) => ({ ...prev, mode }));
  }, []);

  // Context value
  const contextValue: ThemeContextValue = {
    theme,
    setTheme,
    toggleMode,
    isDark,
    colors,
    setMode,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Hook to access theme context values.
 *
 * Must be used within a ThemeProvider.
 *
 * @throws Error if used outside of ThemeProvider
 * @returns Theme context value with state and actions
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { theme, isDark, toggleMode, setMode, colors } = useThemeContext();
 *
 *   return (
 *     <div style={{ backgroundColor: colors['--background'] }}>
 *       <button onClick={toggleMode}>
 *         {isDark ? 'Switch to Light' : 'Switch to Dark'}
 *       </button>
 *       <button onClick={() => setMode('system')}>
 *         Use System Theme
 *       </button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useThemeContext(): ThemeContextValue {
  const context = useContext(ThemeContext);

  if (context === undefined) {
    throw new Error('useThemeContext must be used within a ThemeProvider');
  }

  return context;
}

export default ThemeProvider;
