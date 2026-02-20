'use client';

import { useState } from 'react';
import { Eye, Shield, type LucideIcon } from 'lucide-react';

type AccessLevel = 'read_only' | 'full_access';

interface ConnectGmailButtonProps {
  onConnected?: () => void;
}

const GMAIL_ICON = (
  <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none">
    <path
      d="M22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6zm-2 0l-8 5-8-5h16zm0 12H4V8l8 5 8-5v10z"
      fill="currentColor"
    />
  </svg>
);

interface AccessOption {
  level: AccessLevel;
  label: string;
  description: string;
  icon: LucideIcon;
  borderColor: string;
  hoverColor: string;
  iconBgColor: string;
  iconTextColor: string;
  badgeColor: string;
}

const ACCESS_OPTIONS: AccessOption[] = [
  {
    level: 'read_only',
    label: 'Gmail — Read Only',
    description: 'List, read, search emails',
    icon: Eye,
    borderColor: 'border-gray-200 dark:border-gray-700',
    hoverColor: 'hover:border-gray-400 dark:hover:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-750',
    iconBgColor: 'bg-gray-100 dark:bg-gray-700',
    iconTextColor: 'text-gray-600 dark:text-gray-300',
    badgeColor: 'text-gray-400 dark:text-gray-500',
  },
  {
    level: 'full_access',
    label: 'Gmail — Full Access',
    description: 'Send, reply, modify + read',
    icon: Shield,
    borderColor: 'border-amber-200 dark:border-amber-700',
    hoverColor: 'hover:border-amber-400 dark:hover:border-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20',
    iconBgColor: 'bg-amber-50 dark:bg-amber-900/30',
    iconTextColor: 'text-amber-600 dark:text-amber-400',
    badgeColor: 'text-amber-500 dark:text-amber-400',
  },
];

export function ConnectGmailButton({ onConnected: _onConnected }: ConnectGmailButtonProps) {
  const [isLoading, setIsLoading] = useState<AccessLevel | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleConnect(accessLevel: AccessLevel): Promise<void> {
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
  }

  return (
    <div className="space-y-2">
      {ACCESS_OPTIONS.map(({ level, label, description, icon: BadgeIcon, borderColor, hoverColor, iconBgColor, iconTextColor, badgeColor }) => (
        <button
          key={level}
          onClick={() => handleConnect(level)}
          disabled={isLoading !== null}
          className={`flex items-center gap-3 w-full px-4 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg border ${borderColor} ${hoverColor} disabled:opacity-50 disabled:cursor-not-allowed transition-colors`}
        >
          <div className={`flex items-center justify-center w-9 h-9 rounded-lg ${iconBgColor} ${iconTextColor} shrink-0`}>
            {GMAIL_ICON}
          </div>
          <div className="flex-1 text-left min-w-0">
            <div className="text-sm font-medium truncate">
              {isLoading === level ? 'Connecting...' : label}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {description}
            </div>
          </div>
          <BadgeIcon className={`w-4 h-4 ${badgeColor} shrink-0`} />
        </button>
      ))}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
