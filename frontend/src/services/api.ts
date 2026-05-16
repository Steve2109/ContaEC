import axios from 'axios';
import type { User, Company, License, Invoice, Product, Employee } from '../types';

const API_BASE_URL = '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para manejar errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  login: async (email: string, password: string) => {
    const response = await api.post('/api/v1/auth/login', { email, password });
    return response.data;
  },
  register: async (data: any) => {
    const response = await api.post('/api/v1/auth/register', data);
    return response.data;
  },
  me: async () => {
    const response = await api.get<User>('/api/v1/auth/me');
    return response.data;
  },
};

export const companyService = {
  getAll: async () => {
    const response = await api.get<Company[]>('/api/v1/companies');
    return response.data;
  },
  getByRuc: async (ruc: string) => {
    const response = await api.get<Company>(`/api/v1/companies/${ruc}`);
    return response.data;
  },
  create: async (data: Partial<Company>) => {
    const response = await api.post<Company>('/api/v1/companies', data);
    return response.data;
  },
  update: async (id: string, data: Partial<Company>) => {
    const response = await api.put<Company>(`/api/v1/companies/${id}`, data);
    return response.data;
  },
};

export const licenseService = {
  getMyLicense: async () => {
    const response = await api.get<License>('/api/v1/license');
    return response.data;
  },
};

export const invoiceService = {
  getAll: async (companyId: string) => {
    const response = await api.get<Invoice[]>(`/facturacion/facturas/?company_id=${companyId}`);
    return response.data;
  },
  create: async (data: Partial<Invoice>) => {
    const response = await api.post<Invoice>('/facturacion/facturas/', data);
    return response.data;
  },
  authorize: async (id: string) => {
    const response = await api.post<Invoice>(`/facturacion/facturas/${id}/autorizar`);
    return response.data;
  },
};

export const productService = {
  getAll: async (companyId: string) => {
    const response = await api.get<Product[]>(`/inventario/productos/?company_id=${companyId}`);
    return response.data;
  },
  create: async (data: Partial<Product>) => {
    const response = await api.post<Product>('/inventario/productos/', data);
    return response.data;
  },
  update: async (id: string, data: Partial<Product>) => {
    const response = await api.put<Product>(`/inventario/productos/${id}`, data);
    return response.data;
  },
};

export const employeeService = {
  getAll: async (companyId: string) => {
    const response = await api.get<Employee[]>(`/api/nomina/empleados?company_id=${companyId}`);
    return response.data;
  },
  create: async (data: Partial<Employee>) => {
    const response = await api.post<Employee>('/api/nomina/empleados', data);
    return response.data;
  },
};

export const adminService = {
  getDashboardSummary: async () => {
    const response = await api.get('/api/v1/admin/dashboard/summary');
    return response.data;
  },
  getHealth: async () => {
    const response = await api.get('/api/v1/admin/dashboard/health');
    return response.data;
  },
  getUsers: async () => {
    const response = await api.get('/api/v1/admin/users');
    return response.data;
  },
  updateLicense: async (userId: string, data: any) => {
    const response = await api.put(`/api/v1/admin/licenses/${userId}`, data);
    return response.data;
  },
};

export default api;
