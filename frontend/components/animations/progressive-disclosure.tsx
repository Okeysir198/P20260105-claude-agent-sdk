'use client';

/**
 * Progressive Disclosure Component
 *
 * 2026 Design Pattern: Progressive Disclosure
 *
 * Hides advanced options and secondary information behind collapsible sections
 * to reduce cognitive load and improve user experience. Uses smooth animations
 * for expand/collapse transitions.
 *
 * Features:
 * - Smooth spring-based expand/collapse
 * - Chevron rotation animation
 * - Accessible keyboard navigation
 * - Configurable default state
 *
 * @module components/animations/progressive-disclosure
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { chevronVariants, progressiveCollapseVariants } from '@/lib/animations';

interface ProgressiveDisclosureProps {
  /** Content to hide behind disclosure */
  children: React.ReactNode;
  /** Trigger label */
  triggerLabel: string;
  /** Whether disclosure is open by default */
  defaultOpen?: boolean;
  /** Icon to show in trigger */
  icon?: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Variant style */
  variant?: 'default' | 'compact' | 'bordered';
}

/**
 * Progressive disclosure wrapper component
 *
 * @example
 * ```tsx
 * <ProgressiveDisclosure
 *   triggerLabel="Advanced Options"
 *   defaultOpen={false}
 * >
 *   <div>Advanced content here</div>
 * </ProgressiveDisclosure>
 * ```
 */
export function ProgressiveDisclosure({
  children,
  triggerLabel,
  defaultOpen = false,
  icon,
  className,
  variant = 'default',
}: ProgressiveDisclosureProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const variantClasses = {
    default: 'border-l-2 border-claude-orange-300 pl-4',
    compact: '',
    bordered: 'border border-border-primary rounded-lg px-4 py-2',
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={cn('w-full', className)}>
      <CollapsibleTrigger
        className={cn(
          'w-full flex items-center gap-2',
          'text-left',
          'text-sm font-medium text-text-primary',
          'hover:text-text-accent',
          'focus:outline-none',
          'transition-colors',
          'group',
          variantClasses[variant]
        )}
      >
        <motion.div
          variants={chevronVariants}
          animate={isOpen ? 'expanded' : 'collapsed'}
          transition={{ duration: 0.2 }}
          className="flex-shrink-0"
        >
          <ChevronRight className="w-4 h-4" />
        </motion.div>
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <span>{triggerLabel}</span>
      </CollapsibleTrigger>

      <AnimatePresence initial={false}>
        {isOpen && (
          <CollapsibleContent forceMount>
            <motion.div
              initial="collapsed"
              animate="expanded"
              exit="collapsed"
              variants={progressiveCollapseVariants}
              className="overflow-hidden"
            >
              <div className={cn(variant === 'default' && 'mt-3')}>
                {children}
              </div>
            </motion.div>
          </CollapsibleContent>
        )}
      </AnimatePresence>
    </Collapsible>
  );
}

/**
 * Settings group with progressive disclosure
 */
interface SettingsGroupProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

export function SettingsGroup({
  title,
  description,
  children,
  defaultOpen = false,
  className,
}: SettingsGroupProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={cn('w-full', className)}>
      <CollapsibleTrigger
        className={cn(
          'w-full flex items-start gap-3',
          'p-4',
          'border border-border-primary rounded-lg',
          'bg-surface-secondary',
          'hover:bg-surface-tertiary',
          'transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-claude-orange-500'
        )}
      >
        <motion.div
          variants={chevronVariants}
          animate={isOpen ? 'expanded' : 'collapsed'}
          transition={{ duration: 0.2 }}
          className="flex-shrink-0 mt-0.5"
        >
          <ChevronDown className="w-4 h-4 text-text-secondary" />
        </motion.div>
        <div className="flex-1 text-left">
          <div className="text-sm font-medium text-text-primary">{title}</div>
          {description && (
            <div className="text-xs text-text-secondary mt-0.5">{description}</div>
          )}
        </div>
      </CollapsibleTrigger>

      <AnimatePresence initial={false}>
        {isOpen && (
          <CollapsibleContent forceMount>
            <motion.div
              initial="collapsed"
              animate="expanded"
              exit="collapsed"
              variants={progressiveCollapseVariants}
              className="overflow-hidden"
            >
              <div className="px-4 pb-4 pt-2">
                {children}
              </div>
            </motion.div>
          </CollapsibleContent>
        )}
      </AnimatePresence>
    </Collapsible>
  );
}

/**
 * Info tooltip with progressive disclosure
 */
interface InfoDisclosureProps {
  label: string;
  children: React.ReactNode;
  className?: string;
}

export function InfoDisclosure({ label, children, className }: InfoDisclosureProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={cn('w-full', className)}>
      <CollapsibleTrigger
        className={cn(
          'flex items-center gap-1',
          'text-xs text-text-accent',
          'hover:underline',
          'focus:outline-none',
          'transition-colors'
        )}
      >
        <span>{label}</span>
        <motion.div
          variants={chevronVariants}
          animate={isOpen ? 'expanded' : 'collapsed'}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-3 h-3" />
        </motion.div>
      </CollapsibleTrigger>

      <AnimatePresence initial={false}>
        {isOpen && (
          <CollapsibleContent forceMount>
            <motion.div
              initial="collapsed"
              animate="expanded"
              exit="collapsed"
              variants={progressiveCollapseVariants}
              className="overflow-hidden"
            >
              <div className="text-xs text-text-secondary mt-2">
                {children}
              </div>
            </motion.div>
          </CollapsibleContent>
        )}
      </AnimatePresence>
    </Collapsible>
  );
}

/**
 * Code block with progressive disclosure
 */
interface CodeDisclosureProps {
  language: string;
  code: string;
  defaultOpen?: boolean;
  className?: string;
}

export function CodeDisclosure({
  language,
  code,
  defaultOpen = false,
  className,
}: CodeDisclosureProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={cn('w-full', className)}>
      <CollapsibleTrigger
        className={cn(
          'w-full flex items-center justify-between',
          'px-4 py-2',
          'bg-surface-primary',
          'border border-border-primary rounded-t-lg',
          'text-xs font-medium text-text-primary',
          'hover:bg-surface-tertiary',
          'transition-colors',
          'focus:outline-none'
        )}
      >
        <span>{language}</span>
        <motion.div
          variants={chevronVariants}
          animate={isOpen ? 'expanded' : 'collapsed'}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </CollapsibleTrigger>

      <AnimatePresence initial={false}>
        {isOpen && (
          <CollapsibleContent forceMount>
            <motion.div
              initial="collapsed"
              animate="expanded"
              exit="collapsed"
              variants={progressiveCollapseVariants}
              className="overflow-hidden"
            >
              <pre className={cn(
                'p-4 text-xs font-mono text-text-secondary',
                'bg-surface-primary',
                'border border-t-0 border-border-primary rounded-b-lg',
                'overflow-x-auto'
              )}>
                <code>{code}</code>
              </pre>
            </motion.div>
          </CollapsibleContent>
        )}
      </AnimatePresence>
    </Collapsible>
  );
}

/**
 * Advanced options panel example
 */
export function AdvancedOptionsPanel() {
  return (
    <div className="w-full space-y-4">
      <ProgressiveDisclosure
        triggerLabel="Advanced Options"
        defaultOpen={false}
        variant="bordered"
      >
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-text-primary">
              Temperature
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              defaultValue="0.7"
              className="w-full mt-2"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-text-primary">
              Max Tokens
            </label>
            <input
              type="number"
              defaultValue="4096"
              className="w-full mt-2 px-3 py-2 border border-border-primary rounded-lg"
            />
          </div>
        </div>
      </ProgressiveDisclosure>

      <SettingsGroup
        title="Model Settings"
        description="Configure model behavior and parameters"
        defaultOpen={false}
      >
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-primary">Streaming</span>
            <button className="text-sm text-text-accent">Enabled</button>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-primary">System Prompt</span>
            <button className="text-sm text-text-accent">Edit</button>
          </div>
        </div>
      </SettingsGroup>
    </div>
  );
}
