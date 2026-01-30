'use client';

import { useState, useEffect, useMemo } from 'react';
import type { ChatMessage } from '@/types';
import { cn, formatTime } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  MessageSquare,
  Check,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { RunningIndicator } from './tool-status-badge';
import { useQuestionStore } from '@/lib/store/question-store';

interface AskUserQuestionDisplayProps {
  message: ChatMessage;
  isRunning: boolean;
  answer?: string;
}

/**
 * Display for AskUserQuestion - collapsible with tabbed questions and answer
 */
export function AskUserQuestionDisplay({
  message,
  isRunning,
  answer,
}: AskUserQuestionDisplayProps) {
  const [activeTab, setActiveTab] = useState(0);
  // Subscribe to submittedAnswers to trigger re-render when answers are submitted
  const submittedAnswers = useQuestionStore((s) => s.submittedAnswers);

  // Safely extract and validate questions array
  const rawQuestions = message.toolInput?.questions;
  const questions = Array.isArray(rawQuestions)
    ? (rawQuestions as Array<{
        question: string;
        header?: string;
        options?: Array<{ label: string; description?: string }>;
        multiSelect?: boolean;
      }>)
    : undefined;

  // Parse the answer to extract user selections - prioritize submitted answer for immediate display
  const parsedAnswers = useMemo(() => {
    // Use message.id as the key - this matches the questionId from the WebSocket event
    const msgId = message.id;
    // First try to get the locally submitted answer (immediate display)
    const submitted = submittedAnswers[msgId];
    if (submitted && Object.keys(submitted).length > 0) {
      return submitted;
    }
    // Fall back to the result from backend
    return answer ? parseAnswerContent(answer) : null;
  }, [answer, message.id, submittedAnswers]);

  const questionCount = questions?.length ?? 0;
  const hasAnswer = !!parsedAnswers && Object.keys(parsedAnswers).length > 0;

  // Default: expanded when waiting for answer, collapsed when answered
  const [expanded, setExpanded] = useState(!hasAnswer);

  // Sync expanded state when answer arrives
  useEffect(() => {
    if (hasAnswer) {
      setExpanded(false);
    }
  }, [hasAnswer]);

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

  const statusText = hasAnswer ? 'answered' : 'waiting for response';
  const detailsId = `question-details-${message.toolUseId || message.timestamp}`;

  return (
    <div
      className="group flex gap-2 sm:gap-3 py-1.5 px-2 sm:px-4"
      role="article"
      aria-label={`User question with ${questionCount} ${questionCount === 1 ? 'question' : 'questions'}, status: ${statusText}`}
    >
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border',
          isRunning && 'animate-pulse'
        )}
        style={{ color: 'hsl(var(--tool-question))' }}
        aria-hidden="true"
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : hasAnswer ? (
          <Check className="h-3.5 w-3.5" />
        ) : (
          <MessageSquare className="h-3.5 w-3.5" />
        )}
      </div>
      <div className="min-w-0 flex-1 overflow-hidden" aria-live="polite">
        <Card
          className="overflow-hidden rounded-lg shadow-sm w-full md:max-w-2xl bg-muted/30 border-l-2"
          style={{ borderLeftColor: 'hsl(var(--tool-question))' }}
        >
          {/* Header - clickable to expand/collapse */}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start rounded-none px-2 sm:px-3 py-2 text-xs hover:bg-muted/50 h-auto min-h-[40px] sm:min-h-[36px] border-b border-border/50"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            aria-controls={detailsId}
          >
            <div className="flex items-center gap-2 w-full">
              {expanded ? (
                <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              )}
              <span className="font-medium text-foreground">AskUserQuestion</span>
              <span
                className="text-xs sm:text-[10px] px-1.5 py-0.5 rounded border"
                style={{
                  backgroundColor: hasAnswer
                    ? 'hsl(var(--progress-high) / 0.1)'
                    : 'hsl(var(--tool-question) / 0.1)',
                  color: hasAnswer ? 'hsl(var(--progress-high))' : 'hsl(var(--tool-question))',
                  borderColor: hasAnswer
                    ? 'hsl(var(--progress-high) / 0.2)'
                    : 'hsl(var(--tool-question) / 0.2)',
                }}
              >
                {hasAnswer ? 'Answered' : 'Waiting'}
              </span>
              {!expanded && getSummary() && (
                <>
                  <span className="text-muted-foreground/60">:</span>
                  <span className="text-muted-foreground/80 font-normal text-xs sm:text-[11px] truncate">
                    {getSummary()}
                  </span>
                </>
              )}
              {/* Status indicator */}
              <span className="ml-auto flex items-center gap-1.5 shrink-0" role="status">
                {hasAnswer ? (
                  <span aria-label="Question answered">
                    <CheckCircle2 className="h-4 w-4 text-status-success" aria-hidden="true" />
                    <span className="sr-only">Answered</span>
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-status-warning" aria-label="Waiting for user response">
                    <Clock className="h-4 w-4" aria-hidden="true" />
                    <span className="text-xs sm:text-[10px] font-medium">Waiting</span>
                  </span>
                )}
              </span>
            </div>
          </Button>

          {/* Expanded content with smooth transition */}
          <div
            className={cn(
              "grid transition-all duration-200 ease-out",
              expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            )}
            id={detailsId}
          >
            <div className="overflow-hidden">
              {/* Question tabs */}
              {questionCount > 0 && (
                <QuestionTabs
                  questions={questions}
                  activeTab={activeTab}
                  setActiveTab={setActiveTab}
                  parsedAnswers={parsedAnswers}
                />
              )}

              {/* Question content */}
              <div
                className="p-3 bg-background/50"
                role="tabpanel"
                id={`question-panel-${activeTab}`}
                aria-labelledby={`question-tab-${activeTab}`}
              >
                {!questions || questions.length === 0 ? (
                  <div className="text-[11px] text-muted-foreground italic">
                    No questions defined
                  </div>
                ) : (
                  <QuestionContent
                    question={questions[activeTab]}
                    answer={parsedAnswers?.[questions[activeTab]?.question]}
                  />
                )}
              </div>
            </div>
          </div>
        </Card>
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs sm:text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}

interface QuestionTabsProps {
  questions: Array<{
    question: string;
    header?: string;
    options?: Array<{ label: string; description?: string }>;
    multiSelect?: boolean;
  }> | undefined;
  activeTab: number;
  setActiveTab: (tab: number) => void;
  parsedAnswers: Record<string, string | string[]> | null;
}

/**
 * Tab navigation for multiple questions
 */
function QuestionTabs({ questions, activeTab, setActiveTab, parsedAnswers }: QuestionTabsProps) {
  const questionCount = questions?.length ?? 0;

  return (
    <div className="border-b-[3px] border-border bg-muted/20" role="tablist" aria-label="Questions">
      <div className="px-3 pt-2">
        <div className="flex items-end gap-3">
          <span className="text-xs sm:text-[10px] font-medium text-muted-foreground uppercase tracking-wider shrink-0 pb-1.5" aria-hidden="true">
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
                    role="tab"
                    aria-selected={isActive}
                    aria-controls={`question-panel-${idx}`}
                    id={`question-tab-${idx}`}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium transition-colors whitespace-nowrap rounded-t-md -mb-[3px] min-h-[36px] sm:min-h-0',
                      isActive
                        ? 'bg-background border-[3px] border-b-0 border-primary text-foreground'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                    )}
                    aria-label={`Question ${idx + 1}: ${q.header || q.question.slice(0, 30)}${isAnswered ? ', answered' : ''}`}
                  >
                    {isAnswered ? (
                      <Check className="h-3.5 w-3.5 text-status-success" aria-hidden="true" />
                    ) : (
                      <span className="w-5 h-5 rounded-full bg-muted border border-border flex items-center justify-center text-[10px] font-bold" aria-hidden="true">
                        {idx + 1}
                      </span>
                    )}
                    <span className="max-w-[60px] sm:max-w-[100px] truncate">
                      {q.header || `Q${idx + 1}`}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <span className="text-xs sm:text-[10px] text-muted-foreground pb-1.5">1 of 1</span>
          )}
        </div>
      </div>
    </div>
  );
}

interface QuestionContentProps {
  question: {
    question: string;
    header?: string;
    options?: Array<{ label: string; description?: string }>;
    multiSelect?: boolean;
  };
  answer?: string | string[];
}

/**
 * Content for a single question with options and user answer
 */
function QuestionContent({ question, answer }: QuestionContentProps) {
  const answers = Array.isArray(answer) ? answer : answer ? [answer] : [];

  return (
    <div className="space-y-3">
      {/* Question text with optional header */}
      <div>
        {question.header && (
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mr-2">
            {question.header}:
          </span>
        )}
        <span className="text-xs text-foreground">{question.question}</span>
      </div>
      {/* Options - compact list with green highlight for selected */}
      {question.options && question.options.length > 0 && (
        <div className="space-y-0.5 pl-1">
          {question.options.map((opt, oIdx) => {
            const isSelected = isOptionSelected(opt.label, answers);
            return (
              <div
                key={oIdx}
                className={cn(
                  'flex items-center gap-2 text-[11px] px-2 py-1.5 rounded transition-colors',
                  isSelected
                    ? 'bg-green-50 dark:bg-green-950/30 text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {isSelected ? (
                  <Check className="h-3.5 w-3.5 text-green-600 dark:text-green-400 shrink-0" />
                ) : (
                  <span className="w-3.5 h-3.5 flex items-center justify-center text-[9px] font-medium text-muted-foreground/50 shrink-0">
                    {String.fromCharCode(65 + oIdx)}
                  </span>
                )}
                <span className={cn('truncate', isSelected && 'font-medium')}>{opt.label}</span>
                {opt.description && (
                  <span className="text-[10px] text-muted-foreground/70 truncate hidden sm:inline">
                    - {opt.description}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
      {/* Free-text answers - show as highlighted badge */}
      {!question.options || question.options.length === 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {answers.map((ans, idx) => (
            <span
              key={idx}
              className="text-[11px] px-2.5 py-1.5 rounded-md bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 font-medium shadow-sm max-w-full break-words"
            >
              {ans}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Parse the answer content from tool_result to extract user selections
 */
function parseAnswerContent(content: string): Record<string, string | string[]> | null {
  try {
    const parsed = JSON.parse(content);
    if (typeof parsed === 'object' && parsed !== null) {
      return parsed;
    }
  } catch {
    const result: Record<string, string | string[]> = {};
    const selectMatch = content.match(/(?:selected|answer|chose|picked):\s*(.+)/i);
    if (selectMatch) {
      result['_answer'] = selectMatch[1].trim();
      return result;
    }
    if (content.trim()) {
      result['_answer'] = content.trim();
      return result;
    }
  }
  return null;
}

/**
 * Check if an option is selected based on the answer strings
 * Handles various formats: exact match, "Other: text", partial matches
 */
function isOptionSelected(optionLabel: string, answers: string[]): boolean {
  return answers.some((answer) => {
    // Exact match
    if (answer === optionLabel) return true;

    // Handle "Other: custom text" format
    if (answer.startsWith('Other: ') && optionLabel === 'Other') return true;

    // Handle case where answer includes the option label
    if (answer.includes(optionLabel)) {
      // Make sure it's not a partial match of a longer word
      const words = answer.split(/\s+/);
      if (words.some((w) => w === optionLabel)) return true;
    }

    // Handle "Other: value" format more generally
    if (optionLabel.toLowerCase() === 'other' && answer.toLowerCase().startsWith('other:')) {
      return true;
    }

    return false;
  });
}
