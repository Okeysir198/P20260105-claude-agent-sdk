'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ConnectGmailButton, ConnectImapButton, EmailStatusBadge } from '@/components/email';
import { Suspense } from 'react';
import { EmailAccount, EmailStatus } from '@/types/api';

function ProfileContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [emailStatus, setEmailStatus] = useState<EmailStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [disconnectError, setDisconnectError] = useState<string | null>(null);
  const [oauthError, setOauthError] = useState<string | null>(null);
  const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);

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
    const error = searchParams.get('error');

    if (error) {
      const errorMessages: Record<string, string> = {
        'access_denied': 'Access was denied. Please try connecting again.',
        'invalid_state': 'Session expired. Please try connecting again.',
        'token_error': 'Failed to authenticate with Gmail. Please try again.',
        'no_email': 'Could not retrieve your email address from Gmail.',
        'callback_forward_failed': 'OAuth callback failed. Please try connecting again.',
        'backend_callback_failed': 'Backend authentication failed. Please try again.',
        'missing_oauth_params': 'Missing OAuth parameters. Please try connecting again.',
        'missing_backend_config': 'Backend configuration error. Please contact an administrator.',
        'gmail_oauth_error': 'Gmail authorization failed. Please try again.',
      };
      setOauthError(errorMessages[error] || `Connection failed: ${error}`);
      router.replace('/profile');
      return;
    }

    if (email?.startsWith('gmail') && status === 'connected') {
      router.replace('/profile');
      fetchEmailStatus();
    }
  }, [searchParams, router, fetchEmailStatus]);

  useEffect(() => {
    fetchEmailStatus();
  }, [fetchEmailStatus]);

  const handleDisconnect = async (provider: string) => {
    setDisconnectError(null);
    setDisconnectingProvider(provider);
    try {
      let url: string;
      let body: Record<string, string>;

      // Find the account to determine auth_type for proper disconnect routing
      const account = accounts.find(a => a.provider === provider);
      if (account && account.provider.startsWith('gmail') && account.auth_type === 'oauth') {
        url = '/api/proxy/email/gmail/disconnect';
        body = { provider };
      } else {
        url = '/api/proxy/email/imap/disconnect';
        body = { provider };
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`Failed to disconnect ${provider}`);
      }

      fetchEmailStatus();
    } catch (error) {
      const message = error instanceof Error ? error.message : `Failed to disconnect ${provider}`;
      setDisconnectError(message);
      console.error(`Failed to disconnect ${provider}:`, error);
    } finally {
      setDisconnectingProvider(null);
    }
  };

  const accounts = emailStatus?.accounts || [];

  return (
    <div className="max-w-2xl w-full mx-auto px-3 sm:px-4 py-2 sm:py-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            Email Integration
          </h1>
          <p className="mt-1.5 sm:mt-2 text-sm sm:text-base text-gray-600 dark:text-gray-400">
            Connect your email accounts to enable the AI agent to read your emails and
            download attachments.
          </p>
        </div>

        <div className="p-4 sm:p-6 space-y-6">
          {/* Status Section */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Connected Accounts
            </h2>
            {disconnectError && (
              <p className="mb-3 text-sm text-red-600 dark:text-red-400">{disconnectError}</p>
            )}
            {oauthError && (
              <div className="mb-3 flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                <p className="text-sm text-red-600 dark:text-red-400">{oauthError}</p>
                <button
                  onClick={() => setOauthError(null)}
                  className="ml-3 text-red-400 hover:text-red-600 dark:hover:text-red-300"
                >
                  ✕
                </button>
              </div>
            )}
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
              </div>
            ) : accounts.length > 0 ? (
              <div className="space-y-3">
                {accounts.map((account) => (
                  <EmailStatusBadge
                    key={`${account.provider}-${account.email}`}
                    provider={account.provider}
                    connected={true}
                    email={account.email}
                    accessLevel={account.access_level}
                    authType={account.auth_type}
                    onDisconnect={() => handleDisconnect(account.provider)}
                    isDisconnecting={disconnectingProvider === account.provider}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
                No email accounts connected yet. Connect one below to get started.
              </p>
            )}
          </div>

          {/* Connect Section */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Connect New Account
            </h2>
            <div className="flex flex-col gap-2">
              <ConnectGmailButton onConnected={fetchEmailStatus} />
              <ConnectImapButton onConnected={fetchEmailStatus} />
            </div>
          </div>

          {/* Info Section */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              How it works
            </h2>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <li className="flex gap-2">
                <span className="text-primary">&#8226;</span>
                <span>
                  Connect Gmail with OAuth or other providers (Yahoo, Outlook, iCloud, Zoho)
                  via IMAP with an app password
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">&#8226;</span>
                <span>
                  The AI agent can list emails, read full content, and download attachments
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">&#8226;</span>
                <span>
                  Downloaded attachments are stored in your session workspace
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">&#8226;</span>
                <span>
                  Your credentials are stored securely per-user and you can connect
                  multiple providers
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">&#8226;</span>
                <span>
                  Custom IMAP servers are supported for any email provider
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
          &larr; Back to chat
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
