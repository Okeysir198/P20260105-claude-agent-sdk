import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-[var(--claude-border)]",
        className
      )}
      {...props}
    />
  );
}

// Pre-built skeleton variants for common use cases
function SkeletonText({ className, ...props }: SkeletonProps) {
  return (
    <Skeleton
      className={cn("h-4 w-full", className)}
      {...props}
    />
  );
}

function SkeletonCircle({ className, ...props }: SkeletonProps) {
  return (
    <Skeleton
      className={cn("h-10 w-10 rounded-full", className)}
      {...props}
    />
  );
}

function SkeletonCard({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn("space-y-3", className)} {...props}>
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  );
}

function SkeletonMessage({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn("flex gap-3", className)} {...props}>
      <SkeletonCircle className="h-8 w-8 shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-1/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    </div>
  );
}

export { Skeleton, SkeletonText, SkeletonCircle, SkeletonCard, SkeletonMessage };
