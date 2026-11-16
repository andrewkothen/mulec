export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: `Request failed (${response.status})` }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  }
  return response.json();
}
export const json = (value: unknown, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(value),
});
export async function exportBlob(
  project: unknown,
  format: string,
  paper = "letter",
  part = "concert",
  style: { nashville?: boolean; rhythm?: boolean } = {},
) {
  const query = new URLSearchParams({ paper, part });
  if (style.nashville) query.set("nashville", "true");
  if (style.rhythm) query.set("rhythm", "true");
  const response = await fetch(`/api/export/${format}?${query}`, json(project));
  if (!response.ok) {
    const body = await response.json();
    throw new Error(body.detail || "Export failed");
  }
  return response.blob();
}
