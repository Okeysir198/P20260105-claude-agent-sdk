import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { format } from "date-fns"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

function toDate(date: Date | string): Date {
  return typeof date === 'string' ? new Date(date) : date
}

export function formatDate(date: Date | string): string {
  return format(toDate(date), 'MMM d, yyyy')
}

export function formatTime(date: Date | string): string {
  return format(toDate(date), 'h:mm a')
}

export function relativeTime(date: Date | string): string {
  const d = toDate(date)
  const diffInSeconds = Math.floor((Date.now() - d.getTime()) / 1000)

  if (diffInSeconds < 60) return 'just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  return formatDate(d)
}
