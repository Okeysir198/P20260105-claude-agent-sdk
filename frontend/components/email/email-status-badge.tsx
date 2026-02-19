'use client';

import { Check, Eye, Shield, X } from 'lucide-react';
import { PROVIDER_NAMES } from './email-constants';

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
  accessLevel?: string;
  authType?: string;
  onDisconnect?: () => void;
  isDisconnecting?: boolean;
}

export function EmailStatusBadge({
  provider,
  connected,
  email,
  accessLevel,
  authType,
  onDisconnect,
  isDisconnecting,
}: EmailStatusBadgeProps) {
  const displayName = PROVIDER_NAMES[provider] || provider;
  const colors = PROVIDER_COLORS[provider] || DEFAULT_COLORS;

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div
          className={`p-2 rounded-full shrink-0 ${
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
        <div className="min-w-0">
          <p className="font-medium text-gray-900 dark:text-white truncate">
            {displayName}
          </p>
          {connected && email ? (
            <div className="flex flex-wrap items-center gap-1 sm:gap-2">
              <p className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-[180px] sm:max-w-none">{email}</p>
              {authType === 'oauth' && accessLevel === 'full_access' && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                  <Shield className="w-3 h-3" />
                  Full Access
                </span>
              )}
              {authType === 'oauth' && accessLevel !== 'full_access' && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  <Eye className="w-3 h-3" />
                  Read Only
                </span>
              )}
              {authType === 'app_password' && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                  IMAP
                </span>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400 dark:text-gray-500">Not connected</p>
          )}
        </div>
      </div>
      {connected && onDisconnect && (
        <button
          onClick={onDisconnect}
          disabled={isDisconnecting}
          className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50 transition-colors self-end sm:self-auto"
        >
          {isDisconnecting ? 'Disconnecting...' : 'Disconnect'}
        </button>
      )}
    </div>
  );
}
