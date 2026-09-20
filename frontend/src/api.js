const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore parse failure, keep statusText */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  listSections: () => request("/api/sections"),
  sectionsMap: () => request("/api/sections/map"),

  listRequests: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/api/requests${qs ? `?${qs}` : ""}`);
  },
  submitRequest: (payload) =>
    request("/api/requests", { method: "POST", body: JSON.stringify(payload) }),
  deleteRequest: (id) => request(`/api/requests/${id}`, { method: "DELETE" }),

  getPlan: (horizon, mode = "optimized") =>
    request(`/api/plans/${horizon}?mode=${mode}`),
  comparePlan: (horizon) => request(`/api/plans/${horizon}/compare`),
  overridePlan: (horizon, payload) =>
    request(`/api/plans/${horizon}/override`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  reseed: () => request("/api/admin/reseed", { method: "POST" }),
};
