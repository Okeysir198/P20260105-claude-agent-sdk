/**
 * Theme Configuration Types for Claude Chat UI
 *
 * These types define the theme system including colors, configuration,
 * and context values for managing light/dark mode and custom styling.
 *
 * @module types/theme
 */

/**
 * Complete set of CSS custom property colors for the Claude theme.
 * These map directly to CSS variables used throughout the UI.
 */
export interface ClaudeThemeColors {
  // ============================================
  // Background Colors
  // ============================================

  /** Primary background color for the main content area */
  '--background': string;
  /** Secondary/muted background for cards and containers */
  '--background-secondary': string;
  /** Tertiary background for nested elements */
  '--background-tertiary': string;

  // ============================================
  // Foreground/Text Colors
  // ============================================

  /** Primary text color */
  '--foreground': string;
  /** Secondary/muted text color */
  '--foreground-secondary': string;
  /** Tertiary/subtle text color */
  '--foreground-tertiary': string;

  // ============================================
  // Brand Colors
  // ============================================

  /** Primary brand color (Claude's signature color) */
  '--primary': string;
  /** Text color on primary backgrounds */
  '--primary-foreground': string;
  /** Hover state for primary color */
  '--primary-hover': string;
  /** Active/pressed state for primary color */
  '--primary-active': string;

  // ============================================
  // Accent Colors
  // ============================================

  /** Accent color for highlights and emphasis */
  '--accent': string;
  /** Text color on accent backgrounds */
  '--accent-foreground': string;

  // ============================================
  // Semantic Colors
  // ============================================

  /** Success state color */
  '--success': string;
  /** Text on success backgrounds */
  '--success-foreground': string;

  /** Warning state color */
  '--warning': string;
  /** Text on warning backgrounds */
  '--warning-foreground': string;

  /** Error/destructive state color */
  '--error': string;
  /** Text on error backgrounds */
  '--error-foreground': string;

  /** Info state color */
  '--info': string;
  /** Text on info backgrounds */
  '--info-foreground': string;

  // ============================================
  // UI Element Colors
  // ============================================

  /** Border color for general elements */
  '--border': string;
  /** Subtle border color for dividers */
  '--border-subtle': string;

  /** Ring/focus color for accessibility */
  '--ring': string;

  /** Input field background */
  '--input': string;
  /** Input field border */
  '--input-border': string;
  /** Input field focus border */
  '--input-focus': string;

  // ============================================
  // Message Bubble Colors
  // ============================================

  /** User message bubble background */
  '--user-bubble': string;
  /** User message bubble text */
  '--user-bubble-foreground': string;

  /** Assistant message bubble background */
  '--assistant-bubble': string;
  /** Assistant message bubble text */
  '--assistant-bubble-foreground': string;

  /** Tool use indicator background */
  '--tool-bubble': string;
  /** Tool use indicator text */
  '--tool-bubble-foreground': string;

  // ============================================
  // Code/Syntax Colors
  // ============================================

  /** Code block background */
  '--code-background': string;
  /** Code text color */
  '--code-foreground': string;
  /** Code border */
  '--code-border': string;

  // ============================================
  // Scrollbar Colors
  // ============================================

  /** Scrollbar track background */
  '--scrollbar-track': string;
  /** Scrollbar thumb color */
  '--scrollbar-thumb': string;
  /** Scrollbar thumb hover state */
  '--scrollbar-thumb-hover': string;

  // ============================================
  // Shadow Colors
  // ============================================

  /** Small shadow (e.g., buttons) */
  '--shadow-sm': string;
  /** Medium shadow (e.g., cards) */
  '--shadow-md': string;
  /** Large shadow (e.g., modals) */
  '--shadow-lg': string;
}

/**
 * Theme mode options.
 */
export type ThemeMode = 'light' | 'dark' | 'system';

/**
 * Border radius presets for the theme.
 */
export type BorderRadiusPreset = 'none' | 'sm' | 'md' | 'lg' | 'full';

/**
 * Font family presets.
 */
export type FontFamilyPreset = 'system' | 'inter' | 'roboto' | 'custom';

/**
 * Complete theme configuration object.
 */
export interface ThemeConfig {
  /** Current theme mode */
  mode: ThemeMode;
  /** Custom color overrides (partial) */
  colors?: Partial<ClaudeThemeColors>;
  /** Font family configuration */
  fontFamily?: FontFamilyPreset | string;
  /** Border radius configuration */
  borderRadius?: BorderRadiusPreset | string;
  /** Whether to use system preference for color scheme */
  useSystemPreference?: boolean;
  /** Custom CSS class to apply to the root element */
  customClassName?: string;
}

/**
 * Theme context value for React context.
 * Provides access to theme state and actions.
 */
export interface ThemeContextValue {
  /** Current theme configuration */
  theme: ThemeConfig;
  /** Function to update the theme configuration */
  setTheme: (theme: ThemeConfig | ((prev: ThemeConfig) => ThemeConfig)) => void;
  /** Toggle between light and dark modes */
  toggleMode: () => void;
  /** Whether the current theme is dark mode */
  isDark: boolean;
  /** Resolved colors (with defaults applied) */
  colors: ClaudeThemeColors;
  /** Set a specific theme mode */
  setMode: (mode: ThemeMode) => void;
}

/**
 * Default light theme colors for Claude Chat UI.
 */
export const LIGHT_THEME_COLORS: ClaudeThemeColors = {
  '--background': '#ffffff',
  '--background-secondary': '#f9fafb',
  '--background-tertiary': '#f3f4f6',

  '--foreground': '#111827',
  '--foreground-secondary': '#4b5563',
  '--foreground-tertiary': '#9ca3af',

  '--primary': '#d97706',
  '--primary-foreground': '#ffffff',
  '--primary-hover': '#b45309',
  '--primary-active': '#92400e',

  '--accent': '#f59e0b',
  '--accent-foreground': '#ffffff',

  '--success': '#10b981',
  '--success-foreground': '#ffffff',

  '--warning': '#f59e0b',
  '--warning-foreground': '#1f2937',

  '--error': '#ef4444',
  '--error-foreground': '#ffffff',

  '--info': '#3b82f6',
  '--info-foreground': '#ffffff',

  '--border': '#e5e7eb',
  '--border-subtle': '#f3f4f6',

  '--ring': '#d97706',

  '--input': '#ffffff',
  '--input-border': '#d1d5db',
  '--input-focus': '#d97706',

  '--user-bubble': '#d97706',
  '--user-bubble-foreground': '#ffffff',

  '--assistant-bubble': '#f3f4f6',
  '--assistant-bubble-foreground': '#111827',

  '--tool-bubble': '#fef3c7',
  '--tool-bubble-foreground': '#92400e',

  '--code-background': '#1f2937',
  '--code-foreground': '#e5e7eb',
  '--code-border': '#374151',

  '--scrollbar-track': '#f3f4f6',
  '--scrollbar-thumb': '#d1d5db',
  '--scrollbar-thumb-hover': '#9ca3af',

  '--shadow-sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  '--shadow-md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  '--shadow-lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
};

/**
 * Default dark theme colors for Claude Chat UI.
 */
export const DARK_THEME_COLORS: ClaudeThemeColors = {
  '--background': '#111827',
  '--background-secondary': '#1f2937',
  '--background-tertiary': '#374151',

  '--foreground': '#f9fafb',
  '--foreground-secondary': '#d1d5db',
  '--foreground-tertiary': '#9ca3af',

  '--primary': '#f59e0b',
  '--primary-foreground': '#1f2937',
  '--primary-hover': '#fbbf24',
  '--primary-active': '#d97706',

  '--accent': '#fbbf24',
  '--accent-foreground': '#1f2937',

  '--success': '#34d399',
  '--success-foreground': '#1f2937',

  '--warning': '#fbbf24',
  '--warning-foreground': '#1f2937',

  '--error': '#f87171',
  '--error-foreground': '#1f2937',

  '--info': '#60a5fa',
  '--info-foreground': '#1f2937',

  '--border': '#374151',
  '--border-subtle': '#4b5563',

  '--ring': '#f59e0b',

  '--input': '#1f2937',
  '--input-border': '#4b5563',
  '--input-focus': '#f59e0b',

  '--user-bubble': '#f59e0b',
  '--user-bubble-foreground': '#1f2937',

  '--assistant-bubble': '#374151',
  '--assistant-bubble-foreground': '#f9fafb',

  '--tool-bubble': '#78350f',
  '--tool-bubble-foreground': '#fef3c7',

  '--code-background': '#0d1117',
  '--code-foreground': '#e6edf3',
  '--code-border': '#30363d',

  '--scrollbar-track': '#1f2937',
  '--scrollbar-thumb': '#4b5563',
  '--scrollbar-thumb-hover': '#6b7280',

  '--shadow-sm': '0 1px 2px 0 rgb(0 0 0 / 0.3)',
  '--shadow-md': '0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3)',
  '--shadow-lg': '0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.3)',
};

/**
 * Default theme configuration.
 */
export const DEFAULT_THEME_CONFIG: ThemeConfig = {
  mode: 'system',
  useSystemPreference: true,
  borderRadius: 'md',
  fontFamily: 'system',
};

/**
 * Border radius values for presets.
 */
export const BORDER_RADIUS_VALUES: Record<BorderRadiusPreset, string> = {
  none: '0',
  sm: '0.25rem',
  md: '0.5rem',
  lg: '1rem',
  full: '9999px',
};

/**
 * Font family values for presets.
 */
export const FONT_FAMILY_VALUES: Record<FontFamilyPreset, string> = {
  system: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  inter: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  roboto: '"Roboto", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  custom: 'inherit',
};

/**
 * Helper function to get the resolved colors based on theme mode.
 *
 * @param config - Theme configuration
 * @param systemIsDark - Whether the system preference is dark mode
 * @returns Resolved theme colors
 */
export function resolveThemeColors(
  config: ThemeConfig,
  systemIsDark: boolean
): ClaudeThemeColors {
  const isDark = config.mode === 'dark' || (config.mode === 'system' && systemIsDark);
  const baseColors = isDark ? DARK_THEME_COLORS : LIGHT_THEME_COLORS;

  return {
    ...baseColors,
    ...config.colors,
  };
}

/**
 * Helper function to determine if current theme is dark.
 *
 * @param config - Theme configuration
 * @param systemIsDark - Whether the system preference is dark mode
 * @returns True if the resolved theme is dark
 */
export function isThemeDark(config: ThemeConfig, systemIsDark: boolean): boolean {
  return config.mode === 'dark' || (config.mode === 'system' && systemIsDark);
}
