'use client';

import { FileText, Files } from 'lucide-react';
import { buttonVariants } from '@/components/ui/button';

interface SidebarTabsProps {
  activeTab: 'sessions' | 'files';
  onTabChange: (tab: 'sessions' | 'files') => void;
}

export function SidebarTabs({ activeTab, onTabChange }: SidebarTabsProps) {
  return (
    <div className="flex items-center border-b">
      <button
        onClick={() => onTabChange('sessions')}
        className={`
          flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium transition-colors
          border-b-2
          ${
            activeTab === 'sessions'
              ? 'bg-background border-primary text-foreground'
              : 'bg-muted/50 border-transparent text-muted-foreground hover:bg-muted/70 hover:text-foreground cursor-pointer'
          }
        `}
      >
        <Files className={`h-3.5 w-3.5 ${activeTab === 'sessions' ? 'text-primary' : ''}`} />
        <span>Sessions</span>
      </button>

      <button
        onClick={() => onTabChange('files')}
        className={`
          flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium transition-colors
          border-b-2
          ${
            activeTab === 'files'
              ? 'bg-background border-primary text-foreground'
              : 'bg-muted/50 border-transparent text-muted-foreground hover:bg-muted/70 hover:text-foreground cursor-pointer'
          }
        `}
      >
        <FileText className={`h-3.5 w-3.5 ${activeTab === 'files' ? 'text-primary' : ''}`} />
        <span>Files</span>
      </button>
    </div>
  );
}
