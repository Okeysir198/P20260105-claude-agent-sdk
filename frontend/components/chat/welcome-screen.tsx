'use client';
import { Sparkles, MessageSquare, Zap, Shield } from 'lucide-react';

export function WelcomeScreen() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
        <Sparkles className="h-8 w-8 text-primary" />
      </div>
      <h2 className="mb-3 text-2xl font-semibold">Welcome to Claude</h2>
      <p className="mb-8 max-w-md text-muted-foreground">
        Start a conversation with Claude. Ask questions, get help with coding, or explore ideas together.
      </p>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border p-5 text-left">
          <MessageSquare className="mb-3 h-8 w-8 text-primary" />
          <h3 className="mb-2 font-medium">Natural Conversations</h3>
          <p className="text-sm text-muted-foreground">
            Chat naturally with Claude about any topic.
          </p>
        </div>
        <div className="rounded-2xl border p-5 text-left">
          <Zap className="mb-3 h-8 w-8 text-primary" />
          <h3 className="mb-2 font-medium">Quick Responses</h3>
          <p className="text-sm text-muted-foreground">
            Get fast, thoughtful answers to your questions.
          </p>
        </div>
        <div className="rounded-2xl border p-5 text-left">
          <Shield className="mb-3 h-8 w-8 text-primary" />
          <h3 className="mb-2 font-medium">Safe & Secure</h3>
          <p className="text-sm text-muted-foreground">
            Your conversations are private and secure.
          </p>
        </div>
      </div>
    </div>
  );
}
