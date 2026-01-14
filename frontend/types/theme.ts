/**
 * Theme Configuration Types for Claude Chat UI
 * @module types/theme
 */

/**
 * CSS custom property colors for the Claude theme.
 * Maps directly to CSS variables used throughout the UI.
 */
export interface ClaudeThemeColors {
  // Background Colors
  '--background': string;
  '--background-secondary': string;
  '--background-tertiary': string;

  // Foreground/Text Colors
  '--foreground': string;
  '--foreground-secondary': string;
  '--foreground-tertiary': string;

  // Brand Colors
  '--primary': string;
  '--primary-foreground': string;
  '--primary-hover': string;
  '--primary-active': string;

  // Accent Colors
  '--accent': string;
  '--accent-foreground': string;

  // Semantic Colors
  '--success': string;
  '--success-foreground': string;
  '--warning': string;
  '--warning-foreground': string;
  '--error': string;
  '--error-foreground': string;
  '--info': string;
  '--info-foreground': string;

  // UI Element Colors
  '--border': string;
  '--border-subtle': string;
  '--ring': string;
  '--input': string;
  '--input-border': string;
  '--input-focus': string;

  // Message Bubble Colors
  '--user-bubble': string;
  '--user-bubble-foreground': string;
  '--assistant-bubble': string;
  '--assistant-bubble-foreground': string;
  '--tool-bubble': string;
  '--tool-bubble-foreground': string;

  // Code/Syntax Colors
  '--code-background': string;
  '--code-foreground': string;
  '--code-border': string;

  // Scrollbar Colors
  '--scrollbar-track': string;
  '--scrollbar-thumb': string;
  '--scrollbar-thumb-hover': string;

  // Shadow Colors
  '--shadow-sm': string;
  '--shadow-md': string;
  '--shadow-lg': string;
}

export type ThemeMode = 'light' | 'dark' | 'system';
export type BorderRadiusPreset = 'none' | 'sm' | 'md' | 'lg' | 'full';
export type FontFamilyPreset = 'system' | 'inter' | 'roboto' | 'custom';

export interface ThemeConfig {
  mode: ThemeMode;
  colors?: Partial<ClaudeThemeColors>;
  fontFamily?: FontFamilyPreset | string;
  borderRadius?: BorderRadiusPreset | string;
  useSystemPreference?: boolean;
  customClassName?: string;
}

export interface ThemeContextValue {
  theme: ThemeConfig;
  setTheme: (theme: ThemeConfig | ((prev: ThemeConfig) => ThemeConfig)) => void;
  toggleMode: () => void;
  isDark: boolean;
  colors: ClaudeThemeColors;
  setMode: (mode: ThemeMode) => void;
}

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

export const DEFAULT_THEME_CONFIG: ThemeConfig = {
  mode: 'system',
  useSystemPreference: true,
  borderRadius: 'md',
  fontFamily: 'system',
};

export const BORDER_RADIUS_VALUES: Record<BorderRadiusPreset, string> = {
  none: '0',
  sm: '0.25rem',
  md: '0.5rem',
  lg: '1rem',
  full: '9999px',
};

export const FONT_FAMILY_VALUES: Record<FontFamilyPreset, string> = {
  system: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  inter: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  roboto: '"Roboto", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  custom: 'inherit',
};

export function resolveThemeColors(
  config: ThemeConfig,
  systemIsDark: boolean
): ClaudeThemeColors {
  const isDark = config.mode === 'dark' || (config.mode === 'system' && systemIsDark);
  const baseColors = isDark ? DARK_THEME_COLORS : LIGHT_THEME_COLORS;
  return { ...baseColors, ...config.colors };
}

export function isThemeDark(config: ThemeConfig, systemIsDark: boolean): boolean {
  return config.mode === 'dark' || (config.mode === 'system' && systemIsDark);
}
