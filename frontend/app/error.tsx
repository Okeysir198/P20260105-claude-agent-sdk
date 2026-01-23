'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex h-screen items-center justify-center p-4">
      <div className="max-w-md text-center">
        <AlertCircle className="mx-auto mb-4 h-12 w-12 text-destructive" />
        <h2 className="mb-2 text-2xl font-bold">Something went wrong!</h2>
        <p className="mb-6 text-muted-foreground">{error.message || 'An unexpected error occurred'}</p>
        <Button onClick={reset}>Try again</Button>
      </div>
    </div>
  );
}
