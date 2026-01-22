import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--claude-primary)] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--claude-primary)] text-white shadow hover:bg-[var(--claude-primary-hover)]",
        destructive:
          "bg-[var(--claude-error)] text-white shadow-sm hover:bg-[var(--claude-error)]/90",
        outline:
          "border border-[var(--claude-border)] bg-[var(--claude-background)] shadow-sm hover:bg-[var(--claude-background-secondary)] hover:text-[var(--claude-foreground)]",
        secondary:
          "bg-[var(--claude-background-secondary)] text-[var(--claude-foreground)] shadow-sm hover:bg-[var(--claude-background-secondary)]/80",
        ghost:
          "hover:bg-[var(--claude-background-secondary)] hover:text-[var(--claude-foreground)]",
        link: "text-[var(--claude-primary)] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

type ConflictingProps =
  | 'onAnimationStart'
  | 'onAnimationEnd'
  | 'onAnimationIteration'
  | 'onTransitionEnd'
  | 'onDragStart'
  | 'onDragEnd'
  | 'onDrag'
  | 'onDragEnter'
  | 'onDragExit'
  | 'onDragLeave'
  | 'onDragOver'
  | 'onDrop'
  | 'onTouchStart'
  | 'onTouchMove'
  | 'onTouchEnd'
  | 'onTouchCancel';

export interface ButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, ConflictingProps>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

/**
 * Animated Button with 2026 micro-interactions
 * Includes hover scale, enhanced shadow, and ripple effect
 */
export interface AnimatedButtonProps extends ButtonProps {
  /** Enable micro-interactions (hover, tap animations) */
  enableAnimation?: boolean;
  /** Show ripple effect on click */
  ripple?: boolean;
}

const AnimatedButton = React.forwardRef<HTMLButtonElement, AnimatedButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      enableAnimation = true,
      ripple = true,
      children,
      ...props
    },
    ref
  ) => {
    const [ripples, setRipples] = React.useState<Array<{ id: number; x: number; y: number }>>([]);
    const buttonRef = React.useRef<HTMLButtonElement>(null);
    const rippleTimeoutRef = React.useRef<NodeJS.Timeout | undefined>(undefined);

    // Handle ripple effect
    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (!ripple || !buttonRef.current) return;

      const rect = buttonRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const newRipple = {
        id: Date.now(),
        x,
        y,
      };

      setRipples((prev) => [...prev, newRipple]);

      // Clear ripple after animation
      if (rippleTimeoutRef.current) {
        clearTimeout(rippleTimeoutRef.current);
      }
      rippleTimeoutRef.current = setTimeout(() => {
        setRipples((prev) => prev.filter((r) => r.id !== newRipple.id));
      }, 600);
    };

    React.useEffect(() => {
      return () => {
        if (rippleTimeoutRef.current) {
          clearTimeout(rippleTimeoutRef.current);
        }
      };
    }, []);

    const MotionButton = motion(Button);
    const buttonVariants = {
      idle: {
        scale: 1,
      },
      hover: {
        scale: 1.02,
        transition: {
          type: 'spring',
          stiffness: 400,
          damping: 20,
          mass: 0.5,
        },
      },
      tap: {
        scale: 0.98,
        transition: { duration: 0.1 },
      },
    };

    if (!enableAnimation) {
      return (
        <Button
          ref={ref}
          className={className}
          variant={variant}
          size={size}
          asChild={asChild}
          {...props}
        >
          {children}
        </Button>
      );
    }

    return (
      <MotionButton
        ref={buttonRef}
        className={cn('relative overflow-hidden', className)}
        variant={variant}
        size={size}
        asChild={asChild}
        variants={buttonVariants}
        initial="idle"
        whileHover="hover"
        whileTap={{ scale: 0.95 }}
        onClick={handleClick}
        {...props}
      >
        {children}
        {ripples.map((rippleItem) => (
          <motion.span
            key={rippleItem.id}
            className="absolute pointer-events-none rounded-full bg-white/30"
            style={{
              left: rippleItem.x,
              top: rippleItem.y,
              width: 20,
              height: 20,
              marginLeft: -10,
              marginTop: -10,
            }}
            initial={{ scale: 0, opacity: 0.5 }}
            animate={{ scale: 4, opacity: 0 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        ))}
      </MotionButton>
    );
  }
);
AnimatedButton.displayName = "AnimatedButton";

export { Button, buttonVariants };
