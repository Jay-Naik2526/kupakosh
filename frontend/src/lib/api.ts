export const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8010";
export const WS = API.replace(/^http/, "ws");

export async function get<T = any>(path: string, params?: Record<string, any>): Promise<T> {
  const q = params ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "").map(([k, v]) => [k, String(v)])) : "";
  const r = await fetch(`${API}${path}${q}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export async function post<T = any>(path: string, body: any): Promise<T> {
  const r = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}
