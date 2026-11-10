export function formatDate(value: string, language: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString(language === "tr" ? "tr-TR" : "en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
