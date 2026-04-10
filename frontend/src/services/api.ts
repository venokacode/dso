import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

// ── Helpers ──────────────────────────────────────────────

export function fen2yuan(fen: number): string {
  return (fen / 100).toFixed(2);
}

export function yuan2fen(yuan: number): number {
  return Math.round(yuan * 100);
}

// ── Customers ────────────────────────────────────────────

export const customerApi = {
  list: (params?: Record<string, any>) => api.get("/customers", { params }),
  listAll: () => api.get("/customers/all"),
  get: (id: number) => api.get(`/customers/${id}`),
  create: (data: any) => api.post("/customers", data),
  update: (id: number, data: any) => api.put(`/customers/${id}`, data),
  delete: (id: number) => api.delete(`/customers/${id}`),
};

// ── Products ─────────────────────────────────────────────

export const productApi = {
  list: (params?: Record<string, any>) => api.get("/products", { params }),
  listAll: () => api.get("/products/all"),
  get: (id: number) => api.get(`/products/${id}`),
  create: (data: any) => api.post("/products", data),
  update: (id: number, data: any) => api.put(`/products/${id}`, data),
  delete: (id: number) => api.delete(`/products/${id}`),
};

// ── Orders ───────────────────────────────────────────────

export const orderApi = {
  list: (params?: Record<string, any>) => api.get("/orders", { params }),
  get: (id: number) => api.get(`/orders/${id}`),
  create: (data: any) => api.post("/orders", data),
  update: (id: number, data: any) => api.put(`/orders/${id}`, data),
  delete: (id: number) => api.delete(`/orders/${id}`),
};

// ── Invoices ─────────────────────────────────────────────

export const invoiceApi = {
  list: (params?: Record<string, any>) => api.get("/invoices", { params }),
  generate: (year: number, month: number) =>
    api.post("/invoices/generate", null, { params: { year, month } }),
  update: (id: number, data: any) => api.put(`/invoices/${id}`, data),
  exportUrl: (id: number) => `/api/invoices/${id}/export`,
};

// ── Dashboard ────────────────────────────────────────────

export const dashboardApi = {
  get: () => api.get("/dashboard"),
};

export default api;
