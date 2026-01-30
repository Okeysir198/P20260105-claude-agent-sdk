'use client';

import { useMessageQueueStore } from '@/lib/store/message-queue-store';
import { MessageSquare } from 'lucide-react';
import { useEffect, useState } from 'react';

export function QueuedMessagesIndicator() {
  const [queueLength, setQueueLength] = useState(0);
  const getQueueLength = useMessageQueueStore((s) => s.getQueueLength);

  useEffect(() => {
    // Update queue length every second
    const updateQueueLength = () => {
      setQueueLength(getQueueLength());
    };

    updateQueueLength();
    const interval = setInterval(updateQueueLength, 1000);

    return () => clearInterval(interval);
  }, [getQueueLength]);

  if (queueLength === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 rounded-lg border border-amber-200 dark:border-amber-800">
      <MessageSquare className="h-4 w-4" />
      <span className="text-sm font-medium">
        {queueLength} message{queueLength !== 1 ? 's' : ''} queued
      </span>
      <span className="text-xs text-amber-600 dark:text-amber-400">
        (will send when connected)
      </span>
    </div>
  );
}
