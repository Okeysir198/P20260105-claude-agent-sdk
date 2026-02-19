'use client';

import { useState } from 'react';
import {
  useWhitelist,
  useAddWhitelistEntry,
  useRemoveWhitelistEntry,
  useToggleWhitelist,
  type WhitelistEntry,
} from '@/hooks/use-admin';
import { MessageSquare, ShieldCheck, ShieldAlert, Trash2, Plus, Phone, User, Tag, Bug, type LucideIcon } from 'lucide-react';

const PLATFORMS = ['whatsapp', 'telegram', 'zalo', 'imessage'] as const;

function platformIcon(platform: string): LucideIcon {
  const icons: Record<string, LucideIcon> = {
    whatsapp: MessageSquare,
    telegram: Bug,
    zalo: MessageSquare,
    imessage: MessageSquare,
  };
  return icons[platform] || MessageSquare;
}

function platformLabel(platform: string) {
  const labels: Record<string, string> = {
    whatsapp: 'WhatsApp',
    telegram: 'Telegram',
    zalo: 'Zalo',
    imessage: 'iMessage',
  };
  return labels[platform] ?? platform;
}

/* ── Mobile card for a single whitelist entry ── */
function EntryCard({
  entry,
  onRemove,
  isRemoving,
}: {
  entry: WhitelistEntry;
  onRemove: (id: string) => void;
  isRemoving: boolean;
}) {
  const PlatformIcon = platformIcon(entry.platform);

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
              <PlatformIcon className="h-3 w-3" />
              {platformLabel(entry.platform)}
            </span>
            <span className="font-mono text-xs text-gray-900 dark:text-white">
              {entry.phone_number}
            </span>
          </div>
          {entry.label && (
            <div className="mt-1 flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400 truncate">
              <Tag className="h-3 w-3 shrink-0" />
              <span className="truncate">{entry.label}</span>
            </div>
          )}
          {entry.mapped_username && (
            <div className="mt-0.5 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-500">
              <User className="h-3 w-3 shrink-0" />
              <span className="font-medium text-gray-700 dark:text-gray-300">{entry.mapped_username}</span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => onRemove(entry.id)}
          disabled={isRemoving}
          className="shrink-0 rounded p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
          title="Delete entry"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export default function PlatformUsersTab() {
  const { data } = useWhitelist();
  const addEntry = useAddWhitelistEntry();
  const removeEntry = useRemoveWhitelistEntry();
  const toggleWhitelist = useToggleWhitelist();

  const [form, setForm] = useState({
    platform: 'whatsapp',
    phone_number: '',
    label: '',
    mapped_username: '',
  });
  const [showForm, setShowForm] = useState(false);

  const enabled = data?.enabled ?? {};
  const entries = data?.entries ?? [];

  function handleToggle(platform: string) {
    toggleWhitelist.mutate({ platform, enabled: !enabled[platform] });
  }

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!form.phone_number.trim() || !form.label.trim()) return;
    addEntry.mutate(
      {
        platform: form.platform,
        phone_number: form.phone_number.trim(),
        label: form.label.trim(),
        mapped_username: form.mapped_username.trim(),
      },
      {
        onSuccess: () => {
          setForm({ platform: 'whatsapp', phone_number: '', label: '', mapped_username: '' });
          setShowForm(false);
        },
      },
    );
  }

  return (
    <div className="space-y-5">
      {/* Platform toggles */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Chat Platform Whitelist
          </h3>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Control which phone numbers can interact with each Chat Platform (WhatsApp, Telegram, Zalo, iMessage).
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {PLATFORMS.map((p) => {
            const isEnabled = !!enabled[p];
            const PlatformIcon = platformIcon(p);
            return (
              <div
                key={p}
                className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2.5"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
                    isEnabled ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-100 dark:bg-gray-700'
                  }`}>
                    <PlatformIcon className={`h-4 w-4 ${isEnabled ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {platformLabel(p)}
                    </span>
                    {!isEnabled && (
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                        Whitelist disabled
                      </p>
                    )}
                    {isEnabled && (
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                        Only allowed numbers
                      </p>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={isEnabled}
                  onClick={() => handleToggle(p)}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 dark:focus:ring-offset-gray-900 ${
                    isEnabled ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600'
                  }`}
                  disabled={toggleWhitelist.isPending}
                >
                  <span
                    className={`pointer-events-none inline-block h-4 w-4 translate-y-0.5 rounded-full bg-white shadow transition-transform ${
                      isEnabled ? 'translate-x-4' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Entries */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Whitelist entries ({entries.length})
            </h3>
          </div>
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary/90 transition-colors"
          >
            {showForm ? (
              <>Cancel</>
            ) : (
              <>
                <Plus className="h-3 w-3" />
                Add Entry
              </>
            )}
          </button>
        </div>

        {/* Add form (collapsible) */}
        {showForm && (
          <form onSubmit={handleAdd} className="mb-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div>
                <label className="flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  <MessageSquare className="h-3 w-3" />
                  Platform
                </label>
                <select
                  value={form.platform}
                  onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value }))}
                  className="w-full rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm px-2.5 py-1.5"
                >
                  {PLATFORMS.map((p) => (
                    <option key={p} value={p}>{platformLabel(p)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  <Phone className="h-3 w-3" />
                  Phone *
                </label>
                <input
                  type="text"
                  value={form.phone_number}
                  onChange={(e) => setForm((f) => ({ ...f, phone_number: e.target.value }))}
                  placeholder="+1234567890"
                  required
                  className="w-full rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm px-2.5 py-1.5"
                />
              </div>
              <div>
                <label className="flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  <Tag className="h-3 w-3" />
                  Label *
                </label>
                <input
                  type="text"
                  value={form.label}
                  onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
                  placeholder="Display name"
                  required
                  className="w-full rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm px-2.5 py-1.5"
                />
              </div>
              <div>
                <label className="flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  <User className="h-3 w-3" />
                  Mapped User <span className="text-gray-400">(opt)</span>
                </label>
                <input
                  type="text"
                  value={form.mapped_username}
                  onChange={(e) => setForm((f) => ({ ...f, mapped_username: e.target.value }))}
                  placeholder="username"
                  className="w-full rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm px-2.5 py-1.5"
                />
              </div>
            </div>
            <div className="mt-3 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={addEntry.isPending}
                className="rounded-md bg-primary text-white text-sm px-4 py-1.5 font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {addEntry.isPending ? 'Adding...' : 'Add Entry'}
              </button>
            </div>
          </form>
        )}

        {entries.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-600 py-6 text-center text-sm text-gray-400 dark:text-gray-500">
            No whitelist entries yet
          </div>
        ) : (
          <>
            {/* Mobile: card layout */}
            <div className="sm:hidden space-y-2">
              {entries.map((entry: WhitelistEntry) => (
                <EntryCard
                  key={entry.id}
                  entry={entry}
                  onRemove={(id) => removeEntry.mutate(id)}
                  isRemoving={removeEntry.isPending}
                />
              ))}
            </div>

            {/* Desktop: table layout */}
            <div className="hidden sm:block overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-800 text-left text-xs text-gray-500 dark:text-gray-400">
                    <th className="px-3 py-2 font-medium">Platform</th>
                    <th className="px-3 py-2 font-medium">Phone</th>
                    <th className="px-3 py-2 font-medium">Label</th>
                    <th className="px-3 py-2 font-medium">Mapped User</th>
                    <th className="px-3 py-2 font-medium w-10" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-800">
                  {entries.map((entry: WhitelistEntry) => (
                    <tr key={entry.id}>
                      <td className="px-3 py-2 text-gray-900 dark:text-white">
                        {platformLabel(entry.platform)}
                      </td>
                      <td className="px-3 py-2 text-gray-900 dark:text-white font-mono text-xs">
                        {entry.phone_number}
                      </td>
                      <td className="px-3 py-2 text-gray-600 dark:text-gray-300">{entry.label}</td>
                      <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                        {entry.mapped_username || '-'}
                      </td>
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          onClick={() => removeEntry.mutate(entry.id)}
                          disabled={removeEntry.isPending}
                          className="text-red-500 hover:text-red-700 dark:hover:text-red-400 text-xs"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
