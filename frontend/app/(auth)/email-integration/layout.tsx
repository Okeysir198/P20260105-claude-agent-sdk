import { Mail } from 'lucide-react';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '✉️ Email Integration - Claude Agent SDK',
  description: 'Connect your email accounts to enable the AI agent to read your emails and download attachments.',
};

export default function EmailIntegrationLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
