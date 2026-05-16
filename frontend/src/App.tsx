import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useStore } from './store/useStore';
import { authService, companyService, licenseService } from './services/api';

// Páginas
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Companies from './pages/Companies';
import Invoices from './pages/Invoices';
import Products from './pages/Products';
import Employees from './pages/Employees';
import AdminPanel from './pages/AdminPanel';
import Settings from './pages/Settings';

// Componentes de Layout
import Sidebar from './components/Sidebar';
import Header from './components/Header';

// Protected Route
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = useStore((state) => state.token);
  if (!token) return <Navigate to="/login" replace />;
  return <div className="flex h-screen bg-light-bg dark:bg-gray-900">{children}</div>;
};

const App: React.FC = () => {
  const { setUser, setToken, setCompanies, setCurrentCompany, setLicense, isDarkMode } = useStore();

  useEffect(() => {
    const initApp = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          setToken(token);
          const userData = await authService.me();
          setUser(userData);
          const companies = await companyService.getAll();
          setCompanies(companies);
          if (companies.length > 0) {
            setCurrentCompany(companies[0]);
          }
          const license = await licenseService.getMyLicense();
          setLicense(license);
        } catch (error) {
          console.error('Error initializing app:', error);
          localStorage.removeItem('token');
        }
      }
    };
    initApp();
  }, [setUser, setToken, setCompanies, setCurrentCompany, setLicense]);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route path="/" element={
          <ProtectedRoute>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                <Dashboard />
              </main>
            </div>
          </ProtectedRoute>
        } />
        
        <Route path="/companies" element={
          <ProtectedRoute>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                <Companies />
              </main>
            </div>
          </ProtectedRoute>
        } />
        
        <Route path="/invoices" element={
          <ProtectedRoute>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                <Invoices />
              </main>
            </div>
          </ProtectedRoute>
        } />
        
        <Route path="/products" element={
          <ProtectedRoute>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                <Products />
              </main>
            </div>
          </ProtectedRoute>
        } />
        
        <Route path="/employees" element={
          <ProtectedRoute>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                <Employees />
              </main>
            </div>
          </ProtectedRoute>
        } />
        
        <Route path="/admin" element={
          <ProtectedRoute>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                <AdminPanel />
              </main>
            </div>
          </ProtectedRoute>
        } />
        
        <Route path="/settings" element={
          <ProtectedRoute>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                <Settings />
              </main>
            </div>
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
