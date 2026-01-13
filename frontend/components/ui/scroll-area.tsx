import * as React from "react";

import { cn } from "@/lib/utils";

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "vertical" | "horizontal" | "both";
}

const ScrollArea = React.forwardRef<HTMLDivElement, ScrollAreaProps>(
  ({ className, children, orientation = "vertical", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "relative",
          {
            "overflow-y-auto overflow-x-hidden": orientation === "vertical",
            "overflow-x-auto overflow-y-hidden": orientation === "horizontal",
            "overflow-auto": orientation === "both",
          },
          // Custom scrollbar styling
          "scrollbar-thin scrollbar-track-transparent scrollbar-thumb-[var(--claude-border)]",
          "hover:scrollbar-thumb-[var(--claude-border-muted)]",
          // Webkit scrollbar styling
          "[&::-webkit-scrollbar]:w-2",
          "[&::-webkit-scrollbar]:h-2",
          "[&::-webkit-scrollbar-track]:bg-transparent",
          "[&::-webkit-scrollbar-thumb]:bg-[var(--claude-border)]",
          "[&::-webkit-scrollbar-thumb]:rounded-full",
          "[&::-webkit-scrollbar-thumb:hover]:bg-[var(--claude-border-muted)]",
          // Firefox scrollbar styling
          "scrollbar-color:var(--claude-border) transparent",
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
ScrollArea.displayName = "ScrollArea";

interface ScrollBarProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "vertical" | "horizontal";
}

const ScrollBar = React.forwardRef<HTMLDivElement, ScrollBarProps>(
  ({ className, orientation = "vertical", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex touch-none select-none transition-colors",
          orientation === "vertical" &&
            "h-full w-2.5 border-l border-l-transparent p-[1px]",
          orientation === "horizontal" &&
            "h-2.5 flex-col border-t border-t-transparent p-[1px]",
          className
        )}
        {...props}
      />
    );
  }
);
ScrollBar.displayName = "ScrollBar";

export { ScrollArea, ScrollBar };
