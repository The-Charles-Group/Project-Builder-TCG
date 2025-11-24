// Formatting utilities

export function formatNumber(num: number | undefined): string {
  if (num === undefined || num === null) return "—";
  return num.toLocaleString();
}

export function formatHours(hours: number | undefined): string {
  if (hours === undefined || hours === null) return "TBD";
  return `${hours}h`;
}

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return `${str.substring(0, maxLength)}…`;
}
