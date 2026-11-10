// One place for every API call: same-origin /api, the session cookie, and the header the
// backend requires on state-changing requests (ADR 0004).

export const API_BASE = "/api";
const CSRF_HEADER = "X-Requested-With";
const CSRF_VALUE = "visaassist";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: a list of {msg}
    if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === "string") {
      return detail.map((d: { msg: string }) => d.msg).join("; ");
    }
  }
  return fallback;
}

export async function api<T>(
  path: string,
  options: { method?: string; json?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET" && method !== "HEAD") headers[CSRF_HEADER] = CSRF_VALUE;
  if (options.json !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    body: options.json === undefined ? undefined : JSON.stringify(options.json),
    signal: options.signal,
  });
  if (response.status === 204) return undefined as T;
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, detailOf(body, response.statusText));
  }
  return body as T;
}
