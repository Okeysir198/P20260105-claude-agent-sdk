'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/providers/auth-provider';
import PlatformUsersTab from '@/components/admin/platform-users-tab';
import { PlatformSettingsTab } from '@/components/admin/platform-settings-tab';
import UsersTab from '@/components/admin/users-tab';
import { Shield, MessageSquare, Settings, Users } from 'lucide-react';

const TABS = [
  { id: 'platform-users', label: 'Chat Platform Access', icon: MessageSquare },
  { id: 'platform-settings', label: 'Chat Platform Settings', icon: Settings },
  { id: 'users', label: 'User Management', icon: Users },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function AdminPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabId>('platform-users');

  useEffect(() => {
    if (!isLoading && (!user || user.role !== 'admin')) {
      router.replace('/');
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user || user.role !== 'admin') return null;

  return (
    <div className="max-w-4xl w-full mx-auto px-3 sm:px-4 py-2 sm:py-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        {/* Header */}
        <div className="p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
                Admin Settings
              </h1>
              <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-400">
                Manage Chat Platform access, settings, and users.
              </p>
            </div>
          </div>
        </div>

        {/* Tab bar — mobile-friendly */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <div className="flex">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 px-2 py-2.5 text-xs sm:text-sm sm:px-4 font-medium border-b-2 transition-colors text-center flex items-center justify-center gap-1.5 ${
                    activeTab === tab.id
                      ? 'border-primary text-primary'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4 shrink-0" />
                  <span className="hidden sm:inline">{tab.label}</span>
                  <span className="sm:hidden">{tab.id === 'platform-users' ? 'Access' : tab.id === 'platform-settings' ? 'Settings' : 'Users'}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tab content */}
        <div className="p-4 sm:p-6 overflow-x-hidden">
          {activeTab === 'platform-users' && <PlatformUsersTab />}
          {activeTab === 'platform-settings' && <PlatformSettingsTab />}
          {activeTab === 'users' && <UsersTab />}
        </div>
      </div>

      {/* Back to chat */}
      <div className="mt-6 text-center">
        <button
          onClick={() => router.push('/')}
          className="text-primary hover:text-primary/80 transition-colors"
        >
          &larr; Back to chat
        </button>
      </div>
    </div>
  );
}
