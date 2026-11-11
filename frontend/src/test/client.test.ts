import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "../api/client";

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), { status }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("calls /api on the same origin with the session cookie", async () => {
    const fetchMock = mockFetch(200, { ok: true });
    await api("/health");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/health");
    expect(init.credentials).toBe("include");
    expect(init.headers["X-Requested-With"]).toBeUndefined();
  });

  it("adds the custom header and JSON body on state-changing requests (ADR 0004)", async () => {
    const fetchMock = mockFetch(200, {});
    await api("/auth/login", { method: "POST", json: { email: "a@example.com" } });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["X-Requested-With"]).toBe("visaassist");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe('{"email":"a@example.com"}');
  });

  it("sends a form as it is, without a JSON content type", async () => {
    const fetchMock = mockFetch(201, {});
    const form = new FormData();
    form.append("requirement_id", "eu-req-bank-statement");
    await api("/applications/f1/documents", { method: "POST", form });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe(form);
    expect(init.headers["Content-Type"]).toBeUndefined();
    expect(init.headers["X-Requested-With"]).toBe("visaassist");
  });

  it("turns an error response into an ApiError with the server's message", async () => {
    mockFetch(401, { detail: "Wrong e-mail address or password." });
    await expect(api("/auth/login", { method: "POST" })).rejects.toEqual(
      new ApiError(401, "Wrong e-mail address or password."),
    );
  });

  it("joins validation messages", async () => {
    mockFetch(422, { detail: [{ msg: "field required" }, { msg: "too short" }] });
    await expect(api("/x", { method: "POST" })).rejects.toThrow("field required; too short");
  });

  it("returns nothing for 204", async () => {
    mockFetch(204, undefined);
    await expect(api("/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });
});
