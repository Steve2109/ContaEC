import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Users,
  Plus,
  Search,
  Pencil,
  Trash2,
  Calculator,
  Loader2,
  Download,
  FileSpreadsheet,
  ArrowLeft,
  X,
} from 'lucide-react';
import {
  apiGetEmployees,
  apiCreateEmployee,
  apiUpdateEmployee,
  apiDeleteEmployee,
  apiCalculatePayroll,
  apiGetPayrolls,
  apiExportPayrollExcel,
  apiExportPayrollPDF,
} from '../services/api';

interface Employee {
  id: number;
  nombres: string;
  apellidos: string;
  cedula: string;
  cargo: string;
  departamento: string;
  salario_base: number;
  tipo_contrato: string;
  fecha_ingreso: string;
  cargas_familiares: number;
  activo: boolean;
}

interface PayrollLine {
  id: number;
  employee_id: number;
  employee_name: string;
  period: string;
  dias_trabajados: number;
  salario: number;
  horas_extras: number;
  bonificaciones: number;
  comisiones: number;
  decimo_tercero_mensual: number;
  decimo_cuarto: number;
  fondos_reserva: number;
  total_ingresos: number;
  iess_personal: number;
  iess_patronal: number;
  retencion_ir: number;
  prestamos: number;
  anticipos: number;
  otros_descuentos: number;
  total_descuentos: number;
  neto_pagar: number;
}

const CONTRACT_TYPES = [
  'INDEFINIDO',
  'FIJO',
  'POR_HORAS',
  'TEMPORAL',
  'PRACTICAS',
];

const DEPARTMENTS = [
  'ADMINISTRACIÓN',
  'VENTAS',
  'PRODUCCIÓN',
  'LOGÍSTICA',
  'CONTABILIDAD',
  'TECNOLOGÍA',
  'RECURSOS HUMANOS',
  'MARKETING',
  'OTROS',
];

export default function Employees() {
  const { t } = useTranslation();

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [payrolls, setPayrolls] = useState<PayrollLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [showPayroll, setShowPayroll] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [payrollPeriod, setPayrollPeriod] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [calculatingPayroll, setCalculatingPayroll] = useState(false);

  const [form, setForm] = useState({
    nombres: '',
    apellidos: '',
    cedula: '',
    cargo: '',
    departamento: 'ADMINISTRACIÓN',
    salario_base: 0,
    tipo_contrato: 'INDEFINIDO',
    fecha_ingreso: '',
    cargas_familiares: 0,
    activo: true,
  });

  const fetchEmployees = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiGetEmployees();
      setEmployees(res.data || []);
    } catch (err) {
      console.error('Error cargando empleados:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPayrolls = useCallback(async () => {
    try {
      const res = await apiGetPayrolls(payrollPeriod);
      setPayrolls(res.data || []);
    } catch (err) {
      setPayrolls([]);
    }
  }, [payrollPeriod]);

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  useEffect(() => {
    if (showPayroll) fetchPayrolls();
  }, [showPayroll, fetchPayrolls]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingId) {
        await apiUpdateEmployee(editingId, form);
      } else {
        await apiCreateEmployee(form);
      }
      setShowForm(false);
      setEditingId(null);
      setForm({
        nombres: '', apellidos: '', cedula: '', cargo: '', departamento: 'ADMINISTRACIÓN',
        salario_base: 0, tipo_contrato: 'INDEFINIDO', fecha_ingreso: '', cargas_familiares: 0, activo: true,
      });
      await fetchEmployees();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error guardando empleado');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (emp: Employee) => {
    setForm({
      nombres: emp.nombres,
      apellidos: emp.apellidos,
      cedula: emp.cedula,
      cargo: emp.cargo,
      departamento: emp.departamento,
      salario_base: emp.salario_base,
      tipo_contrato: emp.tipo_contrato,
      fecha_ingreso: emp.fecha_ingreso?.slice(0, 10) || '',
      cargas_familiares: emp.cargas_familiares,
      activo: emp.activo,
    });
    setEditingId(emp.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await apiDeleteEmployee(id);
      setDeleteConfirm(null);
      await fetchEmployees();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error eliminando empleado');
    }
  };

  const handleCalculatePayroll = async () => {
    setCalculatingPayroll(true);
    try {
      await apiCalculatePayroll({ period: payrollPeriod });
      await fetchPayrolls();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error calculando nómina');
    } finally {
      setCalculatingPayroll(false);
    }
  };

  const handleExportExcel = async () => {
    try {
      const res = await apiExportPayrollExcel(payrollPeriod);
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rol_${payrollPeriod}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Error exportando');
    }
  };

  const handleExportPDF = async () => {
    try {
      const res = await apiExportPayrollPDF(payrollPeriod);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rol_${payrollPeriod}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Error exportando');
    }
  };

  const filtered = employees.filter(
    (e) =>
      e.nombres.toLowerCase().includes(search.toLowerCase()) ||
      e.apellidos.toLowerCase().includes(search.toLowerCase()) ||
      e.cedula.includes(search) ||
      e.cargo.toLowerCase().includes(search.toLowerCase())
  );

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(v || 0);

  if (showPayroll) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <button onClick={() => setShowPayroll(false)} className="rounded-md p-1 hover:bg-slate-100 dark:hover:bg-slate-700">
            <ArrowLeft className="h-5 w-5 text-slate-500" />
          </button>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{t('employees.payroll')}</h1>
        </div>

        <div className="flex items-center gap-4">
          <input
            type="month"
            value={payrollPeriod}
            onChange={(e) => setPayrollPeriod(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
          <button
            onClick={handleCalculatePayroll}
            disabled={calculatingPayroll}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {calculatingPayroll ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4" />}
            {t('employees.calculatePayroll')}
          </button>
          <button onClick={handleExportExcel} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300">
            <FileSpreadsheet className="h-4 w-4" /> Excel
          </button>
          <button onClick={handleExportPDF} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300">
            <Download className="h-4 w-4" /> PDF
          </button>
        </div>

        {payrolls.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white py-12 text-center dark:border-slate-700 dark:bg-slate-800">
            <Calculator className="mx-auto h-12 w-12 text-slate-300" />
            <p className="mt-4 text-slate-500 dark:text-slate-400">Sin roles calculados para este período</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 dark:bg-slate-700/50">
                <tr>
                  <th className="px-2 py-2 text-left">Empleado</th>
                  <th className="px-2 py-2 text-right">Salario</th>
                  <th className="px-2 py-2 text-right">Ingresos</th>
                  <th className="px-2 py-2 text-right">IESS</th>
                  <th className="px-2 py-2 text-right">IR</th>
                  <th className="px-2 py-2 text-right">Desc.</th>
                  <th className="px-2 py-2 text-right font-bold">Neto</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {payrolls.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                    <td className="px-2 py-2">
                      <p className="font-medium text-slate-900 dark:text-white">{p.employee_name}</p>
                      <p className="text-[10px] text-slate-500">{p.dias_trabajados} días</p>
                    </td>
                    <td className="px-2 py-2 text-right">{formatCurrency(p.salario)}</td>
                    <td className="px-2 py-2 text-right text-emerald-600">{formatCurrency(p.total_ingresos)}</td>
                    <td className="px-2 py-2 text-right text-red-500">{formatCurrency(p.iess_personal)}</td>
                    <td className="px-2 py-2 text-right text-red-500">{formatCurrency(p.retencion_ir)}</td>
                    <td className="px-2 py-2 text-right text-red-500">{formatCurrency(p.total_descuentos)}</td>
                    <td className="px-2 py-2 text-right font-bold text-slate-900 dark:text-white">{formatCurrency(p.neto_pagar)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{t('employees.title')}</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowPayroll(true)}
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
          >
            <Calculator className="h-4 w-4" />
            {t('employees.calculatePayroll')}
          </button>
          <button
            onClick={() => {
              setEditingId(null);
              setForm({
                nombres: '', apellidos: '', cedula: '', cargo: '', departamento: 'ADMINISTRACIÓN',
                salario_base: 0, tipo_contrato: 'INDEFINIDO', fecha_ingreso: '', cargas_familiares: 0, activo: true,
              });
              setShowForm(true);
            }}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            <Plus className="h-4 w-4" />
            {t('employees.newEmployee')}
          </button>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('common.search')}
          className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white py-12 text-center dark:border-slate-700 dark:bg-slate-800">
          <Users className="mx-auto h-12 w-12 text-slate-300" />
          <p className="mt-4 text-slate-500 dark:text-slate-400">{t('common.noData')}</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('employees.fullName')}</th>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('employees.position')}</th>
                <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">{t('employees.salary')}</th>
                <th className="px-4 py-3 text-center font-medium text-slate-700 dark:text-slate-300">{t('employees.contractType')}</th>
                <th className="px-4 py-3 text-center font-medium text-slate-700 dark:text-slate-300">Estado</th>
                <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {filtered.map((e) => (
                <tr key={e.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900 dark:text-white">{e.nombres} {e.apellidos}</p>
                    <p className="text-xs text-slate-500">{e.cedula} · {e.departamento}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{e.cargo}</td>
                  <td className="px-4 py-3 text-right text-slate-900 dark:text-white">{formatCurrency(e.salario_base)}</td>
                  <td className="px-4 py-3 text-center text-xs text-slate-500">{e.tipo_contrato}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      e.activo ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {e.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => handleEdit(e)} className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => setDeleteConfirm(e.id)} className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-slate-800">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {editingId ? 'Editar Empleado' : t('employees.newEmployee')}
              </h2>
              <button onClick={() => setShowForm(false)} className="rounded-md p-1 hover:bg-slate-100 dark:hover:bg-slate-700">
                <X className="h-5 w-5 text-slate-500" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Nombres *</label>
                  <input required value={form.nombres} onChange={(e) => setForm({ ...form, nombres: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Apellidos *</label>
                  <input required value={form.apellidos} onChange={(e) => setForm({ ...form, apellidos: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Cédula/RUC *</label>
                  <input required value={form.cedula} onChange={(e) => setForm({ ...form, cedula: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Cargo *</label>
                  <input required value={form.cargo} onChange={(e) => setForm({ ...form, cargo: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Departamento</label>
                  <select value={form.departamento} onChange={(e) => setForm({ ...form, departamento: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white">
                    {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Tipo Contrato</label>
                  <select value={form.tipo_contrato} onChange={(e) => setForm({ ...form, tipo_contrato: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white">
                    {CONTRACT_TYPES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('employees.salary')}</label>
                  <input type="number" step="0.01" min="0" value={form.salario_base} onChange={(e) => setForm({ ...form, salario_base: parseFloat(e.target.value) || 0 })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('employees.startDate')}</label>
                  <input type="date" value={form.fecha_ingreso} onChange={(e) => setForm({ ...form, fecha_ingreso: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('employees.familyBurden')}</label>
                <input type="number" min="0" value={form.cargas_familiares} onChange={(e) => setForm({ ...form, cargas_familiares: parseInt(e.target.value) || 0 })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
              </div>
              <div className="flex items-center gap-2">
                <input id="emp_activo" type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-emerald-600" />
                <label htmlFor="emp_activo" className="text-sm text-slate-700 dark:text-slate-300">Empleado activo</label>
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowForm(false)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-300">{t('common.cancel')}</button>
                <button type="submit" disabled={submitting} className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">
                  {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editingId ? t('common.save') : t('common.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteConfirm !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-800">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">¿Eliminar empleado?</h3>
            <p className="mt-2 text-sm text-slate-500">Esta acción no se puede deshacer.</p>
            <div className="mt-4 flex justify-end gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-300">{t('common.cancel')}</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">{t('common.delete')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
