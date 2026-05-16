import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useStore } from './store/useStore';
import { apiGetMe } from './services/api';

import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Companies from './pages/Companies';
import Invoices from './pages/Invoices';
import Products from './pages/Products';
import Employees from './pages/Employees';
import Settings from './pages/Settings';
import AdminPanel from './pages/AdminPanel';

function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { user, darkMode, toggleDarkMode } = useStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  };

  return (
    <div className={`min-h-screen ${darkMode ? 'dark bg-slate-900' : 'bg-slate-50'}`}>
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNavigate={(path) => { navigate(path); setSidebarOpen(false); }}
        onLogout={handleLogout}
        isAdmin={user?.is_admin || false}
      />
      <div className="lg:ml-64">
        <Header
          onMenuClick={() => setSidebarOpen(true)}
          onToggleTheme={toggleDarkMode}
          darkMode={darkMode}
        />
        <main className="p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}

function RequireAuth({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { user, loading } = useStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        navigate('/login');
      } else if (adminOnly && !user.is_admin) {
        navigate('/dashboard');
      }
    }
  }, [user, loading, navigate, adminOnly]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-600" />
      </div>
    );
  }

  if (!user || (adminOnly && !user.is_admin)) return null;

  return <Layout>{children}</Layout>;
}

export default function App() {
  const { user, setUser, setLoading } = useStore();
  const { i18n } = useTranslation();
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const res = await apiGetMe();
          setUser(res.data);
          // Restore language from user preference if available
          if (res.data.language && res.data.language !== i18n.language) {
            i18n.changeLanguage(res.data.language);
          }
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
      }
      setLoading(false);
      setInitializing(false);
    };
    init();
  }, []);

  if (initializing) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-600" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/companies" element={<RequireAuth><Companies /></RequireAuth>} />
      <Route path="/invoices" element={<RequireAuth><Invoices /></RequireAuth>} />
      <Route path="/products" element={<RequireAuth><Products /></RequireAuth>} />
      <Route path="/employees" element={<RequireAuth><Employees /></RequireAuth>} />
      <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
      <Route path="/admin" element={<RequireAuth adminOnly><AdminPanel /></RequireAuth>} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
