'use client';

import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NewSessionButtonProps {
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

export function NewSessionButton({ onClick, disabled, className }: NewSessionButtonProps) {
  return (
    <Button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'w-full justify-start gap-3',
        'bg-claude-orange-600 hover:bg-claude-orange-700',
        'text-white font-medium',
        'rounded-xl h-11',
        'shadow-soft hover:shadow-medium',
        'transition-all duration-200',
        className
      )}
    >
      <Plus className="w-4 h-4" />
      New Chat
    </Button>
  );
}
