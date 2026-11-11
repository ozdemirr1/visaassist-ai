// Client-side checks of a file before upload, the same limits as the API's
// (backend/app/storage/documents.py). The server decides by the file's content, not its name.

export const MAX_UPLOAD_MB = 10;
export const ACCEPTED_TYPES: Record<string, string> = {
  "application/pdf": "PDF",
  "image/jpeg": "JPEG",
  "image/png": "PNG",
};

export type UploadProblem = "tooLarge" | "type" | null;

export function uploadProblem(file: { size: number; type: string }): UploadProblem {
  if (!(file.type in ACCEPTED_TYPES)) return "type";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return "tooLarge";
  return null;
}

export function formatSize(bytes: number, language: string): string {
  const locale = language === "tr" ? "tr-TR" : "en-GB";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toLocaleString(locale, { maximumFractionDigits: 1 })} MB`;
}
