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
      variant="outline"
      className={cn('w-full', className)}
    >
      <Plus className="w-4 h-4 mr-2" />
      New Chat
    </Button>
  );
}
