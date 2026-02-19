'use client';

import { useState } from 'react';
import { Eye, Shield } from 'lucide-react';

interface ConnectGmailButtonProps {
  onConnected?: () => void;
}

export function ConnectGmailButton({ onConnected }: ConnectGmailButtonProps) {
  const [isLoading, setIsLoading] = useState<'read_only' | 'full_access' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async (accessLevel: 'read_only' | 'full_access') => {
    setIsLoading(accessLevel);
    setError(null);

    try {
      const response = await fetch(`/api/proxy/email/gmail/auth-url?access_level=${accessLevel}`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error('Failed to get Gmail authorization URL');
      }

      const data = await response.json();
      window.location.href = data.auth_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect Gmail');
      setIsLoading(null);
    }
  };

  const gmailIcon = (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
      <path
        d="M22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6zm-2 0l-8 5-8-5h16zm0 12H4V8l8 5 8-5v10z"
        fill="currentColor"
      />
    </svg>
  );

  return (
    <div className="space-y-2">
      <div className="flex flex-col sm:flex-row gap-2 w-full">
        <button
          onClick={() => handleConnect('read_only')}
          disabled={isLoading !== null}
          className="inline-flex items-center gap-2 px-3 sm:px-4 py-2.5 sm:py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-md border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-1 sm:flex-initial min-w-0"
        >
          {gmailIcon}
          <Eye className="w-4 h-4 text-gray-500 shrink-0" />
          <div className="text-left min-w-0">
            <div className="text-sm font-medium truncate">
              {isLoading === 'read_only' ? 'Connecting...' : 'Read Only'}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
              List, read, search emails
            </div>
          </div>
        </button>
        <button
          onClick={() => handleConnect('full_access')}
          disabled={isLoading !== null}
          className="inline-flex items-center gap-2 px-3 sm:px-4 py-2.5 sm:py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-md border border-amber-300 dark:border-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-1 sm:flex-initial min-w-0"
        >
          {gmailIcon}
          <Shield className="w-4 h-4 text-amber-500 shrink-0" />
          <div className="text-left min-w-0">
            <div className="text-sm font-medium truncate">
              {isLoading === 'full_access' ? 'Connecting...' : 'Full Access'}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
              Send, reply, modify + read
            </div>
          </div>
        </button>
      </div>
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
