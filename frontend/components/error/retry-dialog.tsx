'use client';

import { useState } from 'react';
import { AlertTriangle, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface RetryOptions {
  title?: string;
  message?: string;
  retryLabel?: string;
  showReport?: boolean;
  onReport?: () => void;
}

interface UseRetryDialogReturn {
  showDialog: (options: RetryOptions & { onRetry: () => Promise<void> }) => void;
  RetryDialog: () => React.ReactElement | null;
}

export function useRetryDialog(): UseRetryDialogReturn {
  const [isOpen, setIsOpen] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [options, setOptions] = useState<RetryOptions & { onRetry: () => Promise<void> }>({
    onRetry: async () => {},
  });

  const showDialog = (opts: RetryOptions & { onRetry: () => Promise<void> }) => {
    setOptions(opts);
    setIsOpen(true);
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await options.onRetry();
      setIsOpen(false);
    } catch (error) {
      console.error('Retry failed:', error);
    } finally {
      setIsRetrying(false);
    }
  };

  const RetryDialog = () => {
    if (!isOpen) return null;

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div className="bg-surface-secondary rounded-2xl shadow-xl max-w-md w-full p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-warning-50 dark:bg-warning-900/20 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-warning-600" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary">
                {options.title || 'Operation Failed'}
              </h3>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsOpen(false)}
              disabled={isRetrying}
              className="h-6 w-6"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <p className="text-sm text-text-secondary mb-6">
            {options.message || 'Something went wrong. Would you like to try again?'}
          </p>

          <div className="flex gap-3 justify-end">
            {options.showReport && options.onReport && (
              <Button
                variant="outline"
                onClick={() => {
                  setIsOpen(false);
                  options.onReport?.();
                }}
                disabled={isRetrying}
              >
                Report Issue
              </Button>
            )}
            <Button
              variant="ghost"
              onClick={() => setIsOpen(false)}
              disabled={isRetrying}
            >
              Cancel
            </Button>
            <Button onClick={handleRetry} disabled={isRetrying}>
              {isRetrying ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Retrying...
                </>
              ) : (
                options.retryLabel || 'Retry'
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  };

  return { showDialog, RetryDialog };
}
