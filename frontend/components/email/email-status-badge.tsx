'use client';

import { Check, X } from 'lucide-react';

const PROVIDER_NAMES: Record<string, string> = {
  gmail: 'Gmail',
  yahoo: 'Yahoo Mail',
  outlook: 'Outlook',
  icloud: 'iCloud',
  zoho: 'Zoho Mail',
  custom: 'Custom IMAP',
};

const PROVIDER_COLORS: Record<string, { bg: string; text: string }> = {
  gmail: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-600 dark:text-red-400',
  },
  yahoo: {
    bg: 'bg-purple-100 dark:bg-purple-900/30',
    text: 'text-purple-600 dark:text-purple-400',
  },
  outlook: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-600 dark:text-blue-400',
  },
  icloud: {
    bg: 'bg-sky-100 dark:bg-sky-900/30',
    text: 'text-sky-600 dark:text-sky-400',
  },
  zoho: {
    bg: 'bg-orange-100 dark:bg-orange-900/30',
    text: 'text-orange-600 dark:text-orange-400',
  },
  custom: {
    bg: 'bg-gray-100 dark:bg-gray-700',
    text: 'text-gray-600 dark:text-gray-400',
  },
};

const DEFAULT_COLORS = {
  bg: 'bg-green-100 dark:bg-green-900/30',
  text: 'text-green-600 dark:text-green-400',
};

interface EmailStatusBadgeProps {
  provider: string;
  connected: boolean;
  email?: string;
  onDisconnect?: () => void;
}

export function EmailStatusBadge({
  provider,
  connected,
  email,
  onDisconnect,
}: EmailStatusBadgeProps) {
  const displayName = PROVIDER_NAMES[provider] || provider;
  const colors = PROVIDER_COLORS[provider] || DEFAULT_COLORS;

  return (
    <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-3">
        <div
          className={`p-2 rounded-full ${
            connected
              ? colors.bg
              : 'bg-gray-100 dark:bg-gray-700'
          }`}
        >
          {connected ? (
            <Check className={`w-5 h-5 ${colors.text}`} />
          ) : (
            <X className="w-5 h-5 text-gray-400 dark:text-gray-500" />
          )}
        </div>
        <div>
          <p className="font-medium text-gray-900 dark:text-white">
            {displayName}
          </p>
          {connected && email ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">{email}</p>
          ) : (
            <p className="text-sm text-gray-400 dark:text-gray-500">Not connected</p>
          )}
        </div>
      </div>
      {connected && onDisconnect && (
        <button
          onClick={onDisconnect}
          className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 transition-colors"
        >
          Disconnect
        </button>
      )}
    </div>
  );
}
