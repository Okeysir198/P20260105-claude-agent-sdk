'use client';
import { Button } from '@/components/ui/button';
import { MessageSquarePlus } from 'lucide-react';

interface NewSessionButtonProps {
  onClick?: () => void;
}

export function NewSessionButton({ onClick }: NewSessionButtonProps) {
  return (
    <Button
      onClick={onClick}
      className="w-full gap-2 bg-primary text-primary-foreground hover:opacity-90"
      variant="default"
    >
      <MessageSquarePlus className="h-4 w-4" />
      New conversation
    </Button>
  );
}
