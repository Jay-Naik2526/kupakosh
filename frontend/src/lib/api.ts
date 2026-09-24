// Same-origin by default: works on localhost, a LAN IP, or a shared tunnel link.
// In `npm run dev` (:3000) Next proxies /api to the backend; the replay WebSocket goes straight to :8010.
export const API = process.env.NEXT_PUBLIC_API ?? "";
export const WS = (() => {
  if (process.env.NEXT_PUBLIC_API) return process.env.NEXT_PUBLIC_API.replace(/^http/, "ws");
  if (typeof window === "undefined") return "";
  const { protocol, hostname, port, host } = window.location;
  if (port === "3000") return `${protocol === "https:" ? "wss" : "ws"}://${hostname}:8010`;
  return `${protocol === "https:" ? "wss" : "ws"}://${host}`;
})();

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
