'use client';

import { useState } from 'react';
import type { ChatMessage } from '@/types';
import { Loader2 } from 'lucide-react';
import { extractText } from '@/lib/content-utils';
import { getToolIcon, getToolColorStyles, getToolSummary } from '@/lib/tool-config';
import {
  ToolCard,
  ToolInputDisplay,
  ToolResultDisplay,
  type ToolStatus,
} from './tools';
import { TodoWriteDisplay } from './tools/todo-write-display';
import { EnterPlanModeDisplay, ExitPlanModeDisplay } from './tools/plan-mode-display';
import { AskUserQuestionDisplay } from './tools/ask-user-question-display';

function deriveToolStatus(
  isRunning: boolean,
  hasResult: boolean,
  isInterrupted: boolean,
  isError: boolean | undefined,
): ToolStatus {
  if (isRunning) return 'running';
  if (!hasResult) return 'pending';
  if (isInterrupted) return 'interrupted';
  if (isError) return 'error';
  return 'completed';
}

interface ToolUseMessageProps {
  message: ChatMessage;
  isRunning?: boolean;
  result?: ChatMessage;
}

/**
 * Main component for rendering tool use messages.
 * Delegates to specialized display components for specific tools.
 */
export function ToolUseMessage({ message, isRunning = false, result }: ToolUseMessageProps) {
  const [expanded, setExpanded] = useState(false);

  const toolName = message.toolName || '';
  const ToolIcon = getToolIcon(toolName);
  const colorStyles = getToolColorStyles(toolName);
  const summary = getToolSummary(toolName, message.toolInput);
  const hasResult = !!result;
  const isError = result?.isError;

  // Check if this is an interrupted tool result
  const resultContent = result ? extractText(result.content) : '';
  const isInterrupted = resultContent?.includes('[Request interrupted by user]') ||
                        resultContent?.includes('[Request interrupted by user for tool use]');

  const status: ToolStatus = deriveToolStatus(isRunning, hasResult, isInterrupted, isError);

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
    return <EnterPlanModeDisplay message={message} isRunning={isRunning} />;
  }

  // Special rendering for ExitPlanMode - always visible plan summary
  if (toolName === 'ExitPlanMode') {
    return <ExitPlanModeDisplay message={message} isRunning={isRunning} />;
  }

  // Special rendering for AskUserQuestion - always visible with tabs and answer
  if (toolName === 'AskUserQuestion') {
    return (
      <AskUserQuestionDisplay
        message={message}
        isRunning={isRunning}
        answer={result ? extractText(result.content) : undefined}
      />
    );
  }

  // Standard collapsible tool card
  return (
    <ToolCard
      toolName={toolName}
      ToolIcon={ToolIcon}
      color={colorStyles.iconText?.color}
      status={status}
      isExpanded={expanded}
      onToggle={() => setExpanded(!expanded)}
      summary={summary}
      timestamp={message.timestamp}
      isRunning={isRunning}
      toolId={message.toolUseId || String(message.timestamp)}
    >
      {/* Tool Input */}
      {message.toolInput && (
        <div className="p-2 sm:p-3 border-b border-border/30">
          <div className="text-xs sm:text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5 sm:mb-2">
            Input
          </div>
          <ToolInputDisplay toolName={toolName} input={message.toolInput} />
        </div>
      )}

      {/* Tool Result */}
      {hasResult && (
        <ToolResultSection content={extractText(result.content)} isError={isError} toolName={toolName} />
      )}

      {/* Loading state */}
      {isRunning && !hasResult && (
        <div className="p-2 sm:p-3 flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span className="text-xs sm:text-[11px]">Waiting for result...</span>
        </div>
      )}
    </ToolCard>
  );
}

// --- Sub-components ---

interface ToolResultSectionProps {
  content: string;
  isError?: boolean;
  toolName?: string;
}

/**
 * Displays the tool result section with proper styling
 */
function ToolResultSection({ content, isError, toolName }: ToolResultSectionProps) {
  return (
    <div className="p-2 sm:p-3" role="region" aria-label={isError ? 'Tool error output' : 'Tool output'}>
      <div className="flex items-center gap-2 mb-1.5 sm:mb-2">
        <span className="text-xs sm:text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
          Output
        </span>
        {isError && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-destructive/10 text-destructive border border-destructive/20" role="alert">
            Error
          </span>
        )}
      </div>
      <ToolResultDisplay content={content} isError={isError} toolName={toolName} />
    </div>
  );
}

