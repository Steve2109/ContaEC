import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Settings as SettingsIcon,
  Upload,
  CheckCircle,
  AlertCircle,
  Loader2,
  MessageCircle,
  Lock,
  Mail,
  Sun,
  Moon,
  FlaskConical,
  Save,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import {
  apiGetCompanyConfig,
  apiUpdateCompanyConfig,
  apiUploadSignature,
  apiTestSMTP,
  apiUpdateBackupKey,
} from '../services/api';

export default function Settings() {
  const { t, i18n } = useTranslation();
  const { darkMode, toggleDarkMode, user, currentCompany } = useStore();

  const [activeTab, setActiveTab] = useState<'general' | 'firma' | 'smtp' | 'sandbox'>('general');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Firma
  const [signatureFile, setSignatureFile] = useState<File | null>(null);
  const [signaturePass, setSignaturePass] = useState('');
  const [signatureValidUntil, setSignatureValidUntil] = useState<string | null>(null);

  // SMTP
  const [smtp, setSmtp] = useState({
    host: '',
    port: 587,
    user: '',
    password: '',
    tls: true,
  });
  const [testingSMTP, setTestingSMTP] = useState(false);

  // Backup key
  const [backupKey, setBackupKey] = useState('');
  const [backupKeySet, setBackupKeySet] = useState(false);

  // Sandbox
  const [sandboxMode, setSandboxMode] = useState(false);

  useEffect(() => {
    const load = async () => {
      if (!currentCompany) return;
      try {
        const res = await apiGetCompanyConfig(currentCompany.id);
        const data = res.data;
        setSignatureValidUntil(data.firma_valida_hasta || null);
        setSandboxMode(data.sandbox_mode || false);
        if (data.smtp_config) {
          setSmtp(data.smtp_config);
        }
        setBackupKeySet(data.backup_key_set || false);
      } catch (err) {
        console.error('Error cargando config:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [currentCompany]);

  const handleSave = async () => {
    if (!currentCompany) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiUpdateCompanyConfig(currentCompany.id, {
        sandbox_mode: sandboxMode,
      });
      setMessage({ type: 'success', text: t('settings.configSaved') });
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.response?.data?.detail || 'Error guardando' });
    } finally {
      setSaving(false);
    }
  };

  const handleUploadSignature = async () => {
    if (!signatureFile || !signaturePass || !currentCompany) {
      setMessage({ type: 'error', text: 'Selecciona el archivo .p12 y la clave' });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      const data = new FormData();
      data.append('file', signatureFile);
      data.append('password', signaturePass);
      await apiUploadSignature(currentCompany.id, data);
      setSignatureFile(null);
      setSignaturePass('');
      const res = await apiGetCompanyConfig(currentCompany.id);
      setSignatureValidUntil(res.data.firma_valida_hasta || null);
      setMessage({ type: 'success', text: 'Firma electrónica cargada exitosamente' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.response?.data?.detail || 'Error subiendo firma' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestSMTP = async () => {
    setTestingSMTP(true);
    setMessage(null);
    try {
      await apiTestSMTP(smtp);
      setMessage({ type: 'success', text: 'Correo de prueba enviado exitosamente' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.response?.data?.detail || 'Error enviando correo de prueba' });
    } finally {
      setTestingSMTP(false);
    }
  };

  const handleSaveBackupKey = async () => {
    if (!backupKey || backupKey.length < 8) {
      setMessage({ type: 'error', text: 'La clave debe tener al menos 8 caracteres' });
      return;
    }
    setSaving(true);
    try {
      await apiUpdateBackupKey({ backup_key: backupKey });
      setBackupKeySet(true);
      setBackupKey('');
      setMessage({ type: 'success', text: 'Clave de backup configurada' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.response?.data?.detail || 'Error' });
    } finally {
      setSaving(false);
    }
  };

  const openWhatsAppRenewal = () => {
    const phone = '593960068866'; // Número de contacto T&M Technology Ec
    const email = user?.email || '';
    const msg = encodeURIComponent(
      `Hola, soy usuario de ContaEC. Quiero renovar mi licencia por 1 año. Mi correo registrado es ${email}.`
    );
    window.open(`https://wa.me/${phone}?text=${msg}`, '_blank');
  };

  if (!currentCompany) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-800">
        <SettingsIcon className="mx-auto h-12 w-12 text-slate-300" />
        <p className="mt-4 text-slate-500">Selecciona una empresa activa para configurar</p>
      </div>
    );
  }

  const tabs = [
    { id: 'general', label: 'General', icon: SettingsIcon },
    { id: 'firma', label: t('settings.electronicSignature'), icon: Lock },
    { id: 'smtp', label: t('settings.emailSettings'), icon: Mail },
    { id: 'sandbox', label: 'Sandbox', icon: FlaskConical },
  ] as const;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{t('settings.title')}</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {t('settings.saveConfig')}
        </button>
      </div>

      {message && (
        <div className={`rounded-lg p-3 text-sm flex items-center gap-2 ${
          message.type === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
        }`}>
          {message.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {message.text}
        </div>
      )}

      {/* Tabs */}
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

      {/* General Tab */}
      {activeTab === 'general' && (
        <div className="space-y-6">
          {/* Language */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{t('settings.language')}</h3>
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => i18n.changeLanguage('es-EC')}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                  i18n.language === 'es-EC'
                    ? 'bg-emerald-600 text-white'
                    : 'border border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300'
                }`}
              >
                🇪🇨 Español (Ecuador)
              </button>
              <button
                onClick={() => i18n.changeLanguage('en')}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                  i18n.language === 'en'
                    ? 'bg-emerald-600 text-white'
                    : 'border border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300'
                }`}
              >
                🇺🇸 English
              </button>
            </div>
          </div>

          {/* Theme */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{t('settings.theme')}</h3>
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => { if (darkMode) toggleDarkMode(); }}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
                  !darkMode
                    ? 'bg-emerald-600 text-white'
                    : 'border border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300'
                }`}
              >
                <Sun className="h-4 w-4" />
                {t('settings.lightMode')}
              </button>
              <button
                onClick={() => { if (!darkMode) toggleDarkMode(); }}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
                  darkMode
                    ? 'bg-emerald-600 text-white'
                    : 'border border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300'
                }`}
              >
                <Moon className="h-4 w-4" />
                {t('settings.darkMode')}
              </button>
            </div>
          </div>

          {/* Backup Key */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{t('settings.backupKey')}</h3>
            {backupKeySet ? (
              <div className="mt-3 flex items-center gap-2 text-sm text-emerald-600">
                <CheckCircle className="h-4 w-4" />
                {t('settings.backupKeySet')}
              </div>
            ) : (
              <div className="mt-3 space-y-3">
                <p className="text-sm text-slate-500">{t('settings.backupKeyRequired')}</p>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={backupKey}
                    onChange={(e) => setBackupKey(e.target.value)}
                    placeholder="Mínimo 8 caracteres"
                    className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                  <button
                    onClick={handleSaveBackupKey}
                    disabled={saving}
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    Guardar
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* WhatsApp Renewal */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{t('whatsapp.renewTitle')}</h3>
            <button
              onClick={openWhatsAppRenewal}
              className="mt-3 flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            >
              <MessageCircle className="h-4 w-4" />
              Renovar licencia por WhatsApp
            </button>
          </div>
        </div>
      )}

      {/* Firma Tab */}
      {activeTab === 'firma' && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{t('settings.electronicSignature')}</h3>

          {signatureValidUntil && (
            <div className="mt-3 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
              <CheckCircle className="h-4 w-4" />
              Firma válida hasta: {new Date(signatureValidUntil).toLocaleDateString('es-EC')}
            </div>
          )}

          <div className="mt-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('settings.signatureFile')}</label>
              <label className="mt-1 flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300">
                <Upload className="h-4 w-4" />
                {signatureFile ? signatureFile.name : 'Seleccionar archivo .p12'}
                <input
                  type="file"
                  accept=".p12,.pfx"
                  className="hidden"
                  onChange={(e) => setSignatureFile(e.target.files?.[0] || null)}
                />
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('settings.signaturePassword')}</label>
              <input
                type="password"
                value={signaturePass}
                onChange={(e) => setSignaturePass(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
            </div>
            <button
              onClick={handleUploadSignature}
              disabled={!signatureFile || !signaturePass || saving}
              className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Cargar firma electrónica
            </button>
          </div>
        </div>
      )}

      {/* SMTP Tab */}
      {activeTab === 'smtp' && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{t('settings.emailSettings')}</h3>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('settings.smtpHost')}</label>
              <input
                value={smtp.host}
                onChange={(e) => setSmtp({ ...smtp, host: e.target.value })}
                placeholder="smtp.gmail.com"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('settings.smtpPort')}</label>
              <input
                type="number"
                value={smtp.port}
                onChange={(e) => setSmtp({ ...smtp, port: parseInt(e.target.value) || 587 })}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('settings.smtpUser')}</label>
              <input
                value={smtp.user}
                onChange={(e) => setSmtp({ ...smtp, user: e.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">{t('settings.smtpPassword')}</label>
              <input
                type="password"
                value={smtp.password}
                onChange={(e) => setSmtp({ ...smtp, password: e.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <input
              id="tls"
              type="checkbox"
              checked={smtp.tls}
              onChange={(e) => setSmtp({ ...smtp, tls: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300 text-emerald-600"
            />
            <label htmlFor="tls" className="text-sm text-slate-700 dark:text-slate-300">{t('settings.smtpTls')}</label>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleTestSMTP}
              disabled={testingSMTP || !smtp.host || !smtp.user}
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300"
            >
              {testingSMTP && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('settings.testEmail')}
            </button>
          </div>
        </div>
      )}

      {/* Sandbox Tab */}
      {activeTab === 'sandbox' && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{t('settings.sandboxToggle')}</h3>
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={() => setSandboxMode(!sandboxMode)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                sandboxMode ? 'bg-amber-500' : 'bg-slate-300 dark:bg-slate-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                  sandboxMode ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <span className="text-sm text-slate-700 dark:text-slate-300">
              {sandboxMode ? t('settings.sandboxOn') : t('settings.sandboxOff')}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            En modo Sandbox, todos los comprobantes electrónicos se envían al ambiente de pruebas del SRI (celcer.sri.gob.ec). 
            No tienen validez tributaria real.
          </p>
        </div>
      )}
    </div>
  );
}
