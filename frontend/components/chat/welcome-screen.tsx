'use client';
import { Sparkles } from 'lucide-react';

export function WelcomeScreen() {
  return (
    <div className="relative flex h-full flex-col items-center justify-center p-8 text-center overflow-hidden">
      {/* Subtle gradient background */}
      <div
        className="absolute inset-0 opacity-30 dark:opacity-20 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 50% 0%, hsl(var(--primary) / 0.15) 0%, transparent 50%), radial-gradient(ellipse at 80% 80%, hsl(var(--primary) / 0.1) 0%, transparent 40%)',
        }}
      />

      {/* Content with fade-in animation */}
      <div className="relative z-10 animate-in fade-in slide-in-from-bottom-4 duration-500 fill-mode-both">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20 mx-auto">
          <Sparkles className="h-8 w-8 text-primary" />
        </div>
      </div>

      <div className="relative z-10 animate-in fade-in slide-in-from-bottom-4 duration-500 delay-100 fill-mode-both">
        <h2 className="text-2xl font-semibold tracking-tight">Welcome to TT-Bot</h2>
      </div>
    </div>
  );
}
