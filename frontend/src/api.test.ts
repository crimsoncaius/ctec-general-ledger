import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, apiDownload, apiGetDownload, apiUpload } from "./api";

function json(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  }));
}

describe("API client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("adds authentication and company headers and handles empty responses", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })));
    vi.stubGlobal("fetch", fetchMock);
    await expect(api("/accounts/1", { method: "DELETE", headers: { "X-Test": "yes" } }, "token", "company")).resolves.toBeUndefined();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [RequestInfo | URL, RequestInit];
    expect(url).toBe("/api/v1/accounts/1");
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer token");
    expect(headers.get("X-Company-ID")).toBe("company");
    expect(headers.get("X-Test")).toBe("yes");
  });

  it("returns JSON and reports both detailed and generic API failures", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockImplementationOnce(() => json({ ok: true }))
      .mockImplementationOnce(() => json({ detail: "Denied" }, 403))
      .mockImplementationOnce(() => Promise.resolve(new Response("not-json", { status: 500 }))));
    await expect(api<{ ok: boolean }>("/ok")).resolves.toEqual({ ok: true });
    await expect(api("/denied")).rejects.toEqual(new ApiError("Denied", 403));
    await expect(api("/broken")).rejects.toMatchObject({ message: "Request failed (500)", status: 500 });
  });

  it("downloads reports using the supplied or fallback filename", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockImplementationOnce(() => Promise.resolve(new Response("pdf", { status: 200, headers: { "Content-Disposition": "attachment; filename=\"trial.pdf\"" } })))
      .mockImplementationOnce(() => Promise.resolve(new Response("xlsx", { status: 200 }))));
    await expect(apiDownload("/reports/run", { format: "pdf" }, "t", "c")).resolves.toMatchObject({ filename: "trial.pdf" });
    await expect(apiDownload("/reports/run", {}, "t", "c")).resolves.toMatchObject({ filename: "ctec-report" });
  });

  it("reports export errors and uploads multipart files without a content-type override", async () => {
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => json({ detail: "Export blocked" }, 422))
      .mockImplementationOnce(() => json({ rows: 2 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(apiDownload("/reports/run", {}, "t", "c")).rejects.toMatchObject({ message: "Export blocked" });
    const file = new File(["a,b"], "accounts.csv", { type: "text/csv" });
    await expect(apiUpload<{ rows: number }>("/imports/accounts", file, "t", "c", "snapshot")).resolves.toEqual({ rows: 2 });
    const upload = fetchMock.mock.calls[1][1];
    expect(upload?.body).toBeInstanceOf(FormData);
    expect((upload?.body as FormData).get("snapshot")).toBe(file);
    expect(new Headers(upload?.headers).has("Content-Type")).toBe(false);
  });

  it("handles upload and GET-download errors and filenames", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockImplementationOnce(() => json({}, 400))
      .mockImplementationOnce(() => json({ detail: "No exceptions" }, 404))
      .mockImplementationOnce(() => Promise.resolve(new Response("csv", { status: 200, headers: { "Content-Disposition": "attachment; filename=\"exceptions.csv\"" } })))
      .mockImplementationOnce(() => Promise.resolve(new Response("csv", { status: 200 }))));
    await expect(apiUpload("/upload", new File(["x"], "x.csv"), "t", "c")).rejects.toMatchObject({ message: "Upload failed (400)" });
    await expect(apiGetDownload("/exceptions", "t", "c")).rejects.toMatchObject({ message: "No exceptions" });
    await expect(apiGetDownload("/exceptions", "t", "c")).resolves.toMatchObject({ filename: "exceptions.csv" });
    await expect(apiGetDownload("/exceptions", "t", "c")).resolves.toMatchObject({ filename: "migration-exceptions.csv" });
  });

  it("uses generic errors when failed download and upload responses are not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockImplementationOnce(() => Promise.resolve(new Response("bad", { status: 502 })))
      .mockImplementationOnce(() => Promise.resolve(new Response("bad", { status: 413 })))
      .mockImplementationOnce(() => Promise.resolve(new Response("bad", { status: 500 }))));
    await expect(apiDownload("/export", {}, "t", "c")).rejects.toMatchObject({ message: "Export failed (502)" });
    await expect(apiUpload("/upload", new File(["x"], "x.zip"), "t", "c")).rejects.toMatchObject({ message: "Upload failed (413)" });
    await expect(apiGetDownload("/download", "t", "c")).rejects.toMatchObject({ message: "Download failed (500)" });
  });
});
