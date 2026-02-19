import { Suspense } from 'react';
import { LoginForm } from '@/components/features/auth/login-form';

export default function LoginPage() {
  return (
    <div className="max-w-sm w-full px-4">
      <div className="bg-card rounded-lg border p-6 sm:p-8 shadow-lg">
        <Suspense fallback={
          <div className="flex items-center justify-center p-4">
            <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        }>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
