import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: ['class'],
  theme: {
    extend: {
      colors: {
        // Claude.ai-inspired RGB color system
        background: 'rgb(var(--background) / <alpha-value>)',
        foreground: 'rgb(var(--foreground) / <alpha-value>)',
        primary: {
          DEFAULT: 'rgb(var(--primary) / <alpha-value>)',
          foreground: 'rgb(var(--primary-foreground) / <alpha-value>)',
        },
        secondary: {
          DEFAULT: 'rgb(var(--secondary) / <alpha-value>)',
          foreground: 'rgb(var(--secondary-foreground) / <alpha-value>)',
        },
        muted: {
          DEFAULT: 'rgb(var(--muted) / <alpha-value>)',
          foreground: 'rgb(var(--muted-foreground) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'rgb(var(--accent) / <alpha-value>)',
          foreground: 'rgb(var(--accent-foreground) / <alpha-value>)',
        },
        border: 'rgb(var(--border) / <alpha-value>)',
        input: 'rgb(var(--input) / <alpha-value>)',
        ring: 'rgb(var(--ring) / <alpha-value>)',
        card: {
          DEFAULT: 'rgb(var(--card) / <alpha-value>)',
          foreground: 'rgb(var(--card-foreground) / <alpha-value>)',
        },
        destructive: {
          DEFAULT: 'rgb(var(--destructive) / <alpha-value>)',
          foreground: 'rgb(var(--destructive-foreground) / <alpha-value>)',
        },
        // Legacy Claude brand colors (for gradient/shadow references)
        claude: {
          orange: {
            '50': '#fef7f4',
            '100': '#fdede6',
            '200': '#fbd9cc',
            '300': '#f7b8a3',
            '400': '#f18f6f',
            '500': '#d97757',
            '600': '#c56a4a',
            '700': '#a5573c',
            '800': '#884a35',
            '900': '#6e3e2e',
            '950': '#3b1f16'
          },
          sand: {
            '50': '#FDFCFB',
            '100': '#F9F7F4',
            '200': '#F3EFE9',
            '300': '#E8E2D9',
            '400': '#D4CBC0',
            '500': '#B8AC9E',
            '600': '#958777',
            '700': '#756859',
            '800': '#5C5047',
            '900': '#413A33',
            '950': '#2A2520'
          }
        },
        // Semantic state colors
        success: {
          '50': '#F0FDF4',
          '100': '#DCFCE7',
          '500': '#22C55E',
          '600': '#16A34A',
          '700': '#15803D'
        },
        warning: {
          '50': '#FFFBEB',
          '100': '#FEF3C7',
          '500': '#F59E0B',
          '600': '#D97706',
          '700': '#B45309'
        },
        error: {
          '50': '#FEF2F2',
          '100': '#FEE2E2',
          '500': '#EF4444',
          '600': '#DC2626',
          '700': '#B91C1C'
        },
        info: {
          '50': '#EFF6FF',
          '100': '#DBEAFE',
          '500': '#3B82F6',
          '600': '#2563EB',
          '700': '#1D4ED8'
        },
      },
      fontFamily: {
        sans: [
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif',
        ],
        mono: [
          '"SF Mono"',
          'Monaco',
          '"Cascadia Code"',
          '"Roboto Mono"',
          'Consolas',
          '"Courier New"',
          'monospace',
        ],
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.875rem', { lineHeight: '1.25rem' }],
        base: ['1rem', { lineHeight: '1.5rem' }],
        lg: ['1.125rem', { lineHeight: '1.75rem' }],
        xl: ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }]
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem'
      },
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      boxShadow: {
        soft: '0 2px 8px -2px rgba(0, 0, 0, 0.1)',
        medium: '0 4px 16px -4px rgba(0, 0, 0, 0.15)',
        strong: '0 8px 32px -8px rgba(0, 0, 0, 0.2)',
        'inner-soft': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.05)',
        glow: '0 0 20px -5px rgba(249, 115, 22, 0.3)',
        'glow-lg': '0 0 40px -10px rgba(249, 115, 22, 0.4)'
      },
      backdropBlur: {
        xs: '2px'
      },
      transitionDuration: {
        '250': '250ms',
        '350': '350ms',
        '400': '400ms'
      },
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100'
      }
    }
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
