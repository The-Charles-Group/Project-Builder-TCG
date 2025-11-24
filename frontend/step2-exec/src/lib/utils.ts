import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatHours(hours: number | undefined): string {
  if (!hours) return 'n/a';
  return hours.toLocaleString();
}

export function formatHoursRange(min: number | undefined, max: number | undefined): string {
  if (!min || !max) return 'n/a';
  return `${min.toLocaleString()}–${max.toLocaleString()}h`;
}
