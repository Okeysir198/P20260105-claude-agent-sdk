import type { Metadata } from 'next';
import { ThemeProvider } from '@/components/providers/theme-provider';
import { SkipLink } from '@/components/ui/skip-link';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'Claude Chat',
  description: 'Chat with Claude Agent SDK',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 5,
    userScalable: true,
  },
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F4F3EE' },
    { media: '(prefers-color-scheme: dark)', color: '#141413' },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <SkipLink targetId="main-content">Skip to main content</SkipLink>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
