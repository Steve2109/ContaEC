import axios from 'axios';
import type { User, Company, License, Invoice, Product, Employee } from '../types';

const API_BASE_URL = '/api/v1';

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
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  register: async (data: any) => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },
  me: async () => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
};

export const companyService = {
  getAll: async () => {
    const response = await api.get<Company[]>('/companies');
    return response.data;
  },
  getByRuc: async (ruc: string) => {
    const response = await api.get<Company>(`/companies/${ruc}`);
    return response.data;
  },
  create: async (data: Partial<Company>) => {
    const response = await api.post<Company>('/companies', data);
    return response.data;
  },
  update: async (id: string, data: Partial<Company>) => {
    const response = await api.put<Company>(`/companies/${id}`, data);
    return response.data;
  },
};

export const licenseService = {
  getMyLicense: async () => {
    const response = await api.get<License>('/license');
    return response.data;
  },
};

export const invoiceService = {
  getAll: async (companyId: string) => {
    const response = await api.get<Invoice[]>(`/invoices?company_id=${companyId}`);
    return response.data;
  },
  create: async (data: Partial<Invoice>) => {
    const response = await api.post<Invoice>('/invoices', data);
    return response.data;
  },
  authorize: async (id: string) => {
    const response = await api.post<Invoice>(`/invoices/${id}/authorize`);
    return response.data;
  },
};

export const productService = {
  getAll: async (companyId: string) => {
    const response = await api.get<Product[]>(`/products?company_id=${companyId}`);
    return response.data;
  },
  create: async (data: Partial<Product>) => {
    const response = await api.post<Product>('/products', data);
    return response.data;
  },
  update: async (id: string, data: Partial<Product>) => {
    const response = await api.put<Product>(`/products/${id}`, data);
    return response.data;
  },
};

export const employeeService = {
  getAll: async (companyId: string) => {
    const response = await api.get<Employee[]>(`/employees?company_id=${companyId}`);
    return response.data;
  },
  create: async (data: Partial<Employee>) => {
    const response = await api.post<Employee>('/employees', data);
    return response.data;
  },
};

export const adminService = {
  getDashboardSummary: async () => {
    const response = await api.get('/admin/dashboard/summary');
    return response.data;
  },
  getHealth: async () => {
    const response = await api.get('/admin/dashboard/health');
    return response.data;
  },
  getUsers: async () => {
    const response = await api.get('/admin/users');
    return response.data;
  },
  updateLicense: async (userId: string, data: any) => {
    const response = await api.put(`/admin/licenses/${userId}`, data);
    return response.data;
  },
};

export default api;
