'use client';

import { Check, X, Mail } from 'lucide-react';

interface EmailStatusBadgeProps {
  provider: 'gmail' | 'yahoo';
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
  const displayName = provider === 'gmail' ? 'Gmail' : 'Yahoo Mail';

  return (
    <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-3">
        <div
          className={`p-2 rounded-full ${
            connected
              ? 'bg-green-100 dark:bg-green-900/30'
              : 'bg-gray-100 dark:bg-gray-700'
          }`}
        >
          {connected ? (
            <Check className="w-5 h-5 text-green-600 dark:text-green-400" />
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
