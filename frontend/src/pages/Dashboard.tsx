import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Package,
  Users,
  DollarSign,
  AlertTriangle,
  Clock,
  ArrowRight,
  Building2,
  Calculator,
  Settings,
  BarChart3,
} from 'lucide-react';
import {
  apiGetDashboardStats,
  apiGetRecentActivity,
  apiGetLicenseStatus,
} from '../services/api';
import { useStore } from '../store/useStore';

interface DashboardStats {
  invoices_month: number;
  products_active: number;
  clients_total: number;
  revenue_month: number;
  pending_invoices: number;
  low_stock_count: number;
}

interface ActivityItem {
  id: number;
  action: string;
  entity: string;
  entity_id: number;
  timestamp: string;
  user_name: string;
}

interface LicenseStatus {
  valid: boolean;
  type: string;
  expiry_date: string;
  days_remaining: number;
}

export default function Dashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, currentCompany } = useStore();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [license, setLicense] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsRes, activityRes, licenseRes] = await Promise.all([
          apiGetDashboardStats(),
          apiGetRecentActivity(10),
          apiGetLicenseStatus(),
        ]);
        setStats(statsRes.data);
        setActivities(activityRes.data || []);
        setLicense(licenseRes.data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Error cargando dashboard');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [currentCompany?.id]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-EC', {
      style: 'currency',
      currency: 'USD',
    }).format(value || 0);
  };

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleDateString('es-EC', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        <AlertTriangle className="inline h-4 w-4 mr-2" />
        {error}
      </div>
    );
  }

  const statCards = [
    {
      label: t('dashboard.stats.invoices'),
      value: stats?.invoices_month ?? 0,
      icon: FileText,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      onClick: () => navigate('/invoices'),
    },
    {
      label: t('dashboard.stats.products'),
      value: stats?.products_active ?? 0,
      icon: Package,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
      onClick: () => navigate('/products'),
    },
    {
      label: t('dashboard.stats.clients'),
      value: stats?.clients_total ?? 0,
      icon: Users,
      color: 'text-violet-600',
      bg: 'bg-violet-50',
      onClick: () => {},
    },
    {
      label: t('dashboard.stats.revenue'),
      value: formatCurrency(stats?.revenue_month || 0),
      icon: DollarSign,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      onClick: () => {},
    },
    {
      label: t('dashboard.stats.pendingInvoices'),
      value: stats?.pending_invoices ?? 0,
      icon: Clock,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
      onClick: () => navigate('/invoices'),
    },
    {
      label: t('dashboard.stats.lowStock'),
      value: stats?.low_stock_count ?? 0,
      icon: AlertTriangle,
      color: 'text-red-600',
      bg: 'bg-red-50',
      onClick: () => navigate('/products'),
    },
  ];

  const quickActions = [
    { label: t('companies.newCompany'), icon: Building2, path: '/companies', color: 'bg-blue-600' },
    { label: t('invoices.newInvoice'), icon: FileText, path: '/invoices', color: 'bg-emerald-600' },
    { label: t('products.newProduct'), icon: Package, path: '/products', color: 'bg-violet-600' },
    { label: t('employees.calculatePayroll'), icon: Calculator, path: '/employees', color: 'bg-amber-600' },
    { label: t('settings.title'), icon: Settings, path: '/settings', color: 'bg-slate-600' },
    { label: t('nav.admin'), icon: BarChart3, path: '/admin', color: 'bg-rose-600' },
  ];

  const showLicenseAlert = license && license.days_remaining <= 15 && license.days_remaining > 0;
  const licenseExpired = license && license.days_remaining <= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
          {t('dashboard.welcome', { name: user?.full_name || user?.email || '' })}
        </h1>
        {currentCompany && (
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Empresa activa: <span className="font-medium">{currentCompany.razon_social}</span>
            {currentCompany.sandbox_mode && (
              <span className="ml-2 inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                🧪 Sandbox
              </span>
            )}
          </p>
        )}
      </div>

      {/* License alerts */}
      {licenseExpired && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <div>
              <p className="font-medium text-red-800">Licencia vencida</p>
              <p className="text-sm text-red-600">
                Tu licencia venció el {new Date(license.expiry_date).toLocaleDateString('es-EC')}. Renueva para continuar usando el sistema.
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/settings')}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            {t('dashboard.licenseAlert.renew')}
          </button>
        </div>
      )}

      {showLicenseAlert && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Clock className="h-5 w-5 text-amber-600" />
            <div>
              <p className="font-medium text-amber-800">{t('dashboard.licenseAlert.title')}</p>
              <p className="text-sm text-amber-700">
                {t('dashboard.licenseAlert.message', { days: license?.days_remaining })}
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/settings')}
            className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            {t('dashboard.licenseAlert.renew')}
          </button>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {statCards.map((card) => (
          <button
            key={card.label}
            onClick={card.onClick}
            className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:shadow-md dark:border-slate-700 dark:bg-slate-800"
          >
            <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${card.bg}`}>
              <card.icon className={`h-6 w-6 ${card.color}`} />
            </div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">{card.label}</p>
              <p className="text-xl font-semibold text-slate-900 dark:text-white">{card.value}</p>
            </div>
          </button>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-3">
          {t('dashboard.quickActions')}
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {quickActions.map((action) => (
            <button
              key={action.path}
              onClick={() => navigate(action.path)}
              className="flex flex-col items-center gap-2 rounded-xl border border-slate-200 bg-white p-4 transition hover:shadow-md dark:border-slate-700 dark:bg-slate-800"
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${action.color}`}>
                <action.icon className="h-5 w-5 text-white" />
              </div>
              <span className="text-xs font-medium text-slate-700 dark:text-slate-300 text-center">
                {action.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Recent activity */}
      <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 dark:border-slate-700">
          <h3 className="font-semibold text-slate-900 dark:text-white">
            {t('dashboard.recentActivity')}
          </h3>
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-700">
          {activities.length === 0 ? (
            <p className="px-4 py-6 text-sm text-slate-500 dark:text-slate-400 text-center">
              {t('common.noData')}
            </p>
          ) : (
            activities.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700">
                    <ArrowRight className="h-4 w-4 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900 dark:text-white">
                      {item.action} — {item.entity} #{item.entity_id}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {item.user_name} · {formatDate(item.timestamp)}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
