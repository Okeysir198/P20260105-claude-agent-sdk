import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  safelist: [
    // Status colors - ensure all variants are generated
    'bg-status-success', 'bg-status-success-fg', 'bg-status-success-bg',
    'text-status-success', 'text-status-success-fg', 'text-status-success-bg',
    'border-status-success',
    'bg-status-warning', 'bg-status-warning-fg', 'bg-status-warning-bg',
    'text-status-warning', 'text-status-warning-fg', 'text-status-warning-bg',
    'border-status-warning',
    'bg-status-error', 'bg-status-error-fg', 'bg-status-error-bg',
    'text-status-error', 'text-status-error-fg', 'text-status-error-bg',
    'border-status-error',
    'bg-status-info', 'bg-status-info-fg', 'bg-status-info-bg',
    'text-status-info', 'text-status-info-fg', 'text-status-info-bg',
    'border-status-info',
    // Codeblock colors
    'bg-codeblock-bg', 'bg-codeblock-header', 'bg-codeblock-border',
    'text-codeblock-text', 'text-codeblock-muted',
    'border-codeblock-border',
    // Diff colors
    'bg-diff-added-bg', 'bg-diff-removed-bg',
    'text-diff-added-fg', 'text-diff-removed-fg',
  ],
  theme: {
    extend: {
      screens: {
        xs: '375px',
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
          hover: "hsl(var(--primary-hover))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        status: {
          success: {
            DEFAULT: "hsl(var(--status-success))",
            fg: "hsl(var(--status-success-fg))",
            bg: "hsl(var(--status-success-bg) / 0.1)",
          },
          warning: {
            DEFAULT: "hsl(var(--status-warning))",
            fg: "hsl(var(--status-warning-fg))",
            bg: "hsl(var(--status-warning-bg) / 0.1)",
          },
          error: {
            DEFAULT: "hsl(var(--status-error))",
            fg: "hsl(var(--status-error-fg))",
            bg: "hsl(var(--status-error-bg) / 0.1)",
          },
          info: {
            DEFAULT: "hsl(var(--status-info))",
            fg: "hsl(var(--status-info-fg))",
            bg: "hsl(var(--status-info-bg) / 0.1)",
          },
        },
        codeblock: {
          bg: "hsl(var(--codeblock-bg))",
          header: "hsl(var(--codeblock-header))",
          text: "hsl(var(--codeblock-text))",
          muted: "hsl(var(--codeblock-muted))",
          border: "hsl(var(--codeblock-border))",
        },
        diff: {
          added: {
            bg: "hsl(var(--diff-added-bg) / 0.1)",
            fg: "hsl(var(--diff-added-fg))",
          },
          removed: {
            bg: "hsl(var(--diff-removed-bg) / 0.1)",
            fg: "hsl(var(--diff-removed-fg))",
          },
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        waveform: {
          '0%': { height: '20%' },
          '100%': { height: '80%' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
