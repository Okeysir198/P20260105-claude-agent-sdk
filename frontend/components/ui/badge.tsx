import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--claude-primary)] focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[var(--claude-primary)] text-white shadow hover:bg-[var(--claude-primary-hover)]",
        secondary:
          "border-transparent bg-[var(--claude-background-secondary)] text-[var(--claude-foreground)] hover:bg-[var(--claude-background-secondary)]/80",
        destructive:
          "border-transparent bg-[var(--claude-error)] text-white shadow hover:bg-[var(--claude-error)]/80",
        outline:
          "border-[var(--claude-border)] text-[var(--claude-foreground)]",
        success:
          "border-transparent bg-[var(--claude-success)] text-white shadow hover:bg-[var(--claude-success)]/80",
        warning:
          "border-transparent bg-[var(--claude-warning)] text-white shadow hover:bg-[var(--claude-warning)]/80",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
