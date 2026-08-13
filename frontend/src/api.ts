const API_ROOT = import.meta.env.VITE_API_URL || "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  companyId?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (companyId) headers.set("X-Company-ID", companyId);
  const response = await fetch(`${API_ROOT}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
    const detail = typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiDownload(
  path: string,
  body: unknown,
  token: string,
  companyId: string,
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_ROOT}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "X-Company-ID": companyId,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(payload.detail ?? `Export failed (${response.status})`, response.status);
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? "ctec-report";
  return { blob: await response.blob(), filename };
}

export async function apiUpload<T>(
  path: string,
  file: File,
  token: string,
  companyId: string,
  fieldName = "file",
): Promise<T> {
  const body = new FormData();
  body.set(fieldName, file);
  const response = await fetch(`${API_ROOT}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "X-Company-ID": companyId },
    body,
  });
  const payload = (await response.json().catch(() => ({}))) as T & { detail?: unknown };
  if (!response.ok) {
    const message = typeof payload.detail === "string" ? payload.detail : `Upload failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return payload;
}

export async function apiGetDownload(
  path: string,
  token: string,
  companyId: string,
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: { Authorization: `Bearer ${token}`, "X-Company-ID": companyId },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(payload.detail ?? `Download failed (${response.status})`, response.status);
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? "migration-exceptions.csv";
  return { blob: await response.blob(), filename };
}
