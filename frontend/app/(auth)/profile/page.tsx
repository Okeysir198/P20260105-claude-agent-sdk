'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ConnectGmailButton, ConnectYahooButton, EmailStatusBadge } from '@/components/email';
import { Suspense } from 'react';

interface EmailStatus {
  gmail_connected: boolean;
  yahoo_connected: boolean;
  gmail_email?: string;
  yahoo_email?: string;
}

function ProfileContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [emailStatus, setEmailStatus] = useState<EmailStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [disconnectError, setDisconnectError] = useState<string | null>(null);

  const fetchEmailStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/proxy/email/status');
      if (response.ok) {
        const data = await response.json();
        setEmailStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch email status:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Check for OAuth callback status
  useEffect(() => {
    const email = searchParams.get('email');
    const status = searchParams.get('status');

    if (email === 'gmail' && status === 'connected') {
      router.replace('/profile');
      fetchEmailStatus();
    }
  }, [searchParams, router, fetchEmailStatus]);

  useEffect(() => {
    fetchEmailStatus();
  }, [fetchEmailStatus]);

  const handleDisconnect = async (provider: 'gmail' | 'yahoo') => {
    setDisconnectError(null);
    try {
      const response = await fetch(`/api/proxy/email/${provider}/disconnect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      });

      if (!response.ok) {
        throw new Error(`Failed to disconnect ${provider}`);
      }

      fetchEmailStatus();
    } catch (error) {
      const message = error instanceof Error ? error.message : `Failed to disconnect ${provider}`;
      setDisconnectError(message);
      console.error(`Failed to disconnect ${provider}:`, error);
    }
  };

  return (
    <div className="max-w-2xl w-full mx-auto px-4 py-8">
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Email Integration
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Connect your email accounts to enable the AI agent to read your emails and
            download attachments.
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* Status Section */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Connected Accounts
            </h2>
            {disconnectError && (
              <p className="mb-3 text-sm text-red-600 dark:text-red-400">{disconnectError}</p>
            )}
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
              </div>
            ) : (
              <div className="space-y-3">
                <EmailStatusBadge
                  provider="gmail"
                  connected={emailStatus?.gmail_connected || false}
                  email={emailStatus?.gmail_email}
                  onDisconnect={() => handleDisconnect('gmail')}
                />
                <EmailStatusBadge
                  provider="yahoo"
                  connected={emailStatus?.yahoo_connected || false}
                  email={emailStatus?.yahoo_email}
                  onDisconnect={() => handleDisconnect('yahoo')}
                />
              </div>
            )}
          </div>

          {/* Connect Section */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Connect New Account
            </h2>
            <div className="flex flex-wrap gap-4">
              <ConnectGmailButton onConnected={fetchEmailStatus} />
              <ConnectYahooButton onConnected={fetchEmailStatus} />
            </div>
          </div>

          {/* Info Section */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              How it works
            </h2>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>
                  Connect your email account with a one-time OAuth authentication flow
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>
                  The AI agent can list emails, read full content, and download attachments
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>
                  Downloaded attachments are stored in your session workspace
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>
                  Your credentials are stored securely per-user
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Back to chat button */}
      <div className="mt-6 text-center">
        <button
          onClick={() => router.push('/')}
          className="text-primary hover:text-primary/80 transition-colors"
        >
          ← Back to chat
        </button>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      }
    >
      <ProfileContent />
    </Suspense>
  );
}
