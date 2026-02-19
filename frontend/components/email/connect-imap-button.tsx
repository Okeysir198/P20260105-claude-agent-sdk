'use client';

import { useState, useMemo } from 'react';
import { Mail } from 'lucide-react';
import { DOMAIN_TO_PROVIDER, PROVIDER_NAMES, IMAP_PROVIDERS, detectProvider } from './email-constants';

interface ConnectImapButtonProps {
  onConnected?: () => void;
}

export function ConnectImapButton({ onConnected }: ConnectImapButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [appPassword, setAppPassword] = useState('');
  const [provider, setProvider] = useState('');
  const [imapServer, setImapServer] = useState('');
  const [imapPort, setImapPort] = useState('993');

  const detectedProvider = useMemo(() => detectProvider(email), [email]);
  const isGmailDetected = detectedProvider === 'gmail';

  // Auto-select provider when email changes
  const effectiveProvider = provider || (detectedProvider && detectedProvider !== 'gmail' ? detectedProvider : '');

  const handleEmailChange = (value: string) => {
    setEmail(value);
    const detected = detectProvider(value);
    if (detected && detected !== 'gmail') {
      setProvider(detected);
    } else if (detected === 'gmail') {
      setProvider('');
    }
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveProvider) return;

    setIsLoading(true);
    setError(null);

    try {
      const body: Record<string, string | number> = {
        email,
        app_password: appPassword,
        provider: effectiveProvider,
      };

      if (effectiveProvider === 'custom') {
        if (!imapServer) {
          throw new Error('IMAP server is required for custom provider');
        }
        body.imap_server = imapServer;
        body.imap_port = parseInt(imapPort, 10) || 993;
      }

      const response = await fetch('/api/proxy/email/imap/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.message || data.detail || 'Failed to connect email account');
      }

      handleClose();
      onConnected?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect email account');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setError(null);
    setEmail('');
    setAppPassword('');
    setProvider('');
    setImapServer('');
    setImapPort('993');
  };

  return (
    <div>
      <button
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center justify-center gap-2 px-4 py-2.5 sm:py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors w-full sm:w-auto"
      >
        <Mail className="w-5 h-5" />
        Connect Email (IMAP)
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 max-w-md w-full shadow-xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Connect Email via IMAP
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Connect your email account using IMAP with an app-specific password.
              Most providers require you to generate an app password in your account
              security settings.
            </p>
            <form onSubmit={handleConnect} className="space-y-4">
              {/* Email Input */}
              <div>
                <label
                  htmlFor="imap-email"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Email Address
                </label>
                <input
                  id="imap-email"
                  type="email"
                  value={email}
                  onChange={(e) => handleEmailChange(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="your-email@example.com"
                />
                {detectedProvider && !isGmailDetected && (
                  <p className="mt-1 text-xs text-green-600 dark:text-green-400">
                    Detected: {PROVIDER_NAMES[detectedProvider] || detectedProvider}
                  </p>
                )}
                {isGmailDetected && (
                  <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                    For richer features, use Gmail OAuth instead
                  </p>
                )}
              </div>

              {/* App Password */}
              <div>
                <label
                  htmlFor="imap-password"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  App Password
                </label>
                <input
                  id="imap-password"
                  type="password"
                  value={appPassword}
                  onChange={(e) => setAppPassword(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Your app-specific password"
                />
              </div>

              {/* Provider Dropdown */}
              <div>
                <label
                  htmlFor="imap-provider"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Email Provider
                </label>
                <select
                  id="imap-provider"
                  value={effectiveProvider}
                  onChange={(e) => setProvider(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Select provider...</option>
                  {IMAP_PROVIDERS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Custom IMAP Fields */}
              {effectiveProvider === 'custom' && (
                <div className="space-y-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-md">
                  <div>
                    <label
                      htmlFor="imap-server"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                      IMAP Server
                    </label>
                    <input
                      id="imap-server"
                      type="text"
                      value={imapServer}
                      onChange={(e) => setImapServer(e.target.value)}
                      required
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      placeholder="imap.example.com"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="imap-port"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                      IMAP Port
                    </label>
                    <input
                      id="imap-port"
                      type="number"
                      value={imapPort}
                      onChange={(e) => setImapPort(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      placeholder="993"
                    />
                  </div>
                </div>
              )}

              {error && (
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              )}

              <div className="flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading || !effectiveProvider}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {isLoading ? 'Connecting...' : 'Test & Connect'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
