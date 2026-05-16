import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Package,
  Plus,
  Search,
  Pencil,
  Trash2,
  Upload,
  Download,
  Loader2,
  AlertTriangle,
  ArrowUpDown,
  X,
} from 'lucide-react';
import {
  apiGetProducts,
  apiCreateProduct,
  apiUpdateProduct,
  apiDeleteProduct,
  apiGetProductKardex,
  apiImportProductsExcel,
  apiExportProductsExcel,
} from '../services/api';

interface Product {
  id: number;
  codigo: string;
  nombre: string;
  categoria_id: number | null;
  categoria_nombre?: string;
  precio_venta: number;
  costo: number;
  stock: number;
  stock_minimo: number;
  unidad_medida: string;
  iva_code: string;
  ice_code: string | null;
  activo: boolean;
}

interface KardexEntry {
  id: number;
  fecha: string;
  tipo: string; // ENTRADA | SALIDA | AJUSTE
  cantidad: number;
  stock_resultante: number;
  documento_ref: string;
  observacion: string;
}

const IVA_OPTIONS = [
  { code: '0', label: '0%' },
  { code: '2', label: '12%' },
  { code: '3', label: '13%' },
  { code: '4', label: '14%' },
  { code: '5', label: '15%' },
  { code: '6', label: 'No Objeto' },
  { code: '7', label: 'Exento' },
];

const ICE_OPTIONS = [
  { code: '0', label: 'Sin ICE' },
  { code: '3011', label: 'Bebidas Alcohólicas (35%)' },
  { code: '3041', label: 'Tabacos (55%)' },
  { code: '3151', label: 'Bebidas Azucaradas (18%)' },
];

export default function Products() {
  const { t } = useTranslation();

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [kardexProduct, setKardexProduct] = useState<Product | null>(null);
  const [kardexData, setKardexData] = useState<KardexEntry[]>([]);
  const [kardexLoading, setKardexLoading] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);

  const [form, setForm] = useState({
    codigo: '',
    nombre: '',
    categoria_id: null as number | null,
    precio_venta: 0,
    costo: 0,
    stock: 0,
    stock_minimo: 5,
    unidad_medida: 'UNIDAD',
    iva_code: '2',
    ice_code: '0',
    activo: true,
  });

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiGetProducts();
      setProducts(res.data || []);
    } catch (err: any) {
      console.error('Error cargando productos:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingId) {
        await apiUpdateProduct(editingId, form);
      } else {
        await apiCreateProduct(form);
      }
      setShowForm(false);
      setEditingId(null);
      setForm({
        codigo: '', nombre: '', categoria_id: null, precio_venta: 0, costo: 0,
        stock: 0, stock_minimo: 5, unidad_medida: 'UNIDAD', iva_code: '2', ice_code: '0', activo: true,
      });
      await fetchProducts();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error guardando producto');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (product: Product) => {
    setForm({
      codigo: product.codigo,
      nombre: product.nombre,
      categoria_id: product.categoria_id,
      precio_venta: product.precio_venta,
      costo: product.costo,
      stock: product.stock,
      stock_minimo: product.stock_minimo,
      unidad_medida: product.unidad_medida,
      iva_code: product.iva_code,
      ice_code: product.ice_code || '0',
      activo: product.activo,
    });
    setEditingId(product.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await apiDeleteProduct(id);
      setDeleteConfirm(null);
      await fetchProducts();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error eliminando producto');
    }
  };

  const handleShowKardex = async (product: Product) => {
    setKardexProduct(product);
    setKardexLoading(true);
    try {
      const res = await apiGetProductKardex(product.id);
      setKardexData(res.data || []);
    } catch (err) {
      setKardexData([]);
    } finally {
      setKardexLoading(false);
    }
  };

  const handleImport = async () => {
    if (!importFile) return;
    setImporting(true);
    const data = new FormData();
    data.append('file', importFile);
    try {
      await apiImportProductsExcel(data);
      setImportFile(null);
      await fetchProducts();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error importando');
    } finally {
      setImporting(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await apiExportProductsExcel();
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `productos_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Error exportando');
    }
  };

  const filtered = products.filter(
    (p) =>
      p.nombre.toLowerCase().includes(search.toLowerCase()) ||
      p.codigo.toLowerCase().includes(search.toLowerCase())
  );

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(v || 0);

  const lowStock = products.filter((p) => p.stock <= p.stock_minimo);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{t('products.title')}</h1>
        <div className="flex gap-2">
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <Upload className="h-4 w-4" />
            {importFile ? importFile.name : 'Importar Excel'}
            <input
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={(e) => setImportFile(e.target.files?.[0] || null)}
            />
          </label>
          {importFile && (
            <button
              onClick={handleImport}
              disabled={importing}
              className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Subir
            </button>
          )}
          <button
            onClick={handleExport}
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
          >
            <Download className="h-4 w-4" />
            Exportar
          </button>
          <button
            onClick={() => {
              setEditingId(null);
              setForm({
                codigo: '', nombre: '', categoria_id: null, precio_venta: 0, costo: 0,
                stock: 0, stock_minimo: 5, unidad_medida: 'UNIDAD', iva_code: '2', ice_code: '0', activo: true,
              });
              setShowForm(true);
            }}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            <Plus className="h-4 w-4" />
            {t('products.newProduct')}
          </button>
        </div>
      </div>

      {/* Low stock alert */}
      {lowStock.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 flex items-center gap-2 text-sm text-red-700">
          <AlertTriangle className="h-4 w-4" />
          {lowStock.length} producto(s) con stock bajo o crítico.
        </div>
      )}

      {/* Search */}
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
          <Package className="mx-auto h-12 w-12 text-slate-300" />
          <p className="mt-4 text-slate-500 dark:text-slate-400">{t('common.noData')}</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('products.code')}</th>
                <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('products.name')}</th>
                <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">{t('products.price')}</th>
                <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">{t('products.stock')}</th>
                <th className="px-4 py-3 text-center font-medium text-slate-700 dark:text-slate-300">{t('products.iva')}</th>
                <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {filtered.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                  <td className="px-4 py-3 font-mono text-slate-500 dark:text-slate-400">{p.codigo}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900 dark:text-white">{p.nombre}</p>
                    {p.categoria_nombre && (
                      <p className="text-xs text-slate-500">{p.categoria_nombre}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-900 dark:text-white">{formatCurrency(p.precio_venta)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-medium ${p.stock <= p.stock_minimo ? 'text-red-600' : 'text-slate-900 dark:text-white'}`}>
                      {p.stock}
                    </span>
                    <span className="text-xs text-slate-400"> / {p.stock_minimo} min</span>
                  </td>
                  <td className="px-4 py-3 text-center text-xs text-slate-500 dark:text-slate-400">
                    {IVA_OPTIONS.find((i) => i.code === p.iva_code)?.label || p.iva_code}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => handleShowKardex(p)}
                        className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700"
                        title="Kárdex"
                      >
                        <ArrowUpDown className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleEdit(p)}
                        className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(p.id)}
                        className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      >
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
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              {editingId ? 'Editar Producto' : t('products.newProduct')}
            </h2>
            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('products.code')} *</label>
                  <input
                    required
                    value={form.codigo}
                    onChange={(e) => setForm({ ...form, codigo: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('products.name')} *</label>
                  <input
                    required
                    value={form.nombre}
                    onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('products.price')}</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.precio_venta}
                    onChange={(e) => setForm({ ...form, precio_venta: parseFloat(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Costo</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.costo}
                    onChange={(e) => setForm({ ...form, costo: parseFloat(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('products.stock')}</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.stock}
                    onChange={(e) => setForm({ ...form, stock: parseFloat(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('products.minStock')}</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.stock_minimo}
                    onChange={(e) => setForm({ ...form, stock_minimo: parseFloat(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('products.unit')}</label>
                  <select
                    value={form.unidad_medida}
                    onChange={(e) => setForm({ ...form, unidad_medida: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    <option value="UNIDAD">UNIDAD</option>
                    <option value="LITRO">LITRO</option>
                    <option value="KILO">KILO</option>
                    <option value="METRO">METRO</option>
                    <option value="CAJA">CAJA</option>
                    <option value="DOCENA">DOCENA</option>
                    <option value="GALON">GALÓN</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">IVA</label>
                  <select
                    value={form.iva_code}
                    onChange={(e) => setForm({ ...form, iva_code: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    {IVA_OPTIONS.map((i) => (
                      <option key={i.code} value={i.code}>{i.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">ICE</label>
                  <select
                    value={form.ice_code}
                    onChange={(e) => setForm({ ...form, ice_code: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  >
                    {ICE_OPTIONS.map((i) => (
                      <option key={i.code} value={i.code}>{i.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="activo"
                  type="checkbox"
                  checked={form.activo}
                  onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-emerald-600"
                />
                <label htmlFor="activo" className="text-sm text-slate-700 dark:text-slate-300">Producto activo</label>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-300"
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

      {/* Kardex Modal */}
      {kardexProduct && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-slate-800">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Kárdex: {kardexProduct.nombre}
              </h3>
              <button onClick={() => setKardexProduct(null)} className="rounded-md p-1 hover:bg-slate-100 dark:hover:bg-slate-700">
                <X className="h-5 w-5 text-slate-500" />
              </button>
            </div>
            {kardexLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
              </div>
            ) : kardexData.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">Sin movimientos registrados</p>
            ) : (
              <table className="mt-4 w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-700/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Fecha</th>
                    <th className="px-3 py-2 text-left font-medium">Tipo</th>
                    <th className="px-3 py-2 text-right font-medium">Cantidad</th>
                    <th className="px-3 py-2 text-right font-medium">Stock</th>
                    <th className="px-3 py-2 text-left font-medium">Documento</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {kardexData.map((k) => (
                    <tr key={k.id}>
                      <td className="px-3 py-2 text-slate-500">{new Date(k.fecha).toLocaleDateString('es-EC')}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          k.tipo === 'ENTRADA' ? 'bg-emerald-100 text-emerald-700' :
                          k.tipo === 'SALIDA' ? 'bg-red-100 text-red-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {k.tipo}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">{k.cantidad}</td>
                      <td className="px-3 py-2 text-right font-medium">{k.stock_resultante}</td>
                      <td className="px-3 py-2 text-slate-500">{k.documento_ref}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Delete confirm */}
      {deleteConfirm !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-800">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">¿Eliminar producto?</h3>
            <p className="mt-2 text-sm text-slate-500">Esta acción no se puede deshacer.</p>
            <div className="mt-4 flex justify-end gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-300">
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
