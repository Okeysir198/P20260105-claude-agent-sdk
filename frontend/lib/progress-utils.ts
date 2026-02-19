/**
 * Shared progress bar utilities.
 *
 * @module progress-utils
 */

/**
 * Returns the CSS variable name for a progress bar color based on percentage.
 *
 * @param progressPercent - Progress percentage (0-100)
 * @returns CSS variable name for the appropriate color tier
 */
export function getProgressColorVar(progressPercent: number): string {
  if (progressPercent > 50) return '--progress-high';
  if (progressPercent > 25) return '--progress-medium';
  return '--progress-low';
}
