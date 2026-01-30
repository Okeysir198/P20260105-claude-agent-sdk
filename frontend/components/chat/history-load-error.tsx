'use client';

import { AlertTriangle, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HistoryLoadErrorProps {
  error: string;
  retryCount: number;
  maxRetries: number;
  isRetrying: boolean;
  onRetry: () => void;
}

function getUserFriendlyErrorMessage(error: string): string {
  const errorLower = error.toLowerCase();

  if (errorLower.includes('network') || errorLower.includes('fetch')) {
    return 'Unable to connect to the server. Please check your internet connection.';
  }
  if (errorLower.includes('timeout')) {
    return 'The request took too long. The server might be busy.';
  }
  if (errorLower.includes('401') || errorLower.includes('unauthorized')) {
    return 'Your session has expired. Please refresh the page to log in again.';
  }
  if (errorLower.includes('403') || errorLower.includes('forbidden')) {
    return 'You do not have permission to access this resource.';
  }
  if (errorLower.includes('404') || errorLower.includes('not found')) {
    return 'The requested resource could not be found. It may have been deleted.';
  }
  if (errorLower.includes('500') || errorLower.includes('server error')) {
    return 'The server encountered an error. Please try again later.';
  }
  if (errorLower.includes('websocket') || errorLower.includes('connection')) {
    return 'Connection to the chat server was interrupted. Attempting to reconnect...';
  }
  return 'An unexpected error occurred. Please try again.';
}

export function HistoryLoadError({ error, retryCount, maxRetries, isRetrying, onRetry }: HistoryLoadErrorProps) {
  const canRetry = retryCount < maxRetries;

  return (
    <div className="mx-4 my-2 rounded-lg border border-status-warning/30 bg-status-warning-bg p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-status-warning-fg" />
        <div className="flex-1 space-y-2">
          <p className="text-sm font-medium text-status-warning">
            Unable to load chat history
          </p>
          <p className="text-xs text-status-warning-fg">
            {getUserFriendlyErrorMessage(error)}
          </p>
          {canRetry && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              disabled={isRetrying}
              className="mt-2 border-status-warning/30 text-status-warning-fg hover:bg-status-warning-bg"
            >
              {isRetrying ? (
                <>
                  <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-3 w-3" />
                  Retry ({retryCount + 1}/{maxRetries})
                </>
              )}
            </Button>
          )}
          {!canRetry && (
            <p className="text-xs text-status-warning-fg">
              Maximum retry attempts reached. You can continue chatting, but previous messages may not be visible.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
