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

  const progressPercent = timeoutSeconds > 0 ? (remainingSeconds / timeoutSeconds) * 100 : 0;

  // Determine progress color based on remaining time percentage
  const getProgressColor = () => {
    if (progressPercent > 50) return 'bg-green-500';
    if (progressPercent > 25) return 'bg-yellow-500';
    return 'bg-red-500';
  };

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
      <DialogContent className="sm:max-w-2xl md:max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between pr-8">
            <span>Claude needs your input</span>
            <span className="text-sm font-normal text-muted-foreground tabular-nums">
              {remainingSeconds}s remaining
            </span>
          </DialogTitle>
        </DialogHeader>

        <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn('h-full transition-all duration-1000 ease-linear', getProgressColor())}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="text-sm text-muted-foreground text-center">
          {answeredCount} of {questions.length} questions answered
        </div>

        {questions.length > 0 && (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
            <TabsList className="w-full justify-start overflow-x-auto flex-shrink-0">
              {questions.map((q, idx) => (
                <TabsTrigger
                  key={idx}
                  value={String(idx)}
                  className="flex items-center gap-2 min-w-fit"
                >
                  {isQuestionAnswered(q) ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Circle className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className="truncate max-w-[120px]">
                    Q{idx + 1}
                  </span>
                </TabsTrigger>
              ))}
            </TabsList>

            <div className="flex-1 overflow-y-auto py-4">
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

        <DialogFooter className="gap-2 sm:gap-0 flex-shrink-0 border-t pt-4">
          <div className="flex items-center gap-2 mr-auto">
            <Button
              variant="outline"
              size="sm"
              disabled={activeTab === '0'}
              onClick={() => setActiveTab(String(Number(activeTab) - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={activeTab === String(questions.length - 1)}
              onClick={() => setActiveTab(String(Number(activeTab) + 1))}
            >
              Next
            </Button>
          </div>
          <Button variant="outline" onClick={closeModal}>
            Skip
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid}>
            Submit ({answeredCount}/{questions.length})
          </Button>
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
      <div className="space-y-4">
        <div className="space-y-1">
          <Label className="text-lg font-semibold">{question.question}</Label>
          <p className="text-sm text-muted-foreground">Select all that apply</p>
        </div>
        <div className="space-y-3 pl-1">
          {question.options.map((option, idx) => (
            <div key={idx} className="flex items-start space-x-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
              <Checkbox
                id={`${question.question}-${idx}`}
                checked={selectedValues.includes(option.value)}
                onCheckedChange={(checked) =>
                  handleCheckboxChange(option.value, checked as boolean)
                }
                className="mt-0.5"
              />
              <div className="flex flex-col flex-1">
                <Label
                  htmlFor={`${question.question}-${idx}`}
                  className="font-medium cursor-pointer"
                >
                  {option.value}
                </Label>
                {option.description && (
                  <span className="text-sm text-muted-foreground">{option.description}</span>
                )}
              </div>
            </div>
          ))}

          {/* Other option for multi-select */}
          <div className="flex items-start space-x-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
            <Checkbox
              id={`${question.question}-other`}
              checked={isOtherSelected}
              onCheckedChange={(checked) => handleOtherCheck(checked as boolean)}
              className="mt-0.5"
            />
            <div className="flex flex-col flex-1 space-y-2">
              <Label
                htmlFor={`${question.question}-other`}
                className="font-medium cursor-pointer"
              >
                Other
              </Label>
              {isOtherSelected && (
                <Input
                  placeholder="Enter your answer..."
                  value={otherText}
                  onChange={(e) => handleOtherTextChange(e.target.value)}
                  className="max-w-md"
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
    <div className="space-y-4">
      <div className="space-y-1">
        <Label className="text-lg font-semibold">{question.question}</Label>
        <p className="text-sm text-muted-foreground">Select one option</p>
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
        className="space-y-3 pl-1"
      >
        {question.options.map((option, idx) => (
          <div key={idx} className="flex items-start space-x-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
            <RadioGroupItem
              value={option.value}
              id={`${question.question}-${idx}`}
              className="mt-0.5"
            />
            <div className="flex flex-col flex-1">
              <Label
                htmlFor={`${question.question}-${idx}`}
                className="font-medium cursor-pointer"
              >
                {option.value}
              </Label>
              {option.description && (
                <span className="text-sm text-muted-foreground">{option.description}</span>
              )}
            </div>
          </div>
        ))}

        {/* Other option for single-select */}
        <div className="flex items-start space-x-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
          <RadioGroupItem
            value={OTHER_OPTION_VALUE}
            id={`${question.question}-other`}
            className="mt-0.5"
          />
          <div className="flex flex-col flex-1 space-y-2">
            <Label
              htmlFor={`${question.question}-other`}
              className="font-medium cursor-pointer"
            >
              Other
            </Label>
            {isOtherValue && (
              <Input
                placeholder="Enter your answer..."
                value={otherText}
                onChange={(e) => handleOtherTextChange(e.target.value)}
                className="max-w-md"
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
