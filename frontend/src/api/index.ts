import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export default api;

// ── Dashboard ──────────────────────────────────────────────────────────────

export const getDashboard = () => api.get('/api/dashboard').then(r => r.data);

// ── Customers ──────────────────────────────────────────────────────────────

export const getCustomers = (params?: object) =>
  api.get('/api/customers', { params }).then(r => r.data);

export const getCustomer = (id: number) =>
  api.get(`/api/customers/${id}`).then(r => r.data);

export const createCustomer = (data: object) =>
  api.post('/api/customers', data).then(r => r.data);

export const updateCustomer = (id: number, data: object) =>
  api.patch(`/api/customers/${id}`, data).then(r => r.data);

// ── Products ───────────────────────────────────────────────────────────────

export const getProducts = (params?: object) =>
  api.get('/api/products', { params }).then(r => r.data);

export const getProduct = (id: number) =>
  api.get(`/api/products/${id}`).then(r => r.data);

export const createProduct = (data: object) =>
  api.post('/api/products', data).then(r => r.data);

export const updateProduct = (id: number, data: object) =>
  api.patch(`/api/products/${id}`, data).then(r => r.data);

// ── Orders ─────────────────────────────────────────────────────────────────

export const getOrders = (params?: object) =>
  api.get('/api/orders', { params }).then(r => r.data);

export const getOrder = (id: number) =>
  api.get(`/api/orders/${id}`).then(r => r.data);

export const createOrder = (data: object) =>
  api.post('/api/orders', data).then(r => r.data);

export const updateOrder = (id: number, data: object) =>
  api.patch(`/api/orders/${id}`, data).then(r => r.data);

export const deleteOrder = (id: number) =>
  api.delete(`/api/orders/${id}`);

// ── Monthly Statements ─────────────────────────────────────────────────────

export const getStatements = (params?: object) =>
  api.get('/api/statements', { params }).then(r => r.data);

export const getStatement = (id: number) =>
  api.get(`/api/statements/${id}`).then(r => r.data);

export const createStatement = (data: object) =>
  api.post('/api/statements', data).then(r => r.data);

export const updateStatement = (id: number, data: object) =>
  api.patch(`/api/statements/${id}`, data).then(r => r.data);

// ── Seed ───────────────────────────────────────────────────────────────────

export const seedDemoData = () => api.post('/api/seed').then(r => r.data);
