// Client-side checks of the trip dates, the same as the API's (backend/app/api/applications.py),
// so the applicant sees the problem before sending.

export const MAX_TRIP_DAYS = 90; // Schengen short stay

export type TripProblem = "missing" | "endBeforeStart" | "tooLong" | null;

function days(start: string, end: string): number {
  const ms = Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`);
  return Math.round(ms / 86_400_000) + 1;
}

export function tripProblem(start: string, end: string): TripProblem {
  if (!start || !end) return "missing";
  if (end < start) return "endBeforeStart";
  if (days(start, end) > MAX_TRIP_DAYS) return "tooLong";
  return null;
}

export function tripDays(start: string, end: string): number {
  return days(start, end);
}
