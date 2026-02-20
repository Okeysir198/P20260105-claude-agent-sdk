/**
 * Returns the CSS variable name for a progress bar color based on percentage.
 */
export function getProgressColorVar(progressPercent: number): string {
  if (progressPercent > 50) return '--progress-high';
  if (progressPercent > 25) return '--progress-medium';
  return '--progress-low';
}
