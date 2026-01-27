'use client';
import type { ChatMessage } from '@/types';
import { formatTime, cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Loader2, Circle, CircleDot, CheckCircle2, ClipboardList, CheckCircle, AlertCircle, MessageSquare, Check, Clock } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useState } from 'react';
import { getToolIcon, getToolColorStyles, getToolSummary } from '@/lib/tool-config';

interface ToolUseMessageProps {
  message: ChatMessage;
  isRunning?: boolean;
  result?: ChatMessage; // The tool_result for this tool_use
}

export function ToolUseMessage({ message, isRunning = false, result }: ToolUseMessageProps) {
  const [expanded, setExpanded] = useState(false);

  const toolName = message.toolName || '';
  const ToolIcon = getToolIcon(toolName);
  const colorStyles = getToolColorStyles(toolName);
  const summary = getToolSummary(toolName, message.toolInput);
  const hasResult = !!result;
  const isError = result?.isError;

  // Special rendering for TodoWrite - always visible, no accordion
  if (toolName === 'TodoWrite') {
    return (
      <TodoWriteDisplay
        message={message}
        isRunning={isRunning}
        ToolIcon={ToolIcon}
        colorStyles={colorStyles}
      />
    );
  }

  // Special rendering for EnterPlanMode - always visible planning indicator
  if (toolName === 'EnterPlanMode') {
    return (
      <EnterPlanModeDisplay
        message={message}
        isRunning={isRunning}
        colorStyles={colorStyles}
      />
    );
  }

  // Special rendering for ExitPlanMode - always visible plan summary
  if (toolName === 'ExitPlanMode') {
    return (
      <ExitPlanModeDisplay
        message={message}
        isRunning={isRunning}
        colorStyles={colorStyles}
      />
    );
  }

  // Special rendering for AskUserQuestion - always visible with tabs and answer
  if (toolName === 'AskUserQuestion') {
    return (
      <AskUserQuestionDisplay
        message={message}
        isRunning={isRunning}
        colorStyles={colorStyles}
        answer={result?.content}
      />
    );
  }

  return (
    <div className="group flex gap-3 py-1.5 px-4">
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border',
          isRunning && 'animate-pulse'
        )}
        style={{ color: colorStyles.iconText?.color || 'hsl(var(--muted-foreground))' }}
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ToolIcon className="h-3.5 w-3.5" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        {message.toolInput && (
          <Card
            className="overflow-hidden rounded-lg shadow-sm max-w-2xl bg-muted/30 border-l-2"
            style={{ borderLeftColor: colorStyles.iconText?.color || 'hsl(var(--border))' }}
          >
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start rounded-none border-b border-border/50 px-3 py-2 text-xs hover:bg-muted/50 h-auto min-h-[36px]"
              onClick={() => setExpanded(!expanded)}
            >
              <div className="flex items-center gap-2 w-full">
                {expanded ? (
                  <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                )}
                <span className="font-medium text-foreground">{toolName}</span>
                {!expanded && summary && (
                  <>
                    <span className="text-muted-foreground/60">:</span>
                    <span className="text-muted-foreground/80 font-mono text-[11px] truncate">
                      {summary}
                    </span>
                  </>
                )}
                {/* Status indicator on the right */}
                <span className="ml-auto flex items-center gap-1.5 shrink-0">
                  {isRunning ? (
                    <span className="flex items-center gap-1.5 text-blue-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-[10px] font-medium">Running</span>
                    </span>
                  ) : hasResult ? (
                    isError ? (
                      <span className="flex items-center gap-1 text-destructive">
                        <AlertCircle className="h-4 w-4" />
                        <span className="text-[10px] font-medium">Error</span>
                      </span>
                    ) : (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    )
                  ) : (
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Clock className="h-3.5 w-3.5" />
                      <span className="text-[10px]">Pending</span>
                    </span>
                  )}
                </span>
              </div>
            </Button>
            {expanded && (
              <div className="bg-background/50">
                {/* Tool Input */}
                <div className="p-3 border-b border-border/30">
                  <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Input</div>
                  <ToolInputDisplay toolName={toolName} input={message.toolInput} />
                </div>
                {/* Tool Result */}
                {hasResult && (
                  <div className="p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Output</span>
                      {isError && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-destructive/10 text-destructive border border-destructive/20">
                          Error
                        </span>
                      )}
                    </div>
                    <ToolResultDisplay content={result.content} isError={isError} />
                  </div>
                )}
                {/* Show loading state if running but no result yet */}
                {isRunning && !hasResult && (
                  <div className="p-3 flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span className="text-[11px]">Waiting for result...</span>
                  </div>
                )}
              </div>
            )}
          </Card>
        )}
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Display tool result content with proper formatting
 */
function ToolResultDisplay({ content, isError }: { content: string; isError?: boolean }) {
  if (!content) return null;

  // Try to parse as JSON for pretty display
  let formattedContent = content;
  let isJson = false;
  try {
    const parsed = JSON.parse(content);
    formattedContent = JSON.stringify(parsed, null, 2);
    isJson = true;
  } catch {
    // Not JSON, use as-is
  }

  const lines = formattedContent.split('\n');
  const isLong = lines.length > 10;
  const preview = isLong ? lines.slice(0, 10).join('\n') + '\n...' : formattedContent;

  return (
    <pre
      className={cn(
        "text-[11px] font-mono whitespace-pre-wrap break-all rounded p-2 max-h-64 overflow-auto",
        isError
          ? "bg-destructive/5 text-destructive border border-destructive/20"
          : "bg-muted/30 text-foreground border border-border/30"
      )}
    >
      {isJson ? (
        <code>{formattedContent}</code>
      ) : (
        <code>{preview}</code>
      )}
    </pre>
  );
}

interface TodoWriteDisplayProps {
  message: ChatMessage;
  isRunning: boolean;
  ToolIcon: LucideIcon;
  colorStyles: {
    iconText?: React.CSSProperties;
    badge?: React.CSSProperties;
  };
}

/**
 * Special display for TodoWrite - always visible task list (no accordion)
 */
function TodoWriteDisplay({ message, isRunning, ToolIcon, colorStyles }: TodoWriteDisplayProps) {
  const todos = message.toolInput?.todos as Array<{
    content?: string;
    subject?: string;
    status?: string;
    activeForm?: string;
  }> | undefined;

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />;
      case 'in_progress':
        return <CircleDot className="h-3.5 w-3.5 text-blue-500" />;
      default: // pending
        return <Circle className="h-3.5 w-3.5 text-muted-foreground/50" />;
    }
  };

  const getStatusBadge = (status?: string) => {
    const statusText = status || 'pending';
    const badgeClass = cn(
      "text-[10px] px-1.5 py-0.5 rounded shrink-0",
      status === 'completed' && "bg-green-500/10 text-green-500 border border-green-500/20",
      status === 'in_progress' && "bg-blue-500/10 text-blue-500 border border-blue-500/20",
      (!status || status === 'pending') && "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border border-yellow-500/20"
    );
    return <span className={badgeClass}>{statusText}</span>;
  };

  return (
    <div className="group flex gap-3 py-1.5 px-4">
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border',
          isRunning && 'animate-pulse'
        )}
        style={{ color: colorStyles.iconText?.color || 'hsl(var(--muted-foreground))' }}
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ToolIcon className="h-3.5 w-3.5" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <Card className="overflow-hidden rounded-lg shadow-sm max-w-2xl bg-muted/30 border-l-2"
          style={{ borderLeftColor: colorStyles.iconText?.color || 'hsl(var(--border))' }}>
          {/* Header - non-clickable */}
          <div className="px-3 py-2 border-b border-border/50">
            <div className="flex items-center gap-2">
              <span className="font-medium text-xs text-foreground">TodoWrite</span>
              {todos && todos.length > 0 && (
                <span className="text-[10px] text-muted-foreground">
                  {todos.length} {todos.length === 1 ? 'task' : 'tasks'}
                </span>
              )}
              {isRunning && (
                <span className="ml-auto text-xs text-muted-foreground flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-foreground/40 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-foreground/60"></span>
                  </span>
                  <span className="text-[11px]">Running</span>
                </span>
              )}
            </div>
          </div>
          {/* Task list - always visible */}
          <div className="p-2 bg-background/50 space-y-1">
            {!todos || todos.length === 0 ? (
              <div className="text-[11px] text-muted-foreground italic px-2 py-1">
                No todos defined
              </div>
            ) : (
              todos.map((todo, idx) => {
                const isCompleted = todo.status === 'completed';
                const taskName = todo.subject || todo.content || todo.activeForm || 'Unnamed task';
                return (
                  <div
                    key={idx}
                    className="flex items-center gap-2 text-[11px] px-2 py-1.5 rounded hover:bg-muted/30 transition-colors"
                  >
                    <div className="shrink-0">
                      {getStatusIcon(todo.status)}
                    </div>
                    <div className={cn(
                      "flex-1 min-w-0 truncate font-medium",
                      isCompleted && "line-through text-muted-foreground"
                    )}>
                      {taskName}
                    </div>
                    {getStatusBadge(todo.status)}
                  </div>
                );
              })
            )}
          </div>
        </Card>
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}

interface PlanModeDisplayProps {
  message: ChatMessage;
  isRunning: boolean;
  colorStyles: {
    iconText?: React.CSSProperties;
    badge?: React.CSSProperties;
  };
}

/**
 * Display for EnterPlanMode - shows that Claude is entering planning mode
 */
function EnterPlanModeDisplay({ message, isRunning, colorStyles }: PlanModeDisplayProps) {
  return (
    <div className="group flex gap-3 py-1.5 px-4">
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border',
          isRunning && 'animate-pulse'
        )}
        style={{ color: 'hsl(var(--tool-plan))' }}
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ClipboardList className="h-3.5 w-3.5" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <Card className="overflow-hidden rounded-lg shadow-sm max-w-2xl bg-muted/30 border-l-2"
          style={{ borderLeftColor: 'hsl(var(--tool-plan))' }}>
          <div className="px-3 py-2.5 border-b border-border/50">
            <div className="flex items-center gap-2">
              <span className="font-medium text-xs text-foreground">Entering Plan Mode</span>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded border"
                style={{
                  backgroundColor: 'hsl(var(--tool-plan) / 0.1)',
                  color: 'hsl(var(--tool-plan))',
                  borderColor: 'hsl(var(--tool-plan) / 0.2)',
                }}
              >
                Planning
              </span>
              {isRunning && (
                <span className="ml-auto text-xs text-muted-foreground flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                      style={{ backgroundColor: 'hsl(var(--tool-plan) / 0.4)' }}></span>
                    <span className="relative inline-flex rounded-full h-2 w-2"
                      style={{ backgroundColor: 'hsl(var(--tool-plan) / 0.6)' }}></span>
                  </span>
                  <span className="text-[11px]">Analyzing</span>
                </span>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1.5 leading-relaxed">
              Claude is analyzing the task and will propose an implementation plan for your approval.
            </p>
          </div>
        </Card>
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Display for ExitPlanMode - shows the plan ready for approval
 */
function ExitPlanModeDisplay({ message, isRunning, colorStyles }: PlanModeDisplayProps) {
  const input = message.toolInput || {};
  const launchSwarm = input.launchSwarm as boolean | undefined;
  const teammateCount = input.teammateCount as number | undefined;
  const allowedPrompts = input.allowedPrompts as Array<{ tool: string; prompt: string }> | undefined;

  return (
    <div className="group flex gap-3 py-1.5 px-4">
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border',
          isRunning && 'animate-pulse'
        )}
        style={{ color: 'hsl(var(--tool-plan))' }}
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <CheckCircle className="h-3.5 w-3.5" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <Card className="overflow-hidden rounded-lg shadow-sm max-w-2xl bg-muted/30 border-l-2"
          style={{ borderLeftColor: 'hsl(var(--tool-plan))' }}>
          {/* Header */}
          <div className="px-3 py-2.5 border-b border-border/50">
            <div className="flex items-center gap-2">
              <span className="font-medium text-xs text-foreground">Plan Ready for Approval</span>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded border"
                style={{
                  backgroundColor: 'hsl(var(--progress-high) / 0.1)',
                  color: 'hsl(var(--progress-high))',
                  borderColor: 'hsl(var(--progress-high) / 0.2)',
                }}
              >
                Ready
              </span>
              {isRunning && (
                <span className="ml-auto text-xs text-muted-foreground flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                      style={{ backgroundColor: 'hsl(var(--tool-plan) / 0.4)' }}></span>
                    <span className="relative inline-flex rounded-full h-2 w-2"
                      style={{ backgroundColor: 'hsl(var(--tool-plan) / 0.6)' }}></span>
                  </span>
                  <span className="text-[11px]">Processing</span>
                </span>
              )}
            </div>
          </div>
          {/* Content */}
          <div className="p-3 space-y-2">
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Claude has completed the plan and is awaiting your approval to proceed with implementation.
            </p>
            {/* Execution details */}
            <div className="flex flex-wrap gap-2">
              {launchSwarm && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20">
                  Swarm: {teammateCount || 'auto'} agents
                </span>
              )}
              {allowedPrompts && allowedPrompts.length > 0 && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                  {allowedPrompts.length} permission{allowedPrompts.length > 1 ? 's' : ''} requested
                </span>
              )}
            </div>
            {/* Permissions list */}
            {allowedPrompts && allowedPrompts.length > 0 && (
              <div className="space-y-1 pt-1">
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                  Requested Permissions
                </span>
                <div className="space-y-1">
                  {allowedPrompts.map((perm, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <AlertCircle className="h-3 w-3 text-amber-500" />
                      <span className="font-mono text-[10px] bg-muted/50 px-1 rounded">{perm.tool}</span>
                      <span>{perm.prompt}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}

interface AskUserQuestionDisplayProps {
  message: ChatMessage;
  isRunning: boolean;
  colorStyles: {
    iconText?: React.CSSProperties;
    badge?: React.CSSProperties;
  };
  answer?: string;
}

/**
 * Display for AskUserQuestion - collapsible with tabbed questions and answer
 */
function AskUserQuestionDisplay({ message, isRunning, colorStyles, answer }: AskUserQuestionDisplayProps) {
  const [activeTab, setActiveTab] = useState(0);

  const questions = message.toolInput?.questions as Array<{
    question: string;
    header?: string;
    options?: Array<{
      label: string;
      description?: string;
    }>;
    multiSelect?: boolean;
  }> | undefined;

  // Parse the answer to extract user selections
  const parsedAnswers = answer ? parseAnswerContent(answer) : null;

  const questionCount = questions?.length || 0;
  const hasAnswer = !!parsedAnswers && Object.keys(parsedAnswers).length > 0;

  // Default: expanded when waiting for answer, collapsed when answered
  const [expanded, setExpanded] = useState(!hasAnswer);

  // Get summary for collapsed state
  const getSummary = () => {
    if (hasAnswer && questions && questions.length > 0) {
      const firstQuestion = questions[0];
      const firstAnswer = parsedAnswers?.[firstQuestion.question];
      if (firstAnswer) {
        const answerText = Array.isArray(firstAnswer) ? firstAnswer.join(', ') : firstAnswer;
        return answerText.length > 50 ? answerText.slice(0, 50) + '...' : answerText;
      }
    }
    if (questions && questions.length > 0) {
      const q = questions[0].question;
      return q.length > 40 ? q.slice(0, 40) + '...' : q;
    }
    return null;
  };

  return (
    <div className="group flex gap-3 py-1.5 px-4">
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border',
          isRunning && 'animate-pulse'
        )}
        style={{ color: 'hsl(var(--tool-question))' }}
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : hasAnswer ? (
          <Check className="h-3.5 w-3.5" />
        ) : (
          <MessageSquare className="h-3.5 w-3.5" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <Card className="overflow-hidden rounded-lg shadow-sm max-w-2xl bg-muted/30 border-l-2"
          style={{ borderLeftColor: 'hsl(var(--tool-question))' }}>
          {/* Header line - clickable to expand/collapse */}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start rounded-none px-3 py-2 text-xs hover:bg-muted/50 h-auto min-h-[36px] border-b border-border/50"
            onClick={() => setExpanded(!expanded)}
          >
            <div className="flex items-center gap-2 w-full">
              {expanded ? (
                <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              )}
              <span className="font-medium text-foreground">AskUserQuestion</span>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded border"
                style={{
                  backgroundColor: hasAnswer ? 'hsl(var(--progress-high) / 0.1)' : 'hsl(var(--tool-question) / 0.1)',
                  color: hasAnswer ? 'hsl(var(--progress-high))' : 'hsl(var(--tool-question))',
                  borderColor: hasAnswer ? 'hsl(var(--progress-high) / 0.2)' : 'hsl(var(--tool-question) / 0.2)',
                }}
              >
                {hasAnswer ? 'Answered' : 'Waiting'}
              </span>
              {!expanded && getSummary() && (
                <>
                  <span className="text-muted-foreground/60">:</span>
                  <span className="text-muted-foreground/80 font-normal text-[11px] truncate">
                    {getSummary()}
                  </span>
                </>
              )}
              {/* Status indicator on the right */}
              <span className="ml-auto flex items-center gap-1.5 shrink-0">
                {isRunning ? (
                  <span className="flex items-center gap-1.5 text-amber-500">
                    <Clock className="h-4 w-4" />
                    <span className="text-[10px] font-medium">Waiting</span>
                  </span>
                ) : hasAnswer ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <span className="flex items-center gap-1 text-amber-500">
                    <Clock className="h-4 w-4" />
                    <span className="text-[10px] font-medium">Waiting</span>
                  </span>
                )}
              </span>
            </div>
          </Button>

          {/* Expanded content */}
          {expanded && (
            <>
              {/* Question tabs - clear tab design */}
              {questionCount > 0 && (
                <div className="border-b-[3px] border-border bg-muted/20">
                  <div className="px-3 pt-2">
                    <div className="flex items-end gap-3">
                      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider shrink-0 pb-1.5">
                        Questions
                      </span>
                      {questionCount > 1 ? (
                        <div className="flex gap-1">
                          {questions?.map((q, idx) => {
                            const isActive = activeTab === idx;
                            const questionAnswer = parsedAnswers?.[q.question];
                            const isAnswered = !!questionAnswer;
                            return (
                              <button
                                key={idx}
                                onClick={() => setActiveTab(idx)}
                                className={cn(
                                  "flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium transition-colors whitespace-nowrap rounded-t-md -mb-[3px]",
                                  isActive
                                    ? "bg-background border-[3px] border-b-0 border-primary text-foreground"
                                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                )}
                              >
                                {isAnswered ? (
                                  <Check className="h-3.5 w-3.5 text-green-500" />
                                ) : (
                                  <span className="w-5 h-5 rounded-full bg-muted border border-border flex items-center justify-center text-[10px] font-bold">
                                    {idx + 1}
                                  </span>
                                )}
                                <span className="max-w-[100px] truncate">
                                  {q.header || `Q${idx + 1}`}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      ) : (
                        <span className="text-[10px] text-muted-foreground pb-1.5">1 of 1</span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Question content */}
              <div className="p-3 bg-background/50">
                {!questions || questions.length === 0 ? (
                  <div className="text-[11px] text-muted-foreground italic">
                    No questions defined
                  </div>
                ) : (
                  <QuestionContent
                    question={questions[activeTab]}
                    answer={parsedAnswers?.[questions[activeTab]?.question]}
                    colorStyles={colorStyles}
                  />
                )}
              </div>
            </>
          )}
        </Card>
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}

interface QuestionContentProps {
  question: {
    question: string;
    header?: string;
    options?: Array<{
      label: string;
      description?: string;
    }>;
    multiSelect?: boolean;
  };
  answer?: string | string[];
  colorStyles: {
    iconText?: React.CSSProperties;
    badge?: React.CSSProperties;
  };
}

function QuestionContent({ question, answer, colorStyles }: QuestionContentProps) {
  const answers = Array.isArray(answer) ? answer : answer ? [answer] : [];

  return (
    <div className="space-y-2">
      {/* Question text with optional header */}
      <div>
        {question.header && (
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mr-2">
            {question.header}:
          </span>
        )}
        <span className="text-xs text-foreground">{question.question}</span>
      </div>
      {/* Options - compact list */}
      {question.options && question.options.length > 0 && (
        <div className="space-y-0.5 pl-1">
          {question.options.map((opt, oIdx) => {
            const isSelected = answers.includes(opt.label) || answers.some(a => a.includes(opt.label));
            return (
              <div
                key={oIdx}
                className={cn(
                  "flex items-center gap-2 text-[11px] px-2 py-1 rounded transition-colors",
                  isSelected
                    ? "bg-green-500/10 text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {isSelected ? (
                  <Check className="h-3 w-3 text-green-500 shrink-0" />
                ) : (
                  <span className="w-3 h-3 flex items-center justify-center text-[9px] font-medium text-muted-foreground/50 shrink-0">
                    {String.fromCharCode(65 + oIdx)}
                  </span>
                )}
                <span className={cn("truncate", isSelected && "font-medium")}>{opt.label}</span>
                {opt.description && (
                  <span className="text-[10px] text-muted-foreground/70 truncate hidden sm:inline">
                    — {opt.description}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
      {/* User's answer section - only show for free-text answers (no predefined options) */}
      {answers.length > 0 && (!question.options || question.options.length === 0) && (
        <div className="pt-2 border-t border-border/50">
          <div className="flex items-center gap-2 mb-2">
            <Check className="h-3 w-3 text-green-500" />
            <span className="text-[10px] font-medium text-green-600 dark:text-green-400 uppercase tracking-wider">
              User&apos;s Answer
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {answers.map((ans, idx) => (
              <span
                key={idx}
                className="text-[11px] px-2 py-1 rounded-md bg-green-500/10 text-green-700 dark:text-green-300 border border-green-500/30 font-medium"
              >
                {ans}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Parse the answer content from tool_result to extract user selections
 * The answer format from backend is typically: {"question_text": "selected_value"} or similar
 */
function parseAnswerContent(content: string): Record<string, string | string[]> | null {
  try {
    // Try to parse as JSON first
    const parsed = JSON.parse(content);
    if (typeof parsed === 'object' && parsed !== null) {
      return parsed;
    }
  } catch {
    // Not JSON - try to extract from text format
    // Common formats: "User selected: Option A" or "Answer: Option B"
    const result: Record<string, string | string[]> = {};

    // Try to match patterns like "selected: value" or "answer: value"
    const selectMatch = content.match(/(?:selected|answer|chose|picked):\s*(.+)/i);
    if (selectMatch) {
      result['_answer'] = selectMatch[1].trim();
      return result;
    }

    // If it's just plain text, use it as the answer
    if (content.trim()) {
      result['_answer'] = content.trim();
      return result;
    }
  }
  return null;
}

interface ToolInputDisplayProps {
  toolName: string;
  input: Record<string, unknown>;
}

/**
 * Renders tool-specific input display.
 */
function ToolInputDisplay({ toolName, input }: ToolInputDisplayProps) {
  const colorStyles = getToolColorStyles(toolName);

  if (toolName === 'Bash') {
    const command = input.command as string | undefined;
    const description = input.description as string | undefined;
    return (
      <div className="space-y-2">
        {description && (
          <p className="text-[11px] text-muted-foreground italic">{description}</p>
        )}
        {command && (
          <pre
            className="p-2.5 rounded-md text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all bg-muted/50 border border-border/50"
            style={{
              color: 'hsl(var(--code-fg))',
            }}
          >
            <span style={{ color: 'hsl(var(--code-prompt))' }} className="select-none">
              ${' '}
            </span>
            {command}
          </pre>
        )}
        {typeof input.timeout === 'number' && (
          <p className="text-[11px] text-muted-foreground">Timeout: {input.timeout}ms</p>
        )}
      </div>
    );
  }

  if (toolName === 'Read') {
    const filePath = input.file_path as string | undefined;
    const offset = input.offset as number | undefined;
    const limit = input.limit as number | undefined;
    return (
      <div className="space-y-2">
        {filePath && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground">File:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
              style={colorStyles.badge}
            >
              {filePath}
            </code>
          </div>
        )}
        {(offset !== undefined || limit !== undefined) && (
          <div className="flex gap-4 text-[11px] text-muted-foreground">
            {offset !== undefined && <span>Offset: {offset}</span>}
            {limit !== undefined && <span>Limit: {limit}</span>}
          </div>
        )}
      </div>
    );
  }

  if (toolName === 'Write' || toolName === 'Edit') {
    const filePath = input.file_path as string | undefined;
    const content = input.content as string | undefined;
    const oldString = input.old_string as string | undefined;
    const newString = input.new_string as string | undefined;
    return (
      <div className="space-y-2">
        {filePath && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground">File:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
              style={colorStyles.badge}
            >
              {filePath}
            </code>
          </div>
        )}
        {content && (
          <div>
            <span className="text-[11px] text-muted-foreground block mb-1">Content:</span>
            <pre className="bg-muted/40 border border-border/50 p-2 rounded text-xs font-mono max-h-32 overflow-auto whitespace-pre-wrap break-all">
              {content.length > 500 ? content.slice(0, 500) + '\n... (truncated)' : content}
            </pre>
          </div>
        )}
        {oldString && (
          <div>
            <span className="text-[11px] text-muted-foreground block mb-1">Replace:</span>
            <pre
              className="p-2 rounded text-xs font-mono max-h-24 overflow-auto whitespace-pre-wrap break-all border border-border/50"
              style={{
                backgroundColor: 'hsl(var(--destructive) / 0.08)',
                color: 'hsl(var(--destructive))',
              }}
            >
              {oldString.length > 200 ? oldString.slice(0, 200) + '\n... (truncated)' : oldString}
            </pre>
          </div>
        )}
        {newString && (
          <div>
            <span className="text-[11px] text-muted-foreground block mb-1">With:</span>
            <pre
              className="p-2 rounded text-xs font-mono max-h-24 overflow-auto whitespace-pre-wrap break-all bg-muted/40 border border-border/50"
              style={colorStyles.badge}
            >
              {newString.length > 200 ? newString.slice(0, 200) + '\n... (truncated)' : newString}
            </pre>
          </div>
        )}
      </div>
    );
  }

  if (toolName === 'Grep' || toolName === 'Glob') {
    const pattern = input.pattern as string | undefined;
    const path = input.path as string | undefined;
    const glob = input.glob as string | undefined;
    return (
      <div className="space-y-2">
        {pattern && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-muted-foreground">Pattern:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
              style={colorStyles.badge}
            >
              {pattern}
            </code>
          </div>
        )}
        {path && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground">Path:</span>
            <code className="bg-muted/50 border border-border/50 px-2 py-0.5 rounded text-xs font-mono">{path}</code>
          </div>
        )}
        {glob && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground">Glob:</span>
            <code className="bg-muted/50 border border-border/50 px-2 py-0.5 rounded text-xs font-mono">{glob}</code>
          </div>
        )}
      </div>
    );
  }

  // Task tool - display delegation information
  if (toolName === 'Task') {
    const description = input.description as string | undefined;
    const subagent = input.subagent as string | undefined;
    const subagentType = input.subagent_type as string | undefined;

    return (
      <div className="space-y-2">
        {description && (
          <div className="space-y-1">
            <span className="text-[11px] text-muted-foreground">Task:</span>
            <p className="text-xs text-foreground leading-relaxed">{description}</p>
          </div>
        )}
        {(subagent || subagentType) && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-muted-foreground">Delegating to:</span>
            {subagent && (
              <code
                className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
                style={colorStyles.badge}
              >
                {subagent}
              </code>
            )}
            {subagentType && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted/30 border border-border/50 text-muted-foreground">
                {subagentType}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }

  // WebFetch tool - display URL information
  if (toolName === 'WebFetch') {
    const url = input.url as string | undefined;
    const query = input.query as string | undefined;

    return (
      <div className="space-y-2">
        {url && (
          <div className="space-y-1">
            <span className="text-[11px] text-muted-foreground">Fetching from:</span>
            <code className="block text-xs font-mono bg-muted/50 border border-border/50 px-2 py-1.5 rounded break-all">
              {url}
            </code>
          </div>
        )}
        {query && (
          <div className="space-y-1">
            <span className="text-[11px] text-muted-foreground">Query:</span>
            <p className="text-xs text-foreground leading-relaxed">{query}</p>
          </div>
        )}
      </div>
    );
  }

  // WebSearch tool - display search query
  if (toolName === 'WebSearch') {
    const query = input.query as string | undefined;
    const url = input.url as string | undefined;

    return (
      <div className="space-y-2">
        {query && (
          <div className="space-y-1">
            <span className="text-[11px] text-muted-foreground">Searching for:</span>
            <p className="text-xs text-foreground leading-relaxed font-medium">"{query}"</p>
          </div>
        )}
        {url && (
          <div className="space-y-1">
            <span className="text-[11px] text-muted-foreground">Search engine:</span>
            <code className="text-xs font-mono bg-muted/50 border border-border/50 px-2 py-0.5 rounded">
              {url}
            </code>
          </div>
        )}
      </div>
    );
  }

  // AskUserQuestion tool - display questions and options in a readable format
  if (toolName === 'AskUserQuestion') {
    const questions = input.questions as Array<{
      question: string;
      header?: string;
      options?: Array<{
        label: string;
        description?: string;
      }>;
      multiSelect?: boolean;
    }> | undefined;

    if (!questions || questions.length === 0) {
      return (
        <div className="text-[11px] text-muted-foreground italic">
          No questions defined
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {questions.map((q, qIdx) => (
          <div key={qIdx} className="space-y-2">
            {q.header && (
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {q.header}
              </div>
            )}
            <div className="text-xs font-medium text-foreground">
              {q.question}
            </div>
            {q.options && q.options.length > 0 && (
              <div className="space-y-1.5 pl-2">
                {q.options.map((opt, oIdx) => (
                  <div
                    key={oIdx}
                    className="flex items-start gap-2 text-[11px]"
                  >
                    <span className="text-muted-foreground/60 select-none mt-0.5">
                      {String.fromCharCode(65 + oIdx)}.
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-foreground">
                        {opt.label}
                      </div>
                      {opt.description && (
                        <div className="text-[10px] text-muted-foreground mt-0.5 leading-snug">
                          {opt.description}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {q.multiSelect !== undefined && (
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted/50 border border-border/50">
                  {q.multiSelect ? 'Multiple selection' : 'Single selection'}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  // TodoWrite tool - display todos in a task list format
  if (toolName === 'TodoWrite') {
    const todos = input.todos as Array<{
      content: string;
      status?: string;
      activeForm?: string;
    }> | undefined;

    if (!todos || todos.length === 0) {
      return (
        <div className="text-[11px] text-muted-foreground italic">
          No todos defined
        </div>
      );
    }

    return (
      <div className="space-y-1.5">
        {todos.map((todo, idx) => {
          const isPending = !todo.status || todo.status === 'pending';
          return (
            <div
              key={idx}
              className="flex items-start gap-2 text-[11px] p-2 rounded bg-muted/20 border border-border/30"
            >
              <div className="flex items-center justify-center w-4 h-4 mt-0.5 shrink-0">
                {isPending ? (
                  <div className="w-3 h-3 rounded-full border-2 border-muted-foreground/40" />
                ) : (
                  <div className="w-3 h-3 rounded-full bg-green-500/80 flex items-center justify-center">
                    <svg className="w-2 h-2 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-foreground">
                  {todo.activeForm || todo.content}
                </div>
                {todo.activeForm && todo.activeForm !== todo.content && (
                  <div className="text-[10px] text-muted-foreground mt-0.5">
                    {todo.content}
                  </div>
                )}
              </div>
              {todo.status && (
                <span className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded shrink-0",
                  isPending
                    ? "bg-yellow-500/10 text-yellow-500 border border-yellow-500/20"
                    : "bg-green-500/10 text-green-500 border border-green-500/20"
                )}>
                  {todo.status}
                </span>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // Fallback to JSON display for other tools
  return (
    <pre className="bg-muted/40 border border-border/50 p-3 rounded text-xs font-mono overflow-auto max-h-64 whitespace-pre-wrap break-all">
      {JSON.stringify(input, null, 2)}
    </pre>
  );
}
