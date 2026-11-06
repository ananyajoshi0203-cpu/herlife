/* HerLife web platform shim.
   The app was written against claude.ai's `window.claude.use(name)` runtime. On the hosted
   web app this file answers the same calls with HerLife's own server, so the UI is identical
   in both places. Errors reject with `{code}` exactly like the claude.ai runtime does, so the
   page's existing fallbacks keep working. */
(() => {
  "use strict";
  const api = async (method, path, body) => {
    const res = await fetch(path, { method, credentials: "same-origin", headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) throw { code: data?.detail?.code || "upstream_error", message: data?.detail?.message || res.statusText };
    return data;
  };

  const sample = async (input, opts = {}) => ({ text: JSON.stringify(await sample.json(input, opts)), truncated: false });
  sample.json = (input, opts = {}) => api("POST", "/api/ai/json", { prompt: typeof input === "string" ? input : input.map((m) => m.content).join("\n\n"), tier: opts.modelTier === "default" || opts.modelTier === "complex" ? opts.modelTier : "quick" });

  const stateDoc = {
    async get() { const r = await api("GET", "/api/state"); return { exists: r.exists, data: () => (r.exists ? { json: r.json, updatedAt: r.updatedAt } : undefined) }; },
    set(data) { return api("PUT", "/api/state", data); },
    delete() { return api("DELETE", "/api/state"); },
  };
  const db = { collection: () => ({ doc: () => stateDoc }), doc: () => stateDoc };

  let me = null;
  const user = { id: async () => (me ||= (await api("GET", "/api/me")).id), isOwner: () => true, canEdit: () => true };

  const OURA_PATH = { oura_daily: (input) => `/api/oura/daily?days=${encodeURIComponent(input?.days ?? 90)}` };
  const mcp = {
    async callTool(server, tool, input) {
      if (server !== "host:bloom_oura" || !OURA_PATH[tool]) throw { code: "not_in_manifest" };
      try { return { payload: await api("GET", OURA_PATH[tool](input)), content: [] }; }
      catch (error) {
        if (error.code === "oura_not_connected") { window.location.href = "/api/oura/connect"; throw { code: "cancelled", message: "Opening Oura sign in" }; }
        throw error;
      }
    },
  };

  const calendar = {
    today() { const d = new Date(), s = new Date(d.getFullYear(), d.getMonth(), d.getDate()), e = new Date(s.getTime() + 864e5);
      return api("GET", `/api/calendar/events?start=${encodeURIComponent(s.toISOString())}&end=${encodeURIComponent(e.toISOString())}`); },
    create(event) { return api("POST", "/api/calendar/events", event); },
    connect() { window.location.href = "/api/calendar/connect"; },
  };
  const namespaces = { sample, db, user, mcp, calendar };
  window.claude = { hosted: true, use: async (name) => namespaces[name] ?? null };
})();
