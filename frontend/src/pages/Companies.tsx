import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Plus,
  Search,
  Pencil,
  Trash2,
  Upload,
  CheckCircle,
  AlertCircle,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import {
  apiGetCompanies,
  apiCreateCompany,
  apiUpdateCompany,
  apiDeleteCompany,
  apiQueryRucSRI,
  apiUploadLogo,
} from '../services/api';
import { useStore } from '../store/useStore';

interface Company {
  id: number;
  ruc: string;
  razon_social: string;
  nombre_comercial: string;
  direccion: string;
  telefono: string;
  email: string;
  logo_url: string | null;
  tipo_contribuyente: string;
  obligado_contabilidad: boolean;
  sandbox_mode: boolean;
  estado: string;
  firma_valida_hasta: string | null;
}

interface CompanyForm {
  ruc: string;
  razon_social: string;
  nombre_comercial: string;
  direccion: string;
  telefono: string;
  email: string;
  tipo_contribuyente: string;
  obligado_contabilidad: boolean;
  sandbox_mode: boolean;
}

const EMPTY_FORM: CompanyForm = {
  ruc: '',
  razon_social: '',
  nombre_comercial: '',
  direccion: '',
  telefono: '',
  email: '',
  tipo_contribuyente: 'RIMPE_EMPRENDEDOR',
  obligado_contabilidad: false,
  sandbox_mode: true,
};

export default function Companies() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setCurrentCompany } = useStore();

  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<CompanyForm>(EMPTY_FORM);
  const [sriLoading, setSriLoading] = useState(false);
  const [sriError, setSriError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);

  const fetchCompanies = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiGetCompanies();
      setCompanies(res.data || []);
    } catch (err: any) {
      console.error('Error cargando empresas:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  const handleQuerySRI = async () => {
    const ruc = form.ruc.trim();
    if (!ruc || ruc.length !== 13) {
      setSriError('El RUC debe tener 13 dígitos');
      return;
    }
    setSriLoading(true);
    setSriError(null);
    try {
      const res = await apiQueryRucSRI(ruc);
      const data = res.data;
      if (data.valido) {
        setForm((prev) => ({
          ...prev,
          razon_social: data.razon_social || prev.razon_social,
          nombre_comercial: data.nombre_comercial || data.razon_social || prev.nombre_comercial,
          direccion: data.direccion || prev.direccion,
          telefono: data.telefono || prev.telefono,
          email: data.email || prev.email,
          tipo_contribuyente: data.tipo_contribuyente || prev.tipo_contribuyente,
          obligado_contabilidad: data.obligado_contabilidad || false,
        }));
      } else {
        setSriError(data.mensaje || 'RUC no encontrado en el SRI');
      }
    } catch (err: any) {
      setSriError(err?.response?.data?.detail || 'Error consultando SRI');
    } finally {
      setSriLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      let companyId: number;
      if (editingId) {
        const res = await apiUpdateCompany(editingId, form);
        companyId = editingId;
      } else {
        const res = await apiCreateCompany(form);
        companyId = res.data.id;
      }

      // Subir logo si hay uno seleccionado
      if (logoFile && companyId) {
        const logoData = new FormData();
        logoData.append('file', logoFile);
        await apiUploadLogo(companyId, logoData);
      }

      setShowModal(false);
      setForm(EMPTY_FORM);
      setLogoFile(null);
      setEditingId(null);
      await fetchCompanies();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error guardando empresa');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (company: Company) => {
    setForm({
      ruc: company.ruc,
      razon_social: company.razon_social,
      nombre_comercial: company.nombre_comercial,
      direccion: company.direccion,
      telefono: company.telefono,
      email: company.email,
      tipo_contribuyente: company.tipo_contribuyente,
      obligado_contabilidad: company.obligado_contabilidad,
      sandbox_mode: company.sandbox_mode,
    });
    setEditingId(company.id);
    setShowModal(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await apiDeleteCompany(id);
      setDeleteConfirm(null);
      await fetchCompanies();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error eliminando empresa');
    }
  };

  const handleSelectCompany = (company: Company) => {
    setCurrentCompany(company);
    navigate('/dashboard');
  };

  const filtered = companies.filter(
    (c) =>
      c.razon_social.toLowerCase().includes(search.toLowerCase()) ||
      c.ruc.includes(search) ||
      c.nombre_comercial.toLowerCase().includes(search.toLowerCase())
  );

  const tipoOptions = [
    'RIMPE_EMPRENDEDOR',
    'RIMPE_POPULAR',
    'RIMPE_ESPECIAL',
    'GENERAL',
    'CONTRIBUYENTE_ESPECIAL',
    'SECTOR_PUBLICO',
    'PERSONA_NATURAL',
    'PERSONA_JURIDICA',
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{t('companies.title')}</h1>
        <button
          onClick={() => {
            setForm(EMPTY_FORM);
            setEditingId(null);
            setLogoFile(null);
            setShowModal(true);
          }}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        >
          <Plus className="h-4 w-4" />
          {t('companies.newCompany')}
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('common.search')}
          className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
        />
      </div>

      {/* Companies grid */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white py-12 text-center dark:border-slate-700 dark:bg-slate-800">
          <Building2 className="mx-auto h-12 w-12 text-slate-300" />
          <p className="mt-4 text-slate-500 dark:text-slate-400">{t('companies.noCompanies')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((company) => (
            <div
              key={company.id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-slate-700 dark:bg-slate-800"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {company.logo_url ? (
                    <img src={company.logo_url} alt="" className="h-12 w-12 rounded-lg object-cover" />
                  ) : (
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-700">
                      <Building2 className="h-6 w-6 text-slate-400" />
                    </div>
                  )}
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-white">{company.razon_social}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">RUC: {company.ruc}</p>
                  </div>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleEdit(company)}
                    className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(company.id)}
                    className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="mt-4 space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <p>{company.nombre_comercial}</p>
                <p className="text-slate-500 dark:text-slate-400">{company.direccion}</p>
                <p className="text-slate-500 dark:text-slate-400">
                  {company.telefono} · {company.email}
                </p>
              </div>

              <div className="mt-4 flex items-center gap-2">
                {company.sandbox_mode && (
                  <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                    🧪 Sandbox
                  </span>
                )}
                {company.firma_valida_hasta && (
                  <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
                    <CheckCircle className="mr-1 h-3 w-3" />
                    Firma válida hasta {new Date(company.firma_valida_hasta).toLocaleDateString('es-EC')}
                  </span>
                )}
                {!company.firma_valida_hasta && (
                  <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                    <AlertCircle className="mr-1 h-3 w-3" />
                    Sin firma electrónica
                  </span>
                )}
              </div>

              <button
                onClick={() => handleSelectCompany(company)}
                className="mt-4 flex w-full items-center justify-center gap-1 rounded-lg border border-slate-200 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                <ExternalLink className="h-4 w-4" />
                Seleccionar como empresa activa
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Modal: Create/Edit */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-slate-800">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              {editingId ? 'Editar Empresa' : t('companies.newCompany')}
            </h2>

            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
              {/* RUC + Consulta SRI */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    {t('companies.rucLabel')} *
                  </label>
                  <input
                    required
                    maxLength={13}
                    value={form.ruc}
                    onChange={(e) => setForm({ ...form, ruc: e.target.value.replace(/\D/g, '').slice(0, 13) })}
                    placeholder={t('companies.rucPlaceholder')}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    type="button"
                    onClick={handleQuerySRI}
                    disabled={sriLoading || form.ruc.length !== 13}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300"
                  >
                    {sriLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}
                    {sriLoading ? t('companies.consultando') : t('companies.consultarSRI')}
                  </button>
                </div>
              </div>
              {sriError && (
                <p className="rounded-md bg-red-50 p-2 text-xs text-red-600">{sriError}</p>
              )}

              {/* Razón social, Nombre comercial */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    {t('companies.razonSocial')} *
                  </label>
                  <input
                    required
                    value={form.razon_social}
                    onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    {t('companies.nombreComercial')}
                  </label>
                  <input
                    value={form.nombre_comercial}
                    onChange={(e) => setForm({ ...form, nombre_comercial: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Dirección, Teléfono, Email */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  {t('companies.direccion')}
                </label>
                <input
                  value={form.direccion}
                  onChange={(e) => setForm({ ...form, direccion: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    {t('companies.telefono')}
                  </label>
                  <input
                    value={form.telefono}
                    onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    {t('companies.email')}
                  </label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Tipo contribuyente + obligado */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    {t('companies.tipoContribuyente')}
                  </label>
                  <select
                    value={form.tipo_contribuyente}
                    onChange={(e) => setForm({ ...form, tipo_contribuyente: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    {tipoOptions.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-3 pt-6">
                  <input
                    id="obligado"
                    type="checkbox"
                    checked={form.obligado_contabilidad}
                    onChange={(e) => setForm({ ...form, obligado_contabilidad: e.target.checked })}
                    className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <label htmlFor="obligado" className="text-sm text-slate-700 dark:text-slate-300">
                    {t('companies.obligadoContabilidad')}
                  </label>
                </div>
              </div>

              {/* Sandbox mode */}
              <div className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <input
                  id="sandbox"
                  type="checkbox"
                  checked={form.sandbox_mode}
                  onChange={(e) => setForm({ ...form, sandbox_mode: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                />
                <div>
                  <label htmlFor="sandbox" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {t('companies.sandboxMode')}
                  </label>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{t('companies.sandboxHelp')}</p>
                </div>
              </div>

              {/* Logo upload */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  {t('companies.logo')}
                </label>
                <div className="mt-1 flex items-center gap-3">
                  <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300">
                    <Upload className="h-4 w-4" />
                    {logoFile ? logoFile.name : 'Seleccionar imagen'}
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => setLogoFile(e.target.files?.[0] || null)}
                    />
                  </label>
                  {logoFile && (
                    <button type="button" onClick={() => setLogoFile(null)} className="text-xs text-red-600">
                      Quitar
                    </button>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editingId ? t('common.save') : t('common.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      {deleteConfirm !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-800">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">¿Eliminar empresa?</h3>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Esta acción no se puede deshacer. Se eliminarán todos los datos asociados a esta empresa.
            </p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-300"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
