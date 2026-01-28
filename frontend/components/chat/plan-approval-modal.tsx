'use client';

import { useEffect, useCallback, useState, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { usePlanStore } from '@/lib/store/plan-store';
import { cn } from '@/lib/utils';
import { Check, Circle, ClipboardList, ThumbsUp, ThumbsDown, MessageSquare, Keyboard } from 'lucide-react';

interface PlanApprovalModalProps {
  onSubmit: (planId: string, approved: boolean, feedback?: string) => void;
}

export function PlanApprovalModal({ onSubmit }: PlanApprovalModalProps) {
  const {
    isOpen,
    planId,
    title,
    summary,
    steps,
    timeoutSeconds,
    remainingSeconds,
    feedback,
    setFeedback,
    tick,
    closeModal,
  } = usePlanStore();

  const [showFeedback, setShowFeedback] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  // Reset feedback visibility when modal opens
  useEffect(() => {
    if (isOpen) {
      setShowFeedback(false);
    }
  }, [isOpen]);

  // Handle approve action
  const handleApprove = useCallback(() => {
    if (planId) {
      onSubmit(planId, true, feedback || undefined);
      closeModal();
    }
  }, [planId, feedback, onSubmit, closeModal]);

  // Handle reject action
  const handleReject = useCallback(() => {
    if (planId) {
      onSubmit(planId, false, feedback || undefined);
      closeModal();
    }
  }, [planId, feedback, onSubmit, closeModal]);

  // Keyboard shortcuts for approve/reject
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in the feedback textarea
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) {
        return;
      }

      const key = e.key.toLowerCase();

      // 'Y' or 'A' to approve
      if (key === 'y' || key === 'a') {
        e.preventDefault();
        handleApprove();
      }

      // 'N' or 'R' to reject
      if (key === 'n' || key === 'r') {
        e.preventDefault();
        handleReject();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleApprove, handleReject]);

  // Countdown timer
  useEffect(() => {
    if (!isOpen) return;

    const interval = setInterval(() => {
      tick();
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, tick]);

  // Auto-approve on timeout (default behavior)
  useEffect(() => {
    if (remainingSeconds === 0 && isOpen && planId) {
      onSubmit(planId, true);
      closeModal();
    }
  }, [remainingSeconds, isOpen, planId, onSubmit, closeModal]);

  const progressPercent = timeoutSeconds > 0 ? (remainingSeconds / timeoutSeconds) * 100 : 0;

  function getProgressColorVar(): string {
    if (progressPercent > 50) return '--progress-high';
    if (progressPercent > 25) return '--progress-medium';
    return '--progress-low';
  }

  // Count completed steps
  const completedCount = steps.filter(s => s.status === 'completed').length;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeModal()}>
      <DialogContent className="w-[95vw] sm:max-w-2xl md:max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="space-y-2">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
              style={{
                backgroundColor: 'hsl(var(--tool-plan) / 0.1)',
                color: 'hsl(var(--tool-plan))',
              }}
            >
              <ClipboardList className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0">
              <DialogTitle className="text-base sm:text-lg truncate">
                {title || 'Plan Ready for Review'}
              </DialogTitle>
              <DialogDescription className="text-xs sm:text-sm text-muted-foreground">
                Review and approve the proposed plan
              </DialogDescription>
            </div>
            <span className="text-xs sm:text-sm font-medium text-muted-foreground tabular-nums shrink-0">
              {remainingSeconds}s
            </span>
          </div>
        </DialogHeader>

        {/* Progress bar */}
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full transition-all duration-1000 ease-linear"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: `hsl(var(${getProgressColorVar()}))`,
            }}
          />
        </div>

        {/* Summary */}
        {summary && (
          <div className="px-1">
            <p className="text-sm text-muted-foreground leading-relaxed">{summary}</p>
          </div>
        )}

        {/* Steps list */}
        <div className="flex-1 overflow-y-auto py-2 px-1 space-y-1.5">
          <div className="flex items-center justify-between mb-2">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Plan Steps
            </Label>
            <span className="text-xs text-muted-foreground">
              {completedCount}/{steps.length} completed
            </span>
          </div>
          {steps.length === 0 ? (
            <div className="text-sm text-muted-foreground italic text-center py-4">
              No steps defined
            </div>
          ) : (
            steps.map((step, idx) => {
              const isCompleted = step.status === 'completed';
              const isInProgress = step.status === 'in_progress';
              return (
                <div
                  key={idx}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg border transition-colors",
                    isCompleted && "bg-status-success-bg border-status-success/20",
                    isInProgress && "bg-status-info-bg border-status-info/20",
                    !isCompleted && !isInProgress && "bg-muted/30 border-border/50"
                  )}
                >
                  <div className="shrink-0 mt-0.5">
                    {isCompleted ? (
                      <div className="w-5 h-5 rounded-full bg-status-success/20 flex items-center justify-center">
                        <Check className="h-3 w-3 text-status-success" />
                      </div>
                    ) : isInProgress ? (
                      <div className="w-5 h-5 rounded-full bg-status-info/20 flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-status-info animate-pulse" />
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-muted-foreground/30 flex items-center justify-center">
                        <span className="text-[10px] font-medium text-muted-foreground">{idx + 1}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={cn(
                      "text-sm leading-relaxed",
                      isCompleted && "text-muted-foreground line-through"
                    )}>
                      {step.description}
                    </p>
                  </div>
                  {step.status && (
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded shrink-0",
                      isCompleted && "bg-status-success-bg text-status-success border border-status-success/20",
                      isInProgress && "bg-status-info-bg text-status-info border border-status-info/20",
                      !isCompleted && !isInProgress && "bg-status-warning-bg text-status-warning-fg border border-status-warning/20"
                    )}>
                      {step.status}
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Feedback section */}
        {showFeedback && (
          <div className="space-y-2 border-t pt-3">
            <Label htmlFor="feedback" className="text-sm font-medium">
              Feedback (optional)
            </Label>
            <Textarea
              id="feedback"
              placeholder="Provide feedback or suggestions for the plan..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="min-h-[80px] resize-none"
            />
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0 flex-shrink-0 border-t pt-3 sm:pt-4 flex-col sm:flex-row">
          <div className="flex items-center gap-2 w-full sm:w-auto sm:mr-auto order-2 sm:order-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFeedback(!showFeedback)}
              className="flex items-center gap-1.5 h-9"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              {showFeedback ? 'Hide' : 'Add'} Feedback
            </Button>
            {/* Keyboard shortcut hints - hidden on mobile */}
            <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <Keyboard className="h-3 w-3" />
              <span>Press</span>
              <kbd className="px-1.5 py-0.5 rounded bg-muted border text-[9px] font-mono">Y</kbd>
              <span>approve</span>
              <kbd className="px-1.5 py-0.5 rounded bg-muted border text-[9px] font-mono">N</kbd>
              <span>reject</span>
            </div>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto order-1 sm:order-2">
            <Button
              variant="outline"
              onClick={handleReject}
              className="flex-1 sm:flex-none h-10 sm:h-9 text-destructive hover:text-destructive hover:bg-destructive/10 group"
            >
              <ThumbsDown className="h-4 w-4 mr-1.5" />
              <span>Reject</span>
              <kbd className="hidden sm:inline-flex ml-2 px-1.5 py-0.5 rounded bg-destructive/10 border border-destructive/20 text-[9px] font-mono opacity-60 group-hover:opacity-100 transition-opacity">N</kbd>
            </Button>
            <Button
              onClick={handleApprove}
              className="flex-1 sm:flex-none h-10 sm:h-9 bg-foreground hover:bg-foreground/90 text-background group"
            >
              <ThumbsUp className="h-4 w-4 mr-1.5" />
              <span>Approve</span>
              <kbd className="hidden sm:inline-flex ml-2 px-1.5 py-0.5 rounded bg-background/20 border border-background/30 text-[9px] font-mono opacity-60 group-hover:opacity-100 transition-opacity">Y</kbd>
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default PlanApprovalModal;
