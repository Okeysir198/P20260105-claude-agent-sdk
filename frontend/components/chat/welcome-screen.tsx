'use client';
import { Sparkles, MessageSquare, Zap, Shield } from 'lucide-react';

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

      {/* Content with staggered fade-in animations */}
      <div className="relative z-10 animate-in fade-in slide-in-from-bottom-4 duration-500 fill-mode-both">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20 mx-auto">
          <Sparkles className="h-8 w-8 text-primary" />
        </div>
      </div>

      <div className="relative z-10 animate-in fade-in slide-in-from-bottom-4 duration-500 delay-100 fill-mode-both">
        <h2 className="mb-3 text-2xl font-semibold tracking-tight">Welcome to Claude</h2>
        <p className="mb-8 max-w-md text-muted-foreground leading-relaxed">
          Start a conversation with Claude. Ask questions, get help with coding, or explore ideas together.
        </p>
      </div>

      <div className="relative z-10 grid gap-4 md:grid-cols-3 w-full max-w-3xl animate-in fade-in slide-in-from-bottom-4 duration-500 delay-200 fill-mode-both">
        <div className="group rounded-2xl border bg-card/50 p-5 text-left transition-all duration-200 hover:bg-card hover:shadow-md hover:border-primary/20">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform duration-200 group-hover:scale-110">
            <MessageSquare className="h-5 w-5" />
          </div>
          <h3 className="mb-2 font-medium">Natural Conversations</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Chat naturally with Claude about any topic.
          </p>
        </div>
        <div className="group rounded-2xl border bg-card/50 p-5 text-left transition-all duration-200 hover:bg-card hover:shadow-md hover:border-primary/20">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform duration-200 group-hover:scale-110">
            <Zap className="h-5 w-5" />
          </div>
          <h3 className="mb-2 font-medium">Quick Responses</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Get fast, thoughtful answers to your questions.
          </p>
        </div>
        <div className="group rounded-2xl border bg-card/50 p-5 text-left transition-all duration-200 hover:bg-card hover:shadow-md hover:border-primary/20">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform duration-200 group-hover:scale-110">
            <Shield className="h-5 w-5" />
          </div>
          <h3 className="mb-2 font-medium">Safe & Secure</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Your conversations are private and secure.
          </p>
        </div>
      </div>
    </div>
  );
}
