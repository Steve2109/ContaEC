# ContaEC

Sistema contable web para Ecuador con FastAPI, React/Vite y PostgreSQL.

- Programa: ContaEC
- Desarrollado por: T&M Technology Ec
- Soporte: info@tymtechnology.shop
- Teléfono: 0960068866
- Dominio: conta.tymtechnology.shop
- Servidor objetivo: LXC Proxmox `10.0.1.20:80`

## Estado Actual

Esta base deja el proyecto preparado para trabajar por fases sin Docker.

- Fase 1: FastAPI, PostgreSQL, configuración de servidor y puerto 80.
- Fase 2: JWT, multiempresa, admin inicial, licencias, rate limit, ClamAV/VirusTotal opcional y configuración sensible cifrada por usuario.
- Fase 3: facturación electrónica SRI con clave de acceso de 49 dígitos, XML para facturas, notas de crédito/débito, retenciones y guías de remisión, firma XML con certificado P12/PKCS#12, SOAP de recepción/autorización, proformas, clientes, productos y catálogos tributarios principales.
- Fase 4-16: modelos/rutas base para inventario, nómina, compras, almacenes, POS, BI, presupuestos, CRM, proyectos, integraciones e IA. Estos módulos existen como cimientos funcionales, pero deben endurecerse fase por fase antes de producción crítica.

El archivo `FICHA_TECNICA.pdf` debe ser la referencia normativa para cerrar la fase 3 completa: XML por tipo de comprobante, firma XAdES, webservices SRI, catálogos oficiales vigentes, estados y validaciones.

## Seguridad Implementada

- Las claves reales van en `.env`; no deben subirse al repositorio.
- Datos sensibles de usuario se guardan cifrados con `MASTER_ENCRYPTION_KEY`.
- No se cargan múltiples `.env` por usuario. La configuración por usuario vive en base de datos cifrada.
- Rate limit global por IP configurable con `RATE_LIMIT_PER_MINUTE`.
- CORS limitado por `CORS_ORIGINS`.
- ClamAV escanea archivos subidos antes de guardarlos definitivamente.
- VirusTotal se usa solo si el usuario marca esa opción y existe `VIRUSTOTAL_API_KEY`.
- Backups automáticos cifrados a medianoche mediante `pg_dump` cuando `postgresql-client` está instalado.
- Archivos temporales se limpian con `TEMP_FILE_TTL_MINUTES`.

## Variables `.env`

Copia `backend/.env.example` a `backend/.env` y cambia todos los secretos:

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Variables críticas:

```env
DATABASE_URL=postgresql://conta_user:CLAVE_SEGURA@localhost:5432/contaec_db
JWT_SECRET_KEY=clave_larga_unica
MASTER_ENCRYPTION_KEY=otra_clave_larga_unica
CORS_ORIGINS=https://conta.tymtechnology.shop,http://10.0.1.20
CLAMAV_ENABLED=True
CLAMAV_SOCKET=/var/run/clamav/clamd.ctl
VIRUSTOTAL_API_KEY=
ADMIN_EMAIL=steve.mejia@tymtechnology.shop
ADMIN_PASSWORD=Vitaestcum21..
```

Después del primer inicio, cambia la contraseña del administrador.

## Instalación En La LXC

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib postgresql-client clamav clamav-daemon nodejs npm
```

Crear base de datos:

```bash
sudo -u postgres psql
CREATE DATABASE contaec_db;
CREATE USER conta_user WITH PASSWORD 'CLAVE_SEGURA';
GRANT ALL PRIVILEGES ON DATABASE contaec_db TO conta_user;
\q
```

Backend:

```bash
cd /opt/contaec/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

ClamAV:

```bash
sudo freshclam
sudo systemctl enable --now clamav-daemon
sudo systemctl status clamav-daemon
```

Frontend:

```bash
cd /opt/contaec/frontend
npm install
npm run build
```

## Ejecución En Puerto 80

Como ya existe proxy reverso, DNS y Let's Encrypt en NPM, el backend puede escuchar en `0.0.0.0:80`.

Servicio systemd recomendado:

```ini
[Unit]
Description=ContaEC FastAPI
After=network.target postgresql.service clamav-daemon.service

[Service]
User=root
WorkingDirectory=/opt/contaec/backend
Environment="PATH=/opt/contaec/backend/venv/bin"
ExecStart=/opt/contaec/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo nano /etc/systemd/system/contaec.service
sudo systemctl daemon-reload
sudo systemctl enable --now contaec
sudo systemctl status contaec
```

## Comandos De Verificación

```bash
cd /opt/contaec/backend
source venv/bin/activate
python -m compileall app
uvicorn app.main:app --host 0.0.0.0 --port 80
```

```bash
cd /opt/contaec/frontend
npm run build
```

## Endpoints Principales

- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/companies`
- `POST /api/v1/companies`
- `GET /api/v1/license`
- `GET /api/v1/admin/dashboard/summary`
- `GET /api/v1/admin/dashboard/health`
- `POST /api/v1/files/upload`
- `GET /facturacion/tipos-iva/`
- `POST /facturacion/facturas/`
- `POST /facturacion/comprobantes/`
- `POST /facturacion/comprobantes/{id}/generar-xml`
- `POST /facturacion/comprobantes/{id}/firmar`
- `POST /facturacion/comprobantes/{id}/enviar-sri`
- `POST /facturacion/comprobantes/{id}/consultar-autorizacion`
- `POST /facturacion/guias-remision/`
- `POST /facturacion/guias-remision/{id}/firmar`
- `GET /inventario/productos/`
- `GET /api/nomina/empleados`

## Flujo De Archivos

1. El usuario sube Excel, CSV, ZIP, PDF, XML o TXT.
2. El backend guarda temporalmente en `TEMP_UPLOAD_FOLDER`.
3. ClamAV escanea el archivo.
4. Si hay malware, se elimina y se registra el evento.
5. Si está limpio, se mueve a `PERMANENT_UPLOAD_FOLDER`.
6. Si el usuario activa VirusTotal, se consulta el hash como segunda opinión.
7. Los temporales se eliminan automáticamente según `TEMP_FILE_TTL_MINUTES`.

## Licencias

El administrador puede gestionar licencias mensual, trimestral, semestral y anual desde `/api/v1/admin`. Los usuarios nuevos reciben una licencia inicial mensual de prueba para que el sistema pueda funcionar al registrarse; luego el administrador puede extender o modificar el período.

Para renovación por WhatsApp, el frontend debe abrir:

```text
https://wa.me/593960068866?text=Quiero%20renovar%20mi%20licencia%20por%20X%20meses
```

## Catálogos Tributarios Base

`backend/app/core/sri_constants.py` contiene los catálogos base solicitados:

- IVA: 0%, 5%, 8%, 12%, 13%, 14%, 15% por defecto, no objeto, exento e IVA diferenciado.
- Retenciones: 0%, 10%, 20%, 30%, 50%, 70% y 100%.
- ICE: estructura base para tarifas porcentuales/específicas.
- Estados de comprobantes.
- Tipos de contribuyente, regímenes y consumidor final.

Antes de usar en producción tributaria, validar estos códigos contra la versión exacta vigente de la ficha técnica SRI y anexos de catálogos.
