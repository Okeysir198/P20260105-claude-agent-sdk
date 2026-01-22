'use client';

/**
 * Inline Suggestions Component
 *
 * 2026 Design Pattern: Contextual Inline Suggestions
 *
 * Provides contextual suggestion chips that appear inline during conversations.
 * Helps users discover capabilities and continue conversations naturally.
 *
 * Features:
 * - Staggered chip animations
 * - Hover/tap micro-interactions
 * - Context-aware suggestions
 * - Progressive disclosure
 *
 * @module components/animations/inline-suggestions
 */

import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { suggestionChipVariants, suggestionsContainerVariants } from '@/lib/animations';

export interface Suggestion {
  id: string;
  text: string;
  icon?: React.ReactNode;
  description?: string;
}

interface InlineSuggestionsProps {
  /** Array of suggestions to display */
  suggestions: Suggestion[];
  /** Callback when suggestion is clicked */
  onSelect: (suggestion: Suggestion) => void;
  /** Whether suggestions are visible */
  isVisible: boolean;
  /** Maximum suggestions to show */
  maxSuggestions?: number;
  /** Additional CSS classes */
  className?: string;
  /** Variant style */
  variant?: 'chips' | 'list' | 'cards';
}

/**
 * Inline suggestions component with animated chips
 *
 * @example
 * ```tsx
 * const suggestions = [
 *   { id: '1', text: 'Explain this code' },
 *   { id: '2', text: 'Add error handling' },
 * ];
 *
 * <InlineSuggestions
 *   suggestions={suggestions}
 *   onSelect={(s) => console.log(s.text)}
 *   isVisible={showSuggestions}
 * />
 * ```
 */
export function InlineSuggestions({
  suggestions,
  onSelect,
  isVisible,
  maxSuggestions = 3,
  className,
  variant = 'chips',
}: InlineSuggestionsProps) {
  const displaySuggestions = suggestions.slice(0, maxSuggestions);

  return (
    <AnimatePresence>
      {isVisible && displaySuggestions.length > 0 && (
        <motion.div
          className={cn(
            'w-full',
            variant === 'list' && 'space-y-2',
            variant === 'cards' && 'grid grid-cols-1 sm:grid-cols-2 gap-2',
            variant === 'chips' && 'flex flex-wrap gap-2',
            className
          )}
          variants={suggestionsContainerVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          {displaySuggestions.map((suggestion, index) => (
            <SuggestionChip
              key={suggestion.id}
              suggestion={suggestion}
              index={index}
              onSelect={onSelect}
              variant={variant}
            />
          ))}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

interface SuggestionChipProps {
  suggestion: Suggestion;
  index: number;
  onSelect: (suggestion: Suggestion) => void;
  variant: 'chips' | 'list' | 'cards';
}

function SuggestionChip({
  suggestion,
  index,
  onSelect,
  variant,
}: SuggestionChipProps) {
  const handleClick = () => {
    onSelect(suggestion);
  };

  const baseClasses = cn(
    'cursor-pointer',
    'border border-border-primary',
    'bg-surface-secondary',
    'hover:bg-surface-tertiary',
    'hover:border-border-secondary',
    'transition-colors',
    'rounded-lg'
  );

  if (variant === 'chips') {
    return (
      <motion.button
        type="button"
        className={cn(
          baseClasses,
          'px-3 py-1.5',
          'text-sm text-text-primary',
          'flex items-center gap-2'
        )}
        variants={suggestionChipVariants}
        initial="hidden"
        animate="visible"
        whileHover="hover"
        whileTap="tap"
        custom={index}
        onClick={handleClick}
        aria-label={`Select suggestion: ${suggestion.text}`}
      >
        {suggestion.icon && (
          <span className="flex-shrink-0 text-text-secondary">
            {suggestion.icon}
          </span>
        )}
        <span>{suggestion.text}</span>
      </motion.button>
    );
  }

  if (variant === 'list') {
    return (
      <motion.button
        type="button"
        className={cn(
          baseClasses,
          'w-full px-4 py-3',
          'text-left',
          'flex items-start gap-3'
        )}
        variants={suggestionChipVariants}
        initial="hidden"
        animate="visible"
        whileHover="hover"
        whileTap="tap"
        custom={index}
        onClick={handleClick}
        aria-label={`Select suggestion: ${suggestion.text}`}
      >
        {suggestion.icon && (
          <span className="flex-shrink-0 text-text-secondary mt-0.5">
            {suggestion.icon}
          </span>
        )}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-text-primary">
            {suggestion.text}
          </div>
          {suggestion.description && (
            <div className="text-xs text-text-secondary mt-0.5">
              {suggestion.description}
            </div>
          )}
        </div>
      </motion.button>
    );
  }

  // Card variant
  return (
    <motion.button
      type="button"
      className={cn(
        baseClasses,
        'p-4',
        'text-left',
        'flex flex-col gap-2'
      )}
      variants={suggestionChipVariants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      whileTap="tap"
      custom={index}
      onClick={handleClick}
      aria-label={`Select suggestion: ${suggestion.text}`}
    >
      {suggestion.icon && (
        <span className="flex-shrink-0 text-text-secondary">
          {suggestion.icon}
        </span>
      )}
      <div className="text-sm font-medium text-text-primary">
        {suggestion.text}
      </div>
      {suggestion.description && (
        <div className="text-xs text-text-secondary">
          {suggestion.description}
        </div>
      )}
    </motion.button>
  );
}

/**
 * Quick suggestion pills for compact display
 */
interface QuickSuggestionsProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
  isVisible: boolean;
  className?: string;
}

export function QuickSuggestions({
  suggestions,
  onSelect,
  isVisible,
  className,
}: QuickSuggestionsProps) {
  return (
    <AnimatePresence>
      {isVisible && suggestions.length > 0 && (
        <motion.div
          className={cn(
            'flex flex-wrap gap-2',
            className
          )}
          variants={suggestionsContainerVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          {suggestions.map((suggestion, index) => (
            <motion.button
              key={suggestion}
              type="button"
              className={cn(
                'px-3 py-1.5',
                'text-xs font-medium',
                'text-text-primary',
                'bg-surface-secondary',
                'border border-border-primary',
                'rounded-full',
                'hover:bg-surface-tertiary',
                'hover:border-border-secondary',
                'transition-colors',
                'cursor-pointer'
              )}
              variants={suggestionChipVariants}
              initial="hidden"
              animate="visible"
              whileHover="hover"
              whileTap="tap"
              custom={index}
              onClick={() => onSelect(suggestion)}
              aria-label={`Select suggestion: ${suggestion}`}
            >
              {suggestion}
            </motion.button>
          ))}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/**
 * Context-aware suggestions that appear based on conversation state
 */
interface ContextualSuggestionsProps {
  suggestions: Suggestion[];
  onSelect: (suggestion: Suggestion) => void;
  isVisible: boolean;
  context?: string;
  className?: string;
}

export function ContextualSuggestions({
  suggestions,
  onSelect,
  isVisible,
  context,
  className,
}: ContextualSuggestionsProps) {
  return (
    <AnimatePresence>
      {isVisible && suggestions.length > 0 && (
        <motion.div
          className={cn(
            'w-full space-y-3',
            className
          )}
          variants={suggestionsContainerVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          {context && (
            <motion.div
              className="text-xs font-medium text-text-tertiary uppercase tracking-wide"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {context}
            </motion.div>
          )}
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <SuggestionChip
                key={suggestion.id}
                suggestion={suggestion}
                index={index}
                onSelect={onSelect}
                variant="chips"
              />
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
