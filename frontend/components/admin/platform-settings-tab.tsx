'use client';

import { useEffect, useState } from 'react';
import { useAdminSettings, useUpdatePlatformSettings } from '@/hooks/use-admin';
import { useAgents } from '@/hooks/use-agents';

export function PlatformSettingsTab() {
  const { data: settings, isLoading: settingsLoading } = useAdminSettings();
  const { data: agents, isLoading: agentsLoading } = useAgents();
  const updateSettings = useUpdatePlatformSettings();

  const [defaultAgentId, setDefaultAgentId] = useState<string>('');
  const [sessionMaxAgeHours, setSessionMaxAgeHours] = useState<number>(24);

  // Populate form state from query data
  useEffect(() => {
    if (settings?.platform) {
      setDefaultAgentId(settings.platform.default_agent_id ?? '');
      setSessionMaxAgeHours(settings.platform.session_max_age_hours);
    }
  }, [settings]);

  const handleSave = () => {
    updateSettings.mutate({
      default_agent_id: defaultAgentId || null,
      session_max_age_hours: sessionMaxAgeHours,
    });
  };

  if (settingsLoading || agentsLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-500 dark:text-gray-400">
        Loading settings...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Platform Settings
        </h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Configure default behavior for messaging platform integrations.
        </p>
      </div>

      <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        {/* Default Agent ID */}
        <div className="space-y-1.5">
          <label
            htmlFor="default-agent"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Default Agent
          </label>
          <select
            id="default-agent"
            value={defaultAgentId}
            onChange={(e) => setDefaultAgentId(e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          >
            <option value="">None (use system default)</option>
            {agents?.map((agent) => (
              <option key={agent.agent_id} value={agent.agent_id}>
                {agent.name}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            The agent used for new platform conversations when no agent is specified.
          </p>
        </div>

        {/* Session Max Age Hours */}
        <div className="space-y-1.5">
          <label
            htmlFor="session-max-age"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Session Max Age (hours)
          </label>
          <input
            id="session-max-age"
            type="number"
            min={1}
            value={sessionMaxAgeHours}
            onChange={(e) => setSessionMaxAgeHours(Number(e.target.value))}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          />
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Platform sessions older than this will be replaced with a new session.
          </p>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={updateSettings.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 dark:focus:ring-offset-gray-900"
        >
          {updateSettings.isPending ? 'Saving...' : 'Save'}
        </button>
        {updateSettings.isSuccess && (
          <span className="text-sm text-green-600 dark:text-green-400">
            Settings saved successfully.
          </span>
        )}
        {updateSettings.isError && (
          <span className="text-sm text-red-600 dark:text-red-400">
            {updateSettings.error?.message || 'Failed to save settings.'}
          </span>
        )}
      </div>
    </div>
  );
}
