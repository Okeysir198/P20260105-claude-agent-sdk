'use client';

import { useEffect, useCallback, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useQuestionStore } from '@/lib/store/question-store';
import type { Question } from '@/types';
import { cn } from '@/lib/utils';
import { Check, Circle } from 'lucide-react';

interface QuestionModalProps {
  onSubmit: (questionId: string, answers: Record<string, string | string[]>) => void;
}

const OTHER_OPTION_VALUE = '__other__';

export function QuestionModal({ onSubmit }: QuestionModalProps) {
  const {
    isOpen,
    questionId,
    questions,
    timeoutSeconds,
    remainingSeconds,
    answers,
    setAnswer,
    tick,
    closeModal,
  } = useQuestionStore();

  const [activeTab, setActiveTab] = useState('0');

  // Reset active tab when modal opens
  useEffect(() => {
    if (isOpen) {
      setActiveTab('0');
    }
  }, [isOpen]);

  // Countdown timer
  useEffect(() => {
    if (!isOpen) return;

    const interval = setInterval(() => {
      tick();
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, tick]);

  // Auto-close on timeout
  useEffect(() => {
    if (remainingSeconds === 0 && isOpen) {
      closeModal();
    }
  }, [remainingSeconds, isOpen, closeModal]);

  const handleSubmit = useCallback(() => {
    if (questionId) {
      onSubmit(questionId, answers);
      closeModal();
    }
  }, [questionId, answers, onSubmit, closeModal]);

  const handleSkip = useCallback(() => {
    if (questionId) {
      // Send empty answers to let agent know user skipped
      onSubmit(questionId, {});
      closeModal();
    }
  }, [questionId, onSubmit, closeModal]);

  const progressPercent = timeoutSeconds > 0 ? (remainingSeconds / timeoutSeconds) * 100 : 0;

  /**
   * Get progress bar color CSS variable based on remaining time percentage.
   */
  function getProgressColorVar(): string {
    if (progressPercent > 50) return '--progress-high';
    if (progressPercent > 25) return '--progress-medium';
    return '--progress-low';
  }

  // Check if a specific question is answered
  const isQuestionAnswered = (q: Question) => {
    const answer = answers[q.question];
    if (!answer) return false;
    if (q.allowMultiple) {
      const arr = answer as string[];
      return arr.length > 0;
    }
    return answer !== '' && answer !== OTHER_OPTION_VALUE;
  };

  // Validate all questions are answered
  const isValid = questions.every(isQuestionAnswered);

  // Count answered questions
  const answeredCount = questions.filter(isQuestionAnswered).length;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeModal()}>
      <DialogContent className="w-[95vw] sm:max-w-2xl md:max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="space-y-2 sm:space-y-0">
          <DialogTitle className="flex items-center justify-between pr-8 text-base sm:text-lg">
            <span className="truncate">Claude needs your input</span>
            <span className="text-xs sm:text-sm font-normal text-muted-foreground tabular-nums shrink-0 ml-2">
              {remainingSeconds}s remaining
            </span>
          </DialogTitle>
        </DialogHeader>

        <div className="relative h-3 sm:h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full transition-all duration-1000 ease-linear"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: `hsl(var(${getProgressColorVar()}))`,
            }}
          />
        </div>

        <div className="text-xs sm:text-sm text-muted-foreground text-center">
          {answeredCount} of {questions.length} questions answered
        </div>

        {questions.length > 0 && (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
            <TabsList className="w-full justify-start overflow-x-auto overflow-y-hidden flex-shrink-0 h-auto min-h-[44px] sm:min-h-0 gap-1 sm:gap-0 p-1 sm:p-0">
              {questions.map((q, idx) => (
                <TabsTrigger
                  key={idx}
                  value={String(idx)}
                  className="flex items-center gap-1.5 sm:gap-2 min-w-fit h-auto min-h-[40px] sm:min-h-0 px-3 sm:px-4 py-2 text-xs sm:text-sm"
                >
                  {isQuestionAnswered(q) ? (
                    <Check
                      className="h-3.5 w-3.5 sm:h-4 sm:w-4 shrink-0"
                      style={{ color: 'hsl(var(--progress-high))' }}
                    />
                  ) : (
                    <Circle className="h-3.5 w-3.5 sm:h-4 sm:w-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="truncate max-w-[80px] sm:max-w-[120px]">
                    Q{idx + 1}
                  </span>
                </TabsTrigger>
              ))}
            </TabsList>

            <div className="flex-1 overflow-y-auto py-2 sm:py-4 px-1 sm:px-0">
              {questions.map((question, idx) => (
                <TabsContent key={idx} value={String(idx)} className="m-0 h-full">
                  <QuestionItem
                    question={question}
                    value={answers[question.question]}
                    onChange={(value) => setAnswer(question.question, value)}
                  />
                </TabsContent>
              ))}
            </div>
          </Tabs>
        )}

        <DialogFooter className="gap-2 sm:gap-0 flex-shrink-0 border-t pt-3 sm:pt-4 flex-col sm:flex-row">
          <div className="flex items-center gap-2 w-full sm:w-auto sm:mr-auto order-3 sm:order-1">
            <Button
              variant="outline"
              size="sm"
              disabled={activeTab === '0'}
              onClick={() => setActiveTab(String(Number(activeTab) - 1))}
              className="flex-1 sm:flex-none h-10 sm:h-9"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={activeTab === String(questions.length - 1)}
              onClick={() => setActiveTab(String(Number(activeTab) + 1))}
              className="flex-1 sm:flex-none h-10 sm:h-9"
            >
              Next
            </Button>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto order-1 sm:order-2">
            <Button variant="outline" onClick={handleSkip} className="flex-1 sm:flex-none h-10 sm:h-9">
              Skip
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!isValid}
              className="flex-1 sm:flex-none h-10 sm:h-9 bg-foreground hover:bg-foreground/90 text-background dark:shadow-none dark:border dark:border-border"
            >
              Submit ({answeredCount}/{questions.length})
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface QuestionItemProps {
  question: Question;
  value: string | string[] | undefined;
  onChange: (value: string | string[]) => void;
}

function QuestionItem({ question, value, onChange }: QuestionItemProps) {
  const [otherText, setOtherText] = useState('');
  const [isOtherSelected, setIsOtherSelected] = useState(false);

  // Check if this is multi-select
  const isMultiSelect = question.allowMultiple === true;

  // Handle "Other" text change for single-select
  const handleOtherTextChange = (text: string) => {
    setOtherText(text);
    if (isMultiSelect) {
      // For multi-select with "Other"
      const currentValues = (value as string[]) || [];
      const withoutOther = currentValues.filter((v) => !v.startsWith('Other: '));
      if (text) {
        onChange([...withoutOther, `Other: ${text}`]);
      } else {
        onChange(withoutOther);
      }
    } else {
      // For single-select, set the custom text as the value
      if (text) {
        onChange(`Other: ${text}`);
      } else {
        onChange(OTHER_OPTION_VALUE);
      }
    }
  };

  if (isMultiSelect) {
    // Multi-select with checkboxes
    const selectedValues = (value as string[]) || [];

    const handleCheckboxChange = (optionValue: string, checked: boolean) => {
      if (checked) {
        onChange([...selectedValues, optionValue]);
      } else {
        onChange(selectedValues.filter((v) => v !== optionValue));
      }
    };

    const handleOtherCheck = (checked: boolean) => {
      setIsOtherSelected(checked);
      if (!checked) {
        // Remove any "Other: ..." values
        onChange(selectedValues.filter((v) => !v.startsWith('Other: ')));
        setOtherText('');
      }
    };

    return (
      <div className="space-y-3 sm:space-y-4">
        <div className="space-y-1">
          <Label className="text-base sm:text-lg font-semibold">{question.question}</Label>
          <p className="text-xs sm:text-sm text-muted-foreground">Select all that apply</p>
        </div>
        <div className="space-y-2 sm:space-y-3 pl-1">
          {question.options.map((option, idx) => (
            <div
              key={idx}
              className="flex items-start space-x-3 sm:space-x-3 p-3 sm:p-2 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer min-h-[52px] sm:min-h-0"
              onClick={() => {
                const checkbox = document.getElementById(`${question.question}-${idx}`) as HTMLInputElement;
                checkbox?.click();
              }}
            >
              <Checkbox
                id={`${question.question}-${idx}`}
                checked={selectedValues.includes(option.value)}
                onCheckedChange={(checked) =>
                  handleCheckboxChange(option.value, checked as boolean)
                }
                className="mt-0.5 h-5 w-5 sm:h-4 sm:w-4"
              />
              <div className="flex flex-col flex-1 min-w-0">
                <Label
                  htmlFor={`${question.question}-${idx}`}
                  className="font-medium cursor-pointer text-sm sm:text-base"
                >
                  {option.value}
                </Label>
                {option.description && (
                  <span className="text-xs sm:text-sm text-muted-foreground line-clamp-2">
                    {option.description}
                  </span>
                )}
              </div>
            </div>
          ))}

          {/* Other option for multi-select */}
          <div className="flex items-start space-x-3 sm:space-x-3 p-3 sm:p-2 rounded-lg hover:bg-muted/50 transition-colors min-h-[52px] sm:min-h-0">
            <Checkbox
              id={`${question.question}-other`}
              checked={isOtherSelected}
              onCheckedChange={(checked) => handleOtherCheck(checked as boolean)}
              className="mt-0.5 h-5 w-5 sm:h-4 sm:w-4"
            />
            <div className="flex flex-col flex-1 space-y-2 min-w-0">
              <Label
                htmlFor={`${question.question}-other`}
                className="font-medium cursor-pointer text-sm sm:text-base"
              >
                Other
              </Label>
              {isOtherSelected && (
                <Input
                  placeholder="Enter your answer..."
                  value={otherText}
                  onChange={(e) => handleOtherTextChange(e.target.value)}
                  className="max-w-md h-10"
                  autoFocus
                />
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Single-select with radio buttons
  const selectedValue = value as string | undefined;
  const isOtherValue =
    selectedValue === OTHER_OPTION_VALUE || selectedValue?.startsWith('Other: ');

  return (
    <div className="space-y-3 sm:space-y-4">
      <div className="space-y-1">
        <Label className="text-base sm:text-lg font-semibold">{question.question}</Label>
        <p className="text-xs sm:text-sm text-muted-foreground">Select one option</p>
      </div>
      <RadioGroup
        value={isOtherValue ? OTHER_OPTION_VALUE : selectedValue || ''}
        onValueChange={(val) => {
          if (val === OTHER_OPTION_VALUE) {
            setIsOtherSelected(true);
            onChange(OTHER_OPTION_VALUE);
          } else {
            setIsOtherSelected(false);
            setOtherText('');
            onChange(val);
          }
        }}
        className="space-y-2 sm:space-y-3 pl-1"
      >
        {question.options.map((option, idx) => (
          <div
            key={idx}
            className="flex items-start space-x-3 sm:space-x-3 p-3 sm:p-2 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer min-h-[52px] sm:min-h-0"
            onClick={() => {
              const radio = document.getElementById(`${question.question}-${idx}`) as HTMLInputElement;
              radio?.click();
            }}
          >
            <RadioGroupItem
              value={option.value}
              id={`${question.question}-${idx}`}
              className="mt-0.5 h-5 w-5 sm:h-4 sm:w-4"
            />
            <div className="flex flex-col flex-1 min-w-0">
              <Label
                htmlFor={`${question.question}-${idx}`}
                className="font-medium cursor-pointer text-sm sm:text-base"
              >
                {option.value}
              </Label>
              {option.description && (
                <span className="text-xs sm:text-sm text-muted-foreground line-clamp-2">
                  {option.description}
                </span>
              )}
            </div>
          </div>
        ))}

        {/* Other option for single-select */}
        <div className="flex items-start space-x-3 sm:space-x-3 p-3 sm:p-2 rounded-lg hover:bg-muted/50 transition-colors min-h-[52px] sm:min-h-0">
          <RadioGroupItem
            value={OTHER_OPTION_VALUE}
            id={`${question.question}-other`}
            className="mt-0.5 h-5 w-5 sm:h-4 sm:w-4"
          />
          <div className="flex flex-col flex-1 space-y-2 min-w-0">
            <Label
              htmlFor={`${question.question}-other`}
              className="font-medium cursor-pointer text-sm sm:text-base"
            >
              Other
            </Label>
            {isOtherValue && (
              <Input
                placeholder="Enter your answer..."
                value={otherText}
                onChange={(e) => handleOtherTextChange(e.target.value)}
                className="max-w-md h-10"
                autoFocus
              />
            )}
          </div>
        </div>
      </RadioGroup>
    </div>
  );
}

export default QuestionModal;
