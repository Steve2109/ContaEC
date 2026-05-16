import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FileText,
  Plus,
  Search,
  Download,
  Send,
  Trash2,
  Pencil,
  Loader2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  ArrowLeft,
  UserPlus,
} from 'lucide-react';
import {
  apiGetInvoices,
  apiCreateInvoice,
  apiGetClients,
  apiGetProducts,
  apiSendInvoiceToSRI,
  apiGetInvoiceXML,
  apiGetInvoicePDF,
} from '../services/api';
import { useStore } from '../store/useStore';

interface InvoiceItem {
  product_id: number | null;
  description: string;
  quantity: number;
  unit_price: number;
  discount: number;
  iva_code: string;
  ice_code: string | null;
  total_line: number;
}

interface Invoice {
  id: number;
  numero_comprobante: string;
  fecha_emision: string;
  cliente_ruc: string;
  cliente_razon_social: string;
  total_sin_impuestos: number;
  total_descuento: number;
  total_iva: number;
  total_ice: number;
  total: number;
  estado: string;
  tipo_documento: string;
}

interface Client {
  id: number;
  ruc: string;
  razon_social: string;
}

interface Product {
  id: number;
  codigo: string;
  nombre: string;
  precio_venta: number;
  iva_code: string;
  ice_code: string | null;
  stock: number;
}

const IVA_OPTIONS = [
  { code: '0', label: '0%', value: 0 },
  { code: '2', label: '12%', value: 0.12 },
  { code: '3', label: '13%', value: 0.13 },
  { code: '4', label: '14%', value: 0.14 },
  { code: '5', label: '15%', value: 0.15 },
  { code: '6', label: 'No Objeto', value: 0 },
  { code: '7', label: 'Exento', value: 0 },
];

const DOCUMENT_TYPES = [
  { code: '01', label: 'Factura' },
  { code: '04', label: 'Nota de Crédito' },
  { code: '05', label: 'Nota de Débito' },
  { code: '07', label: 'Retención' },
];

export default function Invoices() {
  const { t } = useTranslation();
  const { currentCompany } = useStore();

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [docType, setDocType] = useState('01');
  const [clientId, setClientId] = useState<number | ''>('');
  const [newClientRuc, setNewClientRuc] = useState('');
  const [newClientName, setNewClientName] = useState('');
  const [showNewClient, setShowNewClient] = useState(false);
  const [items, setItems] = useState<InvoiceItem[]>([
    { product_id: null, description: '', quantity: 1, unit_price: 0, discount: 0, iva_code: '2', ice_code: null, total_line: 0 },
  ]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [invRes, cliRes, prodRes] = await Promise.all([
        apiGetInvoices(),
        apiGetClients(),
        apiGetProducts(),
      ]);
      setInvoices(invRes.data || []);
      setClients(cliRes.data || []);
      setProducts(prodRes.data || []);
    } catch (err: any) {
      console.error('Error cargando facturas:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const calculateLine = (line: InvoiceItem): InvoiceItem => {
    const base = line.quantity * line.unit_price - line.discount;
    const ivaRate = IVA_OPTIONS.find((i) => i.code === line.iva_code)?.value || 0;
    const ivaAmount = base * ivaRate;
    const total = base + ivaAmount;
    return { ...line, total_line: parseFloat(total.toFixed(2)) };
  };

  const updateItem = (index: number, field: keyof InvoiceItem, value: any) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    if (field === 'product_id' && value) {
      const prod = products.find((p) => p.id === value);
      if (prod) {
        newItems[index] = {
          ...newItems[index],
          description: prod.nombre,
          unit_price: prod.precio_venta,
          iva_code: prod.iva_code,
          ice_code: prod.ice_code,
        };
      }
    }
    newItems[index] = calculateLine(newItems[index]);
    setItems(newItems);
  };

  const addItem = () => {
    setItems([
      ...items,
      { product_id: null, description: '', quantity: 1, unit_price: 0, discount: 0, iva_code: '2', ice_code: null, total_line: 0 },
    ]);
  };

  const removeItem = (index: number) => {
    if (items.length <= 1) return;
    setItems(items.filter((_, i) => i !== index));
  };

  const totals = items.reduce(
    (acc, item) => {
      const base = item.quantity * item.unit_price - item.discount;
      const ivaRate = IVA_OPTIONS.find((i) => i.code === item.iva_code)?.value || 0;
      acc.subtotal += base;
      acc.iva += base * ivaRate;
      acc.discount += item.discount;
      return acc;
    },
    { subtotal: 0, iva: 0, discount: 0 }
  );
  const grandTotal = totals.subtotal + totals.iva;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentCompany) {
      alert('Selecciona una empresa activa primero');
      return;
    }
    if (!clientId && !showNewClient) {
      alert('Selecciona un cliente');
      return;
    }
    if (items.some((i) => !i.description || i.quantity <= 0)) {
      alert('Completa todos los ítems');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        tipo_documento: docType,
        empresa_id: currentCompany.id,
        cliente_id: clientId || null,
        nuevo_cliente: showNewClient
          ? { ruc: newClientRuc, razon_social: newClientName }
          : null,
        items: items.map((i) => ({
          product_id: i.product_id,
          descripcion: i.description,
          cantidad: i.quantity,
          precio_unitario: i.unit_price,
          descuento: i.discount,
          codigo_iva: i.iva_code,
          codigo_ice: i.ice_code,
        })),
      };
      await apiCreateInvoice(payload);
      setShowForm(false);
      setItems([
        { product_id: null, description: '', quantity: 1, unit_price: 0, discount: 0, iva_code: '2', ice_code: null, total_line: 0 },
      ]);
      setClientId('');
      await fetchData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error creando comprobante');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSendSRI = async (id: number) => {
    try {
      await apiSendInvoiceToSRI(id);
      await fetchData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Error enviando al SRI');
    }
  };

  const handleDownloadXML = async (id: number) => {
    try {
      const res = await apiGetInvoiceXML(id);
      const blob = new Blob([res.data], { type: 'application/xml' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `comprobante_${id}.xml`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Error descargando XML');
    }
  };

  const handleDownloadPDF = async (id: number) => {
    try {
      const res = await apiGetInvoicePDF(id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `comprobante_${id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Error descargando PDF');
    }
  };

  const getStateBadge = (estado: string) => {
    const map: Record<string, { bg: string; text: string; icon: any }> = {
      BORRADOR: { bg: 'bg-slate-100', text: 'text-slate-700', icon: Clock },
      FIRMADO: { bg: 'bg-blue-100', text: 'text-blue-700', icon: CheckCircle },
      ENVIADO: { bg: 'bg-amber-100', text: 'text-amber-700', icon: Send },
      AUTORIZADO: { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: CheckCircle },
      RECHAZADO: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
      ANULADO: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Trash2 },
      ERROR_XML: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertTriangle },
    };
    const style = map[estado] || map.BORRADOR;
    return (
      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}>
        <style.icon className="h-3 w-3" />
        {t(`invoices.states.${estado}`)}
      </span>
    );
  };

  const filtered = invoices.filter(
    (inv) =>
      inv.numero_comprobante?.toLowerCase().includes(search.toLowerCase()) ||
      inv.cliente_razon_social?.toLowerCase().includes(search.toLowerCase()) ||
      inv.cliente_ruc?.includes(search)
  );

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(v || 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{t('invoices.title')}</h1>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            <Plus className="h-4 w-4" />
            {t('invoices.newInvoice')}
          </button>
        )}
      </div>

      {!showForm && (
        <>
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
              <FileText className="mx-auto h-12 w-12 text-slate-300" />
              <p className="mt-4 text-slate-500 dark:text-slate-400">{t('common.noData')}</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-700/50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('invoices.invoiceNumber')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('invoices.date')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('invoices.client')}</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">{t('invoices.total')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">{t('invoices.state')}</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">{t('invoices.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {filtered.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                      <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{inv.numero_comprobante}</td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                        {new Date(inv.fecha_emision).toLocaleDateString('es-EC')}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{inv.cliente_razon_social}</td>
                      <td className="px-4 py-3 text-right font-medium text-slate-900 dark:text-white">{formatCurrency(inv.total)}</td>
                      <td className="px-4 py-3">{getStateBadge(inv.estado)}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1">
                          {inv.estado === 'FIRMADO' && (
                            <button
                              onClick={() => handleSendSRI(inv.id)}
                              className="rounded-md p-1.5 text-emerald-600 hover:bg-emerald-50"
                              title={t('invoices.sendToSRI')}
                            >
                              <Send className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleDownloadXML(inv.id)}
                            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
                            title={t('invoices.downloadXML')}
                          >
                            <Download className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDownloadPDF(inv.id)}
                            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
                            title={t('invoices.downloadPDF')}
                          >
                            <FileText className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Create Invoice Form */}
      {showForm && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-800">
          <div className="flex items-center gap-2 mb-4">
            <button onClick={() => setShowForm(false)} className="rounded-md p-1 hover:bg-slate-100 dark:hover:bg-slate-700">
              <ArrowLeft className="h-5 w-5 text-slate-500" />
            </button>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{t('invoices.newInvoice')}</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Header */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Tipo</label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  {DOCUMENT_TYPES.map((d) => (
                    <option key={d.code} value={d.code}>{d.label}</option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Cliente</label>
                <div className="mt-1 flex gap-2">
                  {!showNewClient ? (
                    <>
                      <select
                        value={clientId}
                        onChange={(e) => setClientId(Number(e.target.value) || '')}
                        className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                      >
                        <option value="">{t('invoices.consumidorFinal')}</option>
                        {clients.map((c) => (
                          <option key={c.id} value={c.id}>{c.razon_social} ({c.ruc})</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => setShowNewClient(true)}
                        className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300"
                        title="Nuevo cliente"
                      >
                        <UserPlus className="h-4 w-4" />
                      </button>
                    </>
                  ) : (
                    <div className="flex flex-1 gap-2">
                      <input
                        placeholder="RUC"
                        value={newClientRuc}
                        onChange={(e) => setNewClientRuc(e.target.value)}
                        className="w-32 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                      />
                      <input
                        placeholder="Razón social"
                        value={newClientName}
                        onChange={(e) => setNewClientName(e.target.value)}
                        className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                      />
                      <button
                        type="button"
                        onClick={() => { setShowNewClient(false); setNewClientRuc(''); setNewClientName(''); }}
                        className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 dark:border-slate-600"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Items */}
            <div>
              <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">{t('invoices.items')}</h3>
              <div className="space-y-3">
                {items.map((item, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2 items-end rounded-lg border border-slate-100 p-3 dark:border-slate-700">
                    <div className="col-span-3">
                      <label className="text-xs text-slate-500">Producto</label>
                      <select
                        value={item.product_id || ''}
                        onChange={(e) => updateItem(idx, 'product_id', Number(e.target.value) || null)}
                        className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                      >
                        <option value="">Manual</option>
                        {products.map((p) => (
                          <option key={p.id} value={p.id}>{p.nombre}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-span-3">
                      <label className="text-xs text-slate-500">Descripción</label>
                      <input
                        value={item.description}
                        onChange={(e) => updateItem(idx, 'description', e.target.value)}
                        className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                      />
                    </div>
                    <div className="col-span-1">
                      <label className="text-xs text-slate-500">Cant.</label>
                      <input
                        type="number"
                        min={0.01}
                        step={0.01}
                        value={item.quantity}
                        onChange={(e) => updateItem(idx, 'quantity', parseFloat(e.target.value) || 0)}
                        className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="text-xs text-slate-500">Precio</label>
                      <input
                        type="number"
                        min={0}
                        step={0.01}
                        value={item.unit_price}
                        onChange={(e) => updateItem(idx, 'unit_price', parseFloat(e.target.value) || 0)}
                        className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                      />
                    </div>
                    <div className="col-span-1">
                      <label className="text-xs text-slate-500">Desc.</label>
                      <input
                        type="number"
                        min={0}
                        step={0.01}
                        value={item.discount}
                        onChange={(e) => updateItem(idx, 'discount', parseFloat(e.target.value) || 0)}
                        className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                      />
                    </div>
                    <div className="col-span-1">
                      <label className="text-xs text-slate-500">IVA</label>
                      <select
                        value={item.iva_code}
                        onChange={(e) => updateItem(idx, 'iva_code', e.target.value)}
                        className="w-full rounded-md border border-slate-200 px-1 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                      >
                        {IVA_OPTIONS.map((i) => (
                          <option key={i.code} value={i.code}>{i.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-span-1 text-right">
                      <p className="text-sm font-medium text-slate-900 dark:text-white">
                        {formatCurrency(item.total_line)}
                      </p>
                    </div>
                    <div className="col-span-1 flex justify-end">
                      <button
                        type="button"
                        onClick={() => removeItem(idx)}
                        className="rounded-md p-1 text-red-500 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={addItem}
                className="mt-2 flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300"
              >
                <Plus className="h-4 w-4" /> {t('invoices.addItem')}
              </button>
            </div>

            {/* Totals */}
            <div className="flex justify-end">
              <div className="w-full max-w-xs space-y-1 text-sm">
                <div className="flex justify-between text-slate-500 dark:text-slate-400">
                  <span>Subtotal</span>
                  <span>{formatCurrency(totals.subtotal)}</span>
                </div>
                <div className="flex justify-between text-slate-500 dark:text-slate-400">
                  <span>Descuento</span>
                  <span>-{formatCurrency(totals.discount)}</span>
                </div>
                <div className="flex justify-between text-slate-500 dark:text-slate-400">
                  <span>IVA</span>
                  <span>{formatCurrency(totals.iva)}</span>
                </div>
                <div className="flex justify-between border-t border-slate-200 pt-2 text-lg font-semibold text-slate-900 dark:border-slate-600 dark:text-white">
                  <span>{t('invoices.totalInvoice')}</span>
                  <span>{formatCurrency(grandTotal)}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300"
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('common.create')}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
