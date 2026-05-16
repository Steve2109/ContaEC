import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://10.0.1.20/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor: attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 and refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem('access_token', res.data.access_token);
          originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth ───
export const apiLogin = (data: { email: string; password: string }) =>
  api.post('/auth/login', data);

export const apiRegister = (data: { email: string; password: string; full_name: string }) =>
  api.post('/auth/register', data);

export const apiGetMe = () => api.get('/auth/me');

// ─── Dashboard ───
export const apiGetDashboardStats = () => api.get('/dashboard/stats');
export const apiGetRecentActivity = (limit = 10) => api.get(`/dashboard/activity?limit=${limit}`);
export const apiGetLicenseStatus = () => api.get('/license/status');

// ─── Companies ───
export const apiGetCompanies = () => api.get('/companies');
export const apiCreateCompany = (data: any) => api.post('/companies', data);
export const apiUpdateCompany = (id: number, data: any) => api.put(`/companies/${id}`, data);
export const apiDeleteCompany = (id: number) => api.delete(`/companies/${id}`);
export const apiUploadLogo = (companyId: number, formData: FormData) =>
  api.post(`/companies/${companyId}/logo`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const apiQueryRucSRI = (ruc: string) => api.get(`/companies/lookup-ruc?ruc=${ruc}`);

// ─── Invoices / Facturación ───
export const apiGetInvoices = () => api.get('/facturacion/comprobantes');
export const apiCreateInvoice = (data: any) => api.post('/facturacion/comprobantes', data);
export const apiGetInvoice = (id: number) => api.get(`/facturacion/comprobantes/${id}`);
export const apiSendInvoiceToSRI = (id: number) => api.post(`/facturacion/comprobantes/${id}/enviar-sri`);
export const apiGetInvoiceXML = (id: number) => api.get(`/facturacion/comprobantes/${id}/xml`, { responseType: 'blob' });
export const apiGetInvoicePDF = (id: number) => api.get(`/facturacion/comprobantes/${id}/pdf`, { responseType: 'blob' });

// ─── Clients ───
export const apiGetClients = () => api.get('/facturacion/clientes');
export const apiCreateClient = (data: any) => api.post('/facturacion/clientes', data);

// ─── Products / Inventory ───
export const apiGetProducts = () => api.get('/inventario/productos');
export const apiCreateProduct = (data: any) => api.post('/inventario/productos', data);
export const apiUpdateProduct = (id: number, data: any) => api.put(`/inventario/productos/${id}`, data);
export const apiDeleteProduct = (id: number) => api.delete(`/inventario/productos/${id}`);
export const apiGetProductKardex = (id: number) => api.get(`/inventario/productos/${id}/kardex`);
export const apiImportProductsExcel = (formData: FormData) =>
  api.post('/inventario/productos/import-excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const apiExportProductsExcel = () =>
  api.get('/inventario/productos/export-excel', { responseType: 'blob' });

// ─── Employees / Payroll ───
export const apiGetEmployees = () => api.get('/nomina/empleados');
export const apiCreateEmployee = (data: any) => api.post('/nomina/empleados', data);
export const apiUpdateEmployee = (id: number, data: any) => api.put(`/nomina/empleados/${id}`, data);
export const apiDeleteEmployee = (id: number) => api.delete(`/nomina/empleados/${id}`);
export const apiCalculatePayroll = (data: { period: string }) => api.post('/nomina/rol/calcular', data);
export const apiGetPayrolls = (period: string) => api.get(`/nomina/rol?period=${period}`);
export const apiExportPayrollExcel = (period: string) =>
  api.get(`/nomina/rol/${period}/export-excel`, { responseType: 'blob' });
export const apiExportPayrollPDF = (period: string) =>
  api.get(`/nomina/rol/${period}/export-pdf`, { responseType: 'blob' });

// ─── Settings ───
export const apiGetCompanyConfig = (companyId: number) => api.get(`/companies/${companyId}/config`);
export const apiUpdateCompanyConfig = (companyId: number, data: any) => api.put(`/companies/${companyId}/config`, data);
export const apiUploadSignature = (companyId: number, formData: FormData) =>
  api.post(`/companies/${companyId}/firma`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const apiTestSMTP = (data: any) => api.post('/settings/test-smtp', data);
export const apiUpdateBackupKey = (data: { backup_key: string }) => api.post('/settings/backup-key', data);

// ─── Admin ───
export const apiGetAdminDashboard = () => api.get('/admin/dashboard/summary');
export const apiGetSystemHealth = () => api.get('/admin/system-health');
export const apiGetAdminUsers = () => api.get('/admin/users');
export const apiGetSecurityEvents = (limit = 50) => api.get(`/admin/security-events?limit=${limit}`);
export const apiExtendLicense = (userId: number, data: { period: string }) =>
  api.post(`/admin/users/${userId}/extend-license`, data);

// ─── Files ───
export const apiUploadFile = (formData: FormData, scanVt = false) =>
  api.post(`/files/upload?scan_vt=${scanVt}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export default api;
