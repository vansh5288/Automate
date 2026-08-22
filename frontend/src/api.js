const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  listRequests: () => fetch(`${BASE_URL}/api/requests`).then(handle),
  getRequest: (id) => fetch(`${BASE_URL}/api/requests/${id}`).then(handle),
  getRuns: (id) => fetch(`${BASE_URL}/api/requests/${id}/runs`).then(handle),
  submitRequest: (payload) =>
    fetch(`${BASE_URL}/api/requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(handle),
  retryRequest: (id) => fetch(`${BASE_URL}/api/requests/${id}/retry`, { method: "POST" }).then(handle),
};
