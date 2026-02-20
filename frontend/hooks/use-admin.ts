import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const ADMIN_KEYS = {
  whitelist: 'admin-whitelist',
  settings: 'admin-settings',
  users: 'admin-users',
} as const;

const API_URL = '/api/proxy';

async function fetchJson(url: string, options?: RequestInit) {
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Request failed (${res.status})`);
  }
  return res.json();
}

// --- Types ---

export interface WhitelistEntry {
  id: string;
  platform: string;
  phone_number: string;
  label: string;
  mapped_username: string;
  created_at: string;
}

export interface WhitelistData {
  enabled: Record<string, boolean>;
  entries: WhitelistEntry[];
}

export interface PlatformSettings {
  default_agent_id: string | null;
  session_max_age_hours: number;
}

export interface AdminUser {
  id: string;
  username: string;
  full_name: string | null;
  role: string;
  created_at: string | null;
  last_login: string | null;
  is_active: boolean;
}

// --- Whitelist hooks ---

export function useWhitelist() {
  return useQuery<WhitelistData>({
    queryKey: [ADMIN_KEYS.whitelist],
    queryFn: () => fetchJson(`${API_URL}/admin/whitelist`),
  });
}

export function useAddWhitelistEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entry: { platform: string; phone_number: string; label: string; mapped_username: string }) =>
      fetchJson(`${API_URL}/admin/whitelist`, { method: 'POST', body: JSON.stringify(entry) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ADMIN_KEYS.whitelist] }),
  });
}

export function useRemoveWhitelistEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) =>
      fetchJson(`${API_URL}/admin/whitelist/${entryId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ADMIN_KEYS.whitelist] }),
  });
}

export function useToggleWhitelist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { platform: string; enabled: boolean }) =>
      fetchJson(`${API_URL}/admin/whitelist/toggle`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ADMIN_KEYS.whitelist] }),
  });
}

// --- Settings hooks ---

export function useAdminSettings() {
  return useQuery<{ platform: PlatformSettings }>({
    queryKey: [ADMIN_KEYS.settings],
    queryFn: () => fetchJson(`${API_URL}/admin/settings`),
  });
}

export function useUpdatePlatformSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (settings: Partial<PlatformSettings>) =>
      fetchJson(`${API_URL}/admin/settings/platform`, { method: 'PUT', body: JSON.stringify({ settings }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ADMIN_KEYS.settings] }),
  });
}

// --- User management hooks ---

export function useAdminUsers() {
  return useQuery<AdminUser[]>({
    queryKey: [ADMIN_KEYS.users],
    queryFn: () => fetchJson(`${API_URL}/admin/users`),
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (user: { username: string; password: string; full_name?: string; role?: string }) =>
      fetchJson(`${API_URL}/admin/users`, { method: 'POST', body: JSON.stringify(user) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ADMIN_KEYS.users] }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, ...update }: { userId: string; full_name?: string; role?: string; is_active?: boolean; password?: string }) =>
      fetchJson(`${API_URL}/admin/users/${userId}`, { method: 'PUT', body: JSON.stringify(update) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ADMIN_KEYS.users] }),
  });
}
