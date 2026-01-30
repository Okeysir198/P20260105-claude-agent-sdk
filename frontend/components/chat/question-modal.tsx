'use client';

import { useEffect, useCallback, useState, useRef } from 'react';
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
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useQuestionStore } from '@/lib/store/question-store';
import type { UIQuestion, UIQuestionOption } from '@/types';
import { Check, Circle } from 'lucide-react';

const OTHER_OPTION_VALUE = '__other__';

interface QuestionModalProps {
  onSubmit: (questionId: string, answers: Record<string, string | string[]>) => void;
}

// Helper: Check if device supports hover (non-touch)
function useSupportsHover() {
  const [supportsHover, setSupportsHover] = useState(() => {
    if (typeof window === 'undefined') return true;
    return window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia('(hover: hover) and (pointer: fine)');
    const handler = (e: MediaQueryListEvent) => setSupportsHover(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return supportsHover;
}

// Helper: Get progress color CSS variable
function getProgressColorVar(progressPercent: number): string {
  if (progressPercent > 50) return '--progress-high';
  if (progressPercent > 25) return '--progress-medium';
  return '--progress-low';
}

// Helper: Check if a question is answered
function isQuestionAnswered(q: UIQuestion, answers: Record<string, string | string[]>): boolean {
  const answer = answers[q.question];
  if (!answer) return false;
  if (q.allowMultiple) {
    return (answer as string[]).length > 0;
  }
  return answer !== '' && answer !== OTHER_OPTION_VALUE;
}

// Helper: Format option ID
function getOptionId(question: UIQuestion, index: number, isOther = false): string {
  return isOther ? `${question.question}-other` : `${question.question}-${index}`;
}

// Component: Progress bar
function ProgressBar({ remaining, total }: { remaining: number; total: number }) {
  const percent = total > 0 ? (remaining / total) * 100 : 0;

  return (
    <div className="relative h-3 sm:h-2 w-full overflow-hidden rounded-full bg-muted">
      <div
        className="h-full transition-all duration-1000 ease-linear"
        style={{
          width: `${percent}%`,
          backgroundColor: `hsl(var(${getProgressColorVar(percent)}))`,
        }}
      />
    </div>
  );
}

// Component: Tab trigger with check/circle indicator
function QuestionTabTrigger({
  question,
  index,
  answers,
}: {
  question: UIQuestion;
  index: number;
  answers: Record<string, string | string[]>;
}) {
  const answered = isQuestionAnswered(question, answers);

  return (
    <TabsTrigger
      value={String(index)}
      className="flex items-center gap-1.5 sm:gap-2 min-w-fit h-auto min-h-[40px] sm:min-h-0 px-3 sm:px-4 py-2 text-xs sm:text-sm"
    >
      {answered ? (
        <Check
          className="h-3.5 w-3.5 sm:h-4 sm:w-4 shrink-0"
          style={{ color: 'hsl(var(--progress-high))' }}
        />
      ) : (
        <Circle className="h-3.5 w-3.5 sm:h-4 sm:w-4 shrink-0 text-muted-foreground" />
      )}
      <span className="truncate max-w-[80px] sm:max-w-[120px]">Q{index + 1}</span>
    </TabsTrigger>
  );
}

// Component: Single option row (shared between radio and checkbox)
interface OptionRowProps {
  question: UIQuestion;
  option: UIQuestionOption;
  index: number;
  selected?: boolean;
  onSelect: () => void;
  inputElement: React.ReactNode;
}

function OptionRow({ question, option, index, onSelect, inputElement }: OptionRowProps) {
  const id = getOptionId(question, index);

  return (
    <div
      className="flex items-start space-x-3 sm:space-x-3 p-3 sm:p-2 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer min-h-[52px] sm:min-h-0"
      onClick={onSelect}
    >
      {inputElement}
      <div className="flex flex-col flex-1 min-w-0">
        <Label htmlFor={id} className="font-medium cursor-pointer text-sm sm:text-base">
          {option.value}
        </Label>
        {option.description && (
          <span className="text-xs sm:text-sm text-muted-foreground line-clamp-2">
            {option.description}
          </span>
        )}
      </div>
    </div>
  );
}

// Component: "Other" option with text input
interface OtherOptionProps {
  question: UIQuestion;
  selected: boolean;
  text: string;
  onTextChange: (text: string) => void;
  inputElement: React.ReactNode;
  supportsHover: boolean;
}

function OtherOption({
  question,
  selected,
  text,
  onTextChange,
  inputElement,
  supportsHover,
}: OtherOptionProps) {
  const id = getOptionId(question, -1, true);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (selected && supportsHover && inputRef.current) {
      inputRef.current.focus();
    }
  }, [selected, supportsHover]);

  return (
    <div className="flex items-start space-x-3 sm:space-x-3 p-3 sm:p-2 rounded-lg hover:bg-muted/50 transition-colors min-h-[52px] sm:min-h-0">
      {inputElement}
      <div className="flex flex-col flex-1 space-y-2 min-w-0">
        <Label htmlFor={id} className="font-medium cursor-pointer text-sm sm:text-base">
          Other
        </Label>
        {selected && (
          <Textarea
            ref={inputRef}
            id={id}
            placeholder="Enter your answer..."
            value={text}
            onChange={(e) => onTextChange(e.target.value)}
            className="max-w-md min-h-[80px] resize-y transition-all duration-200"
          />
        )}
      </div>
    </div>
  );
}

// Component: Multi-select question
function MultiSelectQuestion({
  question,
  value,
  onChange,
  supportsHover,
}: {
  question: UIQuestion;
  value: string[] | undefined;
  onChange: (value: string[]) => void;
  supportsHover: boolean;
}) {
  const selectedValues = value || [];

  // Initialize other text from existing value
  const getOtherText = () => {
    const otherValue = selectedValues.find((v) => v.startsWith('Other: '));
    return otherValue ? otherValue.replace('Other: ', '') : '';
  };

  const [otherText, setOtherText] = useState(getOtherText);
  const [isOtherSelected, setIsOtherSelected] = useState(() =>
    selectedValues.some((v) => v.startsWith('Other: '))
  );

  const handleCheckboxChange = (optionValue: string, checked: boolean) => {
    onChange(
      checked
        ? [...selectedValues, optionValue]
        : selectedValues.filter((v) => v !== optionValue)
    );
  };

  const handleOtherCheck = (checked: boolean) => {
    setIsOtherSelected(checked);
    if (!checked) {
      onChange(selectedValues.filter((v) => !v.startsWith('Other: ')));
      setOtherText('');
    }
  };

  const handleOtherTextChange = (text: string) => {
    setOtherText(text);
    const withoutOther = selectedValues.filter((v) => !v.startsWith('Other: '));
    onChange(text ? [...withoutOther, `Other: ${text}`] : withoutOther);
  };

  return (
    <div className="space-y-3 sm:space-y-4">
      <div className="space-y-1">
        <Label className="text-base sm:text-lg font-semibold">{question.question}</Label>
        <p className="text-xs sm:text-sm text-muted-foreground">Select all that apply</p>
      </div>
      <div className="space-y-2 sm:space-y-3 pl-1">
        {question.options.map((option, idx) => {
          const id = getOptionId(question, idx);
          return (
            <OptionRow
              key={idx}
              question={question}
              option={option}
              index={idx}
              selected={selectedValues.includes(option.value)}
              onSelect={() => {
                const checkbox = document.getElementById(id) as HTMLInputElement;
                checkbox?.click();
              }}
              inputElement={
                <Checkbox
                  id={id}
                  checked={selectedValues.includes(option.value)}
                  onCheckedChange={(checked) =>
                    handleCheckboxChange(option.value, checked as boolean)
                  }
                  className="mt-0.5 h-5 w-5 sm:h-4 sm:w-4"
                />
              }
            />
          );
        })}

        <OtherOption
          question={question}
          selected={isOtherSelected}
          text={otherText}
          onTextChange={handleOtherTextChange}
          supportsHover={supportsHover}
          inputElement={
            <Checkbox
              id={getOptionId(question, -1, true)}
              checked={isOtherSelected}
              onCheckedChange={(checked) => handleOtherCheck(checked as boolean)}
              className="mt-0.5 h-5 w-5 sm:h-4 sm:w-4"
            />
          }
        />
      </div>
    </div>
  );
}

// Component: Single-select question
function SingleSelectQuestion({
  question,
  value,
  onChange,
  supportsHover,
}: {
  question: UIQuestion;
  value: string | undefined;
  onChange: (value: string) => void;
  supportsHover: boolean;
}) {
  // Initialize other text from existing value
  const getOtherText = () => {
    if (value?.startsWith('Other: ')) {
      return value.replace('Other: ', '');
    }
    return '';
  };

  const [otherText, setOtherText] = useState(getOtherText);
  const isOtherValue = Boolean(value === OTHER_OPTION_VALUE || value?.startsWith('Other: '));

  const handleValueChange = (val: string) => {
    if (val === OTHER_OPTION_VALUE) {
      setOtherText('');
      onChange(OTHER_OPTION_VALUE);
    } else {
      setOtherText('');
      onChange(val);
    }
  };

  const handleOtherTextChange = (text: string) => {
    setOtherText(text);
    onChange(text ? `Other: ${text}` : OTHER_OPTION_VALUE);
  };

  return (
    <div className="space-y-3 sm:space-y-4">
      <div className="space-y-1">
        <Label className="text-base sm:text-lg font-semibold">{question.question}</Label>
        <p className="text-xs sm:text-sm text-muted-foreground">Select one option</p>
      </div>
      <RadioGroup
        value={isOtherValue ? OTHER_OPTION_VALUE : value || ''}
        onValueChange={handleValueChange}
        className="space-y-2 sm:space-y-3 pl-1"
      >
        {question.options.map((option, idx) => {
          const id = getOptionId(question, idx);
          return (
            <OptionRow
              key={idx}
              question={question}
              option={option}
              index={idx}
              selected={value === option.value}
              onSelect={() => {
                const radio = document.getElementById(id) as HTMLInputElement;
                radio?.click();
              }}
              inputElement={
                <RadioGroupItem value={option.value} id={id} className="mt-0.5 h-5 w-5 sm:h-4 sm:w-4" />
              }
            />
          );
        })}

        <OtherOption
          question={question}
          selected={isOtherValue}
          text={otherText}
          onTextChange={handleOtherTextChange}
          supportsHover={supportsHover}
          inputElement={
            <RadioGroupItem
              value={OTHER_OPTION_VALUE}
              id={getOptionId(question, -1, true)}
              className="mt-0.5 h-5 w-5 sm:h-4 sm:w-4"
            />
          }
        />
      </RadioGroup>
    </div>
  );
}

// Component: Question item (router between multi and single select)
function QuestionItem({
  question,
  value,
  onChange,
}: {
  question: UIQuestion;
  value: string | string[] | undefined;
  onChange: (value: string | string[]) => void;
}) {
  const supportsHover = useSupportsHover();

  if (question.allowMultiple) {
    return (
      <MultiSelectQuestion
        question={question}
        value={value as string[] | undefined}
        onChange={(v) => onChange(v)}
        supportsHover={supportsHover}
      />
    );
  }

  return (
    <SingleSelectQuestion
      question={question}
      value={value as string | undefined}
      onChange={(v) => onChange(v)}
      supportsHover={supportsHover}
    />
  );
}

// Main modal component
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
    submitAnswers,
  } = useQuestionStore();

  // Use a key that changes when the question ID changes to reset tab state
  const tabsKey = questionId || 'closed';
  const [activeTab, setActiveTab] = useState('0');

  // Countdown timer
  useEffect(() => {
    if (!isOpen) return;

    const interval = setInterval(tick, 1000);
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
      // Store answers locally for immediate display
      submitAnswers(questionId, answers);
      onSubmit(questionId, answers);
      closeModal();
    }
  }, [questionId, answers, onSubmit, closeModal, submitAnswers]);

  const handleSkip = useCallback(() => {
    if (questionId) {
      // Store empty answers for skip
      submitAnswers(questionId, {});
      onSubmit(questionId, {});
      closeModal();
    }
  }, [questionId, onSubmit, closeModal, submitAnswers]);

  const answeredCount = questions.filter((q) => isQuestionAnswered(q, answers)).length;
  const isValid = answeredCount === questions.length;
  const currentTabNum = Number(activeTab);
  const hasPrev = currentTabNum > 0;
  const hasNext = currentTabNum < questions.length - 1;

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

        <ProgressBar remaining={remainingSeconds} total={timeoutSeconds} />

        <div className="text-xs sm:text-sm text-muted-foreground text-center">
          {answeredCount} of {questions.length} questions answered
        </div>

        {questions.length > 0 && (
          <Tabs
            key={tabsKey}
            value={activeTab}
            onValueChange={setActiveTab}
            className="flex-1 overflow-hidden flex flex-col"
          >
            <TabsList className="w-full justify-start overflow-x-auto overflow-y-hidden flex-shrink-0 h-auto min-h-[44px] sm:min-h-0 gap-1 sm:gap-0 p-1 sm:p-0">
              {questions.map((q, idx) => (
                <QuestionTabTrigger
                  key={idx}
                  question={q}
                  index={idx}
                  answers={answers}
                />
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
              disabled={!hasPrev}
              onClick={() => setActiveTab(String(currentTabNum - 1))}
              className="flex-1 sm:flex-none h-10 sm:h-9"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasNext}
              onClick={() => setActiveTab(String(currentTabNum + 1))}
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

export default QuestionModal;
