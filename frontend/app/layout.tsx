import type { Metadata } from 'next';
import { ThemeProvider } from '@/components/providers/theme-provider';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'Claude Chat',
  description: 'Chat with Claude Agent SDK',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
