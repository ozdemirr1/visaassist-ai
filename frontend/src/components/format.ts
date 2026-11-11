export function formatDate(value: string, language: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString(language === "tr" ? "tr-TR" : "en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function formatShortDate(value: string, language: string): string {
  return new Date(value).toLocaleDateString(language === "tr" ? "tr-TR" : "en-GB", {
    day: "numeric",
    month: "short",
  });
}

/** Whole days from today until an ISO date (0 when it is today or past). */
export function daysUntil(isoDate: string, today: Date = new Date()): number {
  const target = Date.parse(`${isoDate}T00:00:00Z`);
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.max(0, Math.round((target - start) / 86_400_000));
}
