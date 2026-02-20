'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ConnectGmailButton, ConnectImapButton, EmailStatusBadge } from '@/components/email';
import { Suspense } from 'react';
import { EmailStatus } from '@/types/api';
import { Mail, Link2, Info, CheckCircle, AlertCircle, X, Loader2, RefreshCw } from 'lucide-react';

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="mb-3 flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
      <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
      <p className="text-sm text-red-600 dark:text-red-400 flex-1">{message}</p>
      <button
        onClick={onDismiss}
        className="text-red-400 hover:text-red-600 dark:hover:text-red-300"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

function EmailIntegrationContent() {
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
      router.replace('/email-integration');
      return;
    }

    if (email?.startsWith('gmail') && status === 'connected') {
      router.replace('/email-integration');
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
      const account = accounts.find(a => a.provider === provider);
      const isGmailOAuth = account?.provider.startsWith('gmail') && account?.auth_type === 'oauth';
      const url = isGmailOAuth
        ? '/api/proxy/email/gmail/disconnect'
        : '/api/proxy/email/imap/disconnect';

      const response = await fetch(url, {
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
    } finally {
      setDisconnectingProvider(null);
    }
  };

  const accounts = emailStatus?.accounts || [];

  return (
    <div className="max-w-2xl w-full mx-auto px-3 sm:px-4 py-2 sm:py-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
          <h1 className="flex items-center gap-3 text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Mail className="h-5 w-5 text-primary" />
            </div>
            Email Integration
          </h1>
          <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-400">
            Connect your email accounts to enable the AI agent to read your emails and download attachments.
          </p>
        </div>

        <div className="p-4 sm:p-6 space-y-6">
          {/* Status Section */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Connected Accounts
              </h2>
            </div>
            {disconnectError && (
              <ErrorBanner message={disconnectError} onDismiss={() => setDisconnectError(null)} />
            )}
            {oauthError && (
              <ErrorBanner message={oauthError} onDismiss={() => setOauthError(null)} />
            )}
            {isLoading ? (
              <div className="flex items-center justify-center py-8 gap-2 text-gray-500 dark:text-gray-400">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">Loading email accounts...</span>
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
              <div className="text-center py-8">
                <Mail className="h-12 w-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No email accounts connected yet. Connect one below to get started.
                </p>
              </div>
            )}
          </div>

          {/* Connect Section */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 mb-4">
              <Link2 className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Connect New Account
              </h2>
            </div>
            <div className="flex flex-col gap-2">
              <ConnectGmailButton onConnected={fetchEmailStatus} />
              <ConnectImapButton onConnected={fetchEmailStatus} />
            </div>
          </div>

          {/* Info Section */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 mb-3">
              <Info className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                How it works
              </h2>
            </div>
            <ul className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
              <li className="flex gap-3">
                <Mail className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span>
                  Connect Gmail with OAuth or other providers (Yahoo, Outlook, iCloud, Zoho) via IMAP with an app password
                </span>
              </li>
              <li className="flex gap-3">
                <RefreshCw className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span>
                  The AI agent can list emails, read full content, and download attachments
                </span>
              </li>
              <li className="flex gap-3">
                <CheckCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span>
                  Downloaded attachments are stored in your session workspace
                </span>
              </li>
              <li className="flex gap-3">
                <AlertCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span>
                  Your credentials are stored securely per-user and you can connect multiple providers
                </span>
              </li>
              <li className="flex gap-3">
                <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
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

export default function EmailIntegrationPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      }
    >
      <EmailIntegrationContent />
    </Suspense>
  );
}
