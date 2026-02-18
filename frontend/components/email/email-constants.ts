export const DOMAIN_TO_PROVIDER: Record<string, string> = {
  'gmail.com': 'gmail',
  'googlemail.com': 'gmail',
  'yahoo.com': 'yahoo',
  'yahoo.co.uk': 'yahoo',
  'yahoo.co.jp': 'yahoo',
  'ymail.com': 'yahoo',
  'outlook.com': 'outlook',
  'hotmail.com': 'outlook',
  'live.com': 'outlook',
  'msn.com': 'outlook',
  'icloud.com': 'icloud',
  'me.com': 'icloud',
  'mac.com': 'icloud',
  'zoho.com': 'zoho',
  'zohomail.com': 'zoho',
};

export const PROVIDER_NAMES: Record<string, string> = {
  gmail: 'Gmail',
  yahoo: 'Yahoo Mail',
  outlook: 'Outlook',
  icloud: 'iCloud',
  zoho: 'Zoho Mail',
  custom: 'Custom IMAP',
};

export const IMAP_PROVIDERS = [
  { value: 'yahoo', label: 'Yahoo Mail' },
  { value: 'outlook', label: 'Outlook' },
  { value: 'icloud', label: 'iCloud' },
  { value: 'zoho', label: 'Zoho Mail' },
  { value: 'custom', label: 'Custom IMAP' },
];

export function detectProvider(email: string): string | null {
  const domain = email.split('@')[1]?.toLowerCase();
  if (!domain) return null;
  return DOMAIN_TO_PROVIDER[domain] || null;
}
