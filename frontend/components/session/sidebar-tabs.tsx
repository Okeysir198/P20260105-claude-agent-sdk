'use client';

import { FileText, Files, type LucideIcon } from 'lucide-react';

type TabId = 'sessions' | 'files';

interface SidebarTabsProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

const TABS: { id: TabId; label: string; icon: LucideIcon }[] = [
  { id: 'sessions', label: 'Sessions', icon: Files },
  { id: 'files', label: 'Files', icon: FileText },
];

export function SidebarTabs({ activeTab, onTabChange }: SidebarTabsProps) {
  return (
    <div className="flex items-center border-b">
      {TABS.map(({ id, label, icon: Icon }) => {
        const isActive = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`
              flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium transition-colors
              border-b-2
              ${
                isActive
                  ? 'bg-background border-primary text-foreground'
                  : 'bg-muted/50 border-transparent text-muted-foreground hover:bg-muted/70 hover:text-foreground cursor-pointer'
              }
            `}
          >
            <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-primary' : ''}`} />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
