import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarChart3,
  Users,
  Shield,
  Server,
  Loader2,
  AlertTriangle,
  CheckCircle,
  Clock,
  RefreshCw,
  ArrowUpDown,
} from 'lucide-react';
import {
  apiGetAdminDashboard,
  apiGetSystemHealth,
  apiGetAdminUsers,
  apiGetSecurityEvents,
  apiExtendLicense,
} from '../services/api';

interface AdminStats {
  total_users: number;
  active_licenses: number;
  expired_licenses: number;
  near_expiry: number;
  total_invoices: number;
  total_revenue: number;
}

interface SystemHealth {
  uptime_seconds: number;
  db_status: 'connected' | 'disconnected';
  clamav_status: 'running' | 'stopped' | 'not_installed';
  disk_usage_percent: number;
  memory_usage_percent: number;
  version: string;
}

interface AdminUser {
  id: number;
  full_name: string;
  email: string;
  license_type: string;
  license_expiry: string;
  days_remaining: number;
  is_active: boolean;
  companies_count: number;
}

interface SecurityEvent {
  id: number;
  user_email: string;
  event_type: string;
  description: string;
  created_at: string;
}

export default function AdminPanel() {
  const { t } = useTranslation();

  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'security' | 'health'>('overview');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [extendingUserId, setExtendingUserId] = useState<number | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, healthRes, usersRes, eventsRes] = await Promise.all([
        apiGetAdminDashboard(),
        apiGetSystemHealth(),
        apiGetAdminUsers(),
        apiGetSecurityEvents(50),
      ]);
      setStats(statsRes.data);
      setHealth(healthRes.data);
      setUsers(usersRes.data || []);
      setEvents(eventsRes.data || []);
    } catch (err: any) {
      console.error('Error cargando panel admin:', err);
      if (err?.response?.status === 403) {
        alert('Acceso denegado: credenciales de administrador requeridas');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleExtendLicense = async (userId: number, period: string) => {
    setExtendingUserId(userId);
    try {
      await apiExtendLicense(userId, { period });
      await fetchAll();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error extendiendo licencia');
    } finally {
      setExtendingUserId(null);
    }
  };

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(v || 0);

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${mins}m`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Resumen', icon: BarChart3 },
    { id: 'users', label: t('admin.users'), icon: Users },
    { id: 'health', label: t('admin.systemHealth'), icon: Server },
    { id: 'security', label: t('admin.security'), icon: Shield },
  ] as const;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{t('admin.title')}</h1>
        <button
          onClick={fetchAll}
          className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300"
        >
          <RefreshCw className="h-4 w-4" />
          Actualizar
        </button>
      </div>

      <div className="flex gap-2 border-b border-slate-200 pb-1 dark:border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 rounded-t-lg px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.id
                ? 'border-b-2 border-emerald-600 text-emerald-600'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === 'overview' && stats && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: t('admin.totalUsers'), value: stats.total_users, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
              { label: t('admin.activeLicenses'), value: stats.active_licenses, icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50' },
              { label: t('admin.expiredLicenses'), value: stats.expired_licenses, icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
              { label: t('admin.nearExpiry'), value: stats.near_expiry, icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50' },
            ].map((s) => (
              <div key={s.label} className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
                <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${s.bg}`}>
                  <s.icon className={`h-6 w-6 ${s.color}`} />
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{s.label}</p>
                  <p className="text-2xl font-semibold text-slate-900 dark:text-white">{s.value}</p>
                </div>
              </div>
            ))}
          </div>

          {health && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Estado del Sistema</h3>
              <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-slate-500">{t('admin.systemUptime')}</p>
                  <p className="text-lg font-medium text-slate-900 dark:text-white">{formatUptime(health.uptime_seconds)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">{t('admin.dbStatus')}</p>
                  <p className={`text-lg font-medium ${health.db_status === 'connected' ? 'text-emerald-600' : 'text-red-600'}`}>
                    {health.db_status === 'connected' ? 'Conectado' : 'Desconectado'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">{t('admin.clamavStatus')}</p>
                  <p className={`text-lg font-medium ${health.clamav_status === 'running' ? 'text-emerald-600' : 'text-amber-600'}`}>
                    {health.clamav_status === 'running' ? 'Activo' : health.clamav_status === 'stopped' ? 'Detenido' : 'No instalado'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Versión</p>
                  <p className="text-lg font-medium text-slate-900 dark:text-white">{health.version}</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div>
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>{t('admin.diskUsage')}</span>
                    <span>{health.disk_usage_percent}%</span>
                  </div>
                  <div className="mt-1 h-2 rounded-full bg-slate-100 dark:bg-slate-700">
                    <div
                      className={`h-2 rounded-full ${health.disk_usage_percent > 80 ? 'bg-red-500' : health.disk_usage_percent > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${health.disk_usage_percent}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>{t('admin.memoryUsage')}</span>
                    <span>{health.memory_usage_percent}%</span>
                  </div>
                  <div className="mt-1 h-2 rounded-full bg-slate-100 dark:bg-slate-700">
                    <div
                      className={`h-2 rounded-full ${health.memory_usage_percent > 80 ? 'bg-red-500' : health.memory_usage_percent > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${health.memory_usage_percent}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Users & Licenses */}
      {activeTab === 'users' && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('admin.userTable.name')}</th>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('admin.userTable.email')}</th>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('admin.userTable.licenseType')}</th>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('admin.userTable.expiryDate')}</th>
                <th className="px-4 py-3 text-center font-medium text-slate-700 dark:text-slate-300">{t('admin.userTable.status')}</th>
                <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">{t('admin.userTable.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">{t('common.noData')}</td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900 dark:text-white">{u.full_name}</p>
                      <p className="text-xs text-slate-500">{u.companies_count} empresa(s)</p>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{u.email}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                      {t(`admin.licenseTypes.${u.license_type.toLowerCase()}`) || u.license_type}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        <span className={u.days_remaining <= 0 ? 'text-red-600' : u.days_remaining <= 15 ? 'text-amber-600' : 'text-slate-600 dark:text-slate-300'}>
                          {new Date(u.license_expiry).toLocaleDateString('es-EC')}
                          <span className="ml-1 text-xs">({u.days_remaining}d)</span>
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        u.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {u.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        {['monthly', 'quarterly', 'semiannual', 'annual'].map((period) => (
                          <button
                            key={period}
                            onClick={() => handleExtendLicense(u.id, period)}
                            disabled={extendingUserId === u.id}
                            className="rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-emerald-50 hover:text-emerald-700 disabled:opacity-50 dark:text-slate-300"
                            title={`Extender ${period}`}
                          >
                            {extendingUserId === u.id ? <Loader2 className="h-3 w-3 animate-spin" /> : period[0].toUpperCase()}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* System Health */}
      {activeTab === 'health' && health && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: 'Uptime', value: formatUptime(health.uptime_seconds), status: 'ok' },
              { label: 'Base de Datos', value: health.db_status === 'connected' ? 'Conectado' : 'Error', status: health.db_status === 'connected' ? 'ok' : 'error' },
              { label: 'ClamAV', value: health.clamav_status === 'running' ? 'Activo' : health.clamav_status === 'stopped' ? 'Detenido' : 'No instalado', status: health.clamav_status === 'running' ? 'ok' : 'warn' },
              { label: 'Disco', value: `${health.disk_usage_percent}%`, status: health.disk_usage_percent > 80 ? 'error' : health.disk_usage_percent > 60 ? 'warn' : 'ok' },
              { label: 'Memoria', value: `${health.memory_usage_percent}%`, status: health.memory_usage_percent > 80 ? 'error' : health.memory_usage_percent > 60 ? 'warn' : 'ok' },
              { label: 'Versión', value: health.version, status: 'ok' },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-slate-500">{item.label}</p>
                  {item.status === 'ok' && <CheckCircle className="h-4 w-4 text-emerald-500" />}
                  {item.status === 'warn' && <AlertTriangle className="h-4 w-4 text-amber-500" />}
                  {item.status === 'error' && <AlertTriangle className="h-4 w-4 text-red-500" />}
                </div>
                <p className={`mt-1 text-lg font-semibold ${
                  item.status === 'ok' ? 'text-slate-900 dark:text-white' :
                  item.status === 'warn' ? 'text-amber-600' : 'text-red-600'
                }`}>
                  {item.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security Events */}
      {activeTab === 'security' && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('admin.eventType')}</th>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('admin.userTable.email')}</th>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('admin.eventDetails')}</th>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('admin.eventDate')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">Sin eventos registrados</td>
                </tr>
              ) : (
                events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        ev.event_type.includes('MALWARE') ? 'bg-red-100 text-red-700' :
                        ev.event_type.includes('LOGIN') ? 'bg-blue-100 text-blue-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {ev.event_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{ev.user_email}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{ev.description}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {new Date(ev.created_at).toLocaleString('es-EC')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
