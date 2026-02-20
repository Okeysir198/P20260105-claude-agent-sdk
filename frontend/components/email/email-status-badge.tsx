'use client';

import { Eye, Shield, X, Unlink } from 'lucide-react';
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

// Provider brand icons as SVG components
const GmailIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M2 6C2 4.89543 2.89543 4 4 4H20C21.1046 4 22 4.89543 22 6V18C22 19.1046 21.1046 20 20 20H4C2.89543 20 2 19.1046 2 18V6Z" fill="currentColor" fillOpacity="0.1"/>
    <path d="M22 6L12 13L2 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" strokeWidth="2"/>
  </svg>
);

const YahooIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
    <path d="M12 2C14.5 2 16.5 4 17 6.5C16 9 14 11 12 12C10 11 8 9 7 6.5C7.5 4 9.5 2 12 2Z" fill="currentColor" fillOpacity="0.1"/>
    <path d="M12 2V12M7 6.5C7.5 9 9 11 12 12M17 6.5C16.5 9 15 11 12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const OutlookIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
    <path d="M3 9H21" stroke="currentColor" strokeWidth="2"/>
    <circle cx="8" cy="14" r="2" fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M12 16H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    <path d="M12 12H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const ICloudIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M6 16C3.79086 16 2 14.2091 2 12C2 9.79086 3.79086 8 6 8C6.4 8 6.8 8.05 7.2 8.15C7.7 5.85 9.65 4 12 4C14.35 4 16.3 5.85 16.8 8.15C17.2 8.05 17.6 8 18 8C20.2091 8 22 9.79086 22 12C22 14.2091 20.2091 16 18 16H6Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
    <path d="M12 16V12M12 16L8 12M12 16L16 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const ZohoIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
    <path d="M9 9L15 9M12 9L12 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.5"/>
  </svg>
);

const CustomIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2"/>
    <path d="M12 7V12L15 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    <path d="M8 12L12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    <path d="M12 8L16 12L12 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const PROVIDER_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  gmail: GmailIcon,
  yahoo: YahooIcon,
  outlook: OutlookIcon,
  icloud: ICloudIcon,
  zoho: ZohoIcon,
  custom: CustomIcon,
};

const DEFAULT_COLORS = {
  bg: 'bg-green-100 dark:bg-green-900/30',
  text: 'text-green-600 dark:text-green-400',
};

function AccessLevelBadge({ accessLevel }: { accessLevel?: string }) {
  const isFullAccess = accessLevel === 'full_access';
  const Icon = isFullAccess ? Shield : Eye;
  const label = isFullAccess ? 'Full Access' : 'Read Only';
  const colorClasses = isFullAccess
    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';

  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${colorClasses}`}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}

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
  const ProviderIcon = PROVIDER_ICONS[provider] || CustomIcon;

  return (
    <div className="group relative bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow overflow-hidden">
      {/* Status indicator bar */}
      <div className={`h-1 w-full ${connected ? colors.bg : 'bg-gray-300 dark:bg-gray-600'}`} />

      <div className="p-3">
        <div className="flex items-start justify-between gap-3">
          {/* Left section: Provider info */}
          <div className="flex items-start gap-3 flex-1 min-w-0">
            {/* Provider icon */}
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-lg shrink-0 ${
                connected
                  ? colors.bg
                  : 'bg-gray-100 dark:bg-gray-700'
              }`}
            >
              {connected ? (
                <ProviderIcon className={`w-5 h-5 ${colors.text}`} />
              ) : (
                <X className="w-5 h-5 text-gray-400 dark:text-gray-500" />
              )}
            </div>

            {/* Provider details */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <p className="font-semibold text-gray-900 dark:text-white truncate">
                  {displayName}
                </p>
                {connected && authType === 'oauth' && (
                  <AccessLevelBadge accessLevel={accessLevel} />
                )}
                {connected && authType === 'app_password' && (
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                    IMAP
                  </span>
                )}
              </div>

              {connected && email ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                  {email}
                </p>
              ) : (
                <p className="text-sm text-gray-400 dark:text-gray-500">Not connected</p>
              )}
            </div>
          </div>

          {/* Right section: Disconnect button */}
          {connected && onDisconnect && (
            <button
              onClick={onDisconnect}
              disabled={isDisconnecting}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
              title="Disconnect account"
            >
              <Unlink className="w-4 h-4" />
              <span className="hidden sm:inline">{isDisconnecting ? 'Disconnecting...' : 'Disconnect'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
