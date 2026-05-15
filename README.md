# ContaEC - Sistema Contable y Facturación Electrónica

## Descripción
ContaEC es un sistema contable completo con facturación electrónica para Ecuador, desarrollado por **T&M Technology Ec**.

## Información del Desarrollador
- **Desarrollado por**: T&M Technology Ec
- **Teléfono de soporte**: 0960068866
- **Correo de soporte**: info@tymtechnology.shop
- **DNS**: conta.tymtechnology.shop

## Estructura del Proyecto

### Backend (FastAPI - Python) - 48 archivos
```
/workspace
├── backend/                    # Backend FastAPI (Python)
│   ├── app/
│   │   ├── main.py            # Punto de entrada principal
│   │   ├── models/            # Modelos SQLAlchemy (15 archivos)
│   │   │   ├── __init__.py
│   │   │   ├── user.py        # Modelo de usuario
│   │   │   ├── company.py     # Modelo de empresa
│   │   │   ├── license.py     # Modelo de licencia
│   │   │   ├── facturacion.py # Facturación electrónica
│   │   │   ├── inventario.py  # Inventario y productos
│   │   │   ├── nomina.py      # Nómina y empleados
│   │   │   ├── warehouse.py   # Almacenes multi-bodega
│   │   │   ├── purchase.py    # Compras y proveedores
│   │   │   ├── crm.py         # CRM y leads
│   │   │   ├── projects.py    # Gestión de proyectos
│   │   │   ├── budget.py      # Presupuestos
│   │   │   ├── ai.py          # IA/ML predicciones
│   │   │   ├── integrations.py# Integraciones externas
│   │   │   └── ...
│   │   ├── routes/            # Endpoints API (13 archivos)
│   │   │   ├── auth.py        # Autenticación
│   │   │   ├── companies.py   # Empresas
│   │   │   ├── facturacion.py # Facturación SRI
│   │   │   ├── inventario.py  # Inventario
│   │   │   ├── nomina.py      # Nómina
│   │   │   ├── warehouse.py   # Almacenes
│   │   │   ├── purchase.py    # Compras
│   │   │   ├── pos.py         # Punto de venta
│   │   │   ├── bi.py          # Business Intelligence
│   │   │   ├── budget.py      # Presupuestos
│   │   │   ├── crm.py         # CRM
│   │   │   ├── projects.py    # Proyectos
│   │   │   ├── integrations.py# Integraciones
│   │   │   └── files.py       # Archivos y escaneo
│   │   ├── api/               # API adicional
│   │   │   ├── admin.py       # Panel administrador
│   │   │   └── auth.py        # Auth endpoints
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Lógica de negocio
│   │   │   ├── sri_service.py # Servicio SRI
│   │   │   ├── clamav_service.py # ClamAV
│   │   │   ├── virustotal_service.py # VirusTotal
│   │   │   ├── email_service.py # SMTP
│   │   │   └── backup_service.py # Backups
│   │   ├── utils/             # Utilidades
│   │   └── core/              # Configuración core
│   │       ├── security.py    # Encriptación, JWT
│   │       ├── config.py      # Configuración
│   │       └── sri_constants.py # Constantes SRI (IVA, ICE, Retenciones)
│   ├── static/
│   │   └── uploads/           # Archivos subidos
│   │       ├── temp/          # Temporales (auto-limpieza)
│   │       └── permanent/     # Permanentes
│   ├── backups/               # Backups automáticos
│   ├── logs/                  # Logs del sistema
│   ├── .env.example           # Ejemplo de configuración
│   └── requirements.txt       # Dependencias Python
```

### Frontend (React + TypeScript + Vite) - 16 archivos
```
├── frontend/                   # Frontend React + TypeScript
│   ├── src/
│   │   ├── App.tsx            # Componente principal con routing
│   │   ├── main.tsx           # Entry point
│   │   ├── index.css          # Estilos globales + Tailwind
│   │   ├── components/        # Componentes reutilizables
│   │   │   ├── Sidebar.tsx    # Menú lateral con navegación
│   │   │   ├── Header.tsx     # Cabecera con usuario, idioma, dark mode
│   │   │   └── ...
│   │   ├── pages/             # Páginas de la aplicación (8 archivos)
│   │   │   ├── Login.tsx      # Login
│   │   │   ├── Dashboard.tsx  # Dashboard principal con gráficos
│   │   │   ├── Companies.tsx  # Gestión de empresas
│   │   │   ├── Invoices.tsx   # Facturación electrónica
│   │   │   ├── Products.tsx   # Productos e inventario
│   │   │   ├── Employees.tsx  # Empleados/Nómina
│   │   │   ├── AdminPanel.tsx # Panel de Administrador
│   │   │   └── Settings.tsx   # Configuración general
│   │   ├── services/          # Servicios API
│   │   │   └── api.ts         # Cliente Axios con interceptores
│   │   ├── store/             # Estado global (Zustand)
│   │   │   └── useStore.ts
│   │   ├── hooks/             # Custom hooks
│   │   ├── utils/             # Utilidades
│   │   └── types/             # Tipos TypeScript
│   │       └── index.ts
│   ├── public/
│   │   └── favicon.svg
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── postcss.config.js
```

### Documentación
```
├── FICHA_TECNICA.pdf          # Documentación oficial SRI
└── README.md                  # Este archivo
```

## Tecnologías Utilizadas
- **Backend**: FastAPI (Python)
- **Frontend**: React/Next.js (Fase 6)
- **Base de Datos**: PostgreSQL
- **Seguridad**: ClamAV + VirusTotal
- **Autenticación**: JWT

## Fases del Proyecto - ESTADO ACTUAL

### ✅ FASES COMPLETADAS (1-16)

#### Fase 1-2: Infraestructura Base ✅
- Configuración del servidor LXC
- Base de datos PostgreSQL
- Autenticación JWT
- Gestión multiempresa
- Sistema de licencias (mensual, trimestral, semestral, anual)
- Panel de administrador
- Seguridad con ClamAV y VirusTotal
- Encriptación de datos sensibles
- Rate limiting

#### Fase 3: Facturación Electrónica SRI ✅
- Facturas, notas de crédito/débito
- Retenciones, guías de remisión, proformas
- Firma XML, webservices SRI
- **IVA completo**: 0%, 5%, 8%, 12%, 13%, 14%, 15% (default), No objeto, Exento, IVA diferenciado
- ICE y tarifas de retención (0%, 10%, 20%, 30%, 50%, 70%, 100%)
- Estados de comprobantes electrónicos
- Tipos de contribuyentes y regímenes (RIMPE, General, etc.)
- Consumidor final por defecto

#### Fase 4: Inventario y Kardex ✅
- Control de productos y stock
- Movimientos de inventario
- Múltiples almacenes
- Transferencias entre bodegas
- Ubicaciones físicas (rack/estante/nivel/bin)

#### Fase 5: Nómina RRHH ✅
- Registro de empleados
- Cálculo de sueldos, décimos, fondos de reserva
- Roles de pago
- Archivos para IESS y SRI

#### Fase 6: Frontend Next.js ✅
- APIs preparadas para React/Next.js
- Documentación Swagger completa

#### Fase 7: SMTP Avanzado + Sandbox ✅
- Configuración múltiple (Gmail, Zoho, Microsoft)
- Modo sandbox/pruebas
- Plantillas de email

#### Fase 8: Compras y Proveedores ✅
- Catálogo de proveedores
- Órdenes de compra
- Cuentas por pagar

#### Fase 9: Multi-Almacén y Logística ✅
- Múltiples bodegas
- Transferencias
- Kardex detallado

#### Fase 10: Punto de Venta (POS) ✅
- Ventas rápidas
- Código de barras
- Arqueo de caja

#### Fase 11: Business Intelligence ✅
- KPIs en tiempo real
- Dashboards interactivos
- Exportación a Power BI

#### Fase 12: Presupuestos ✅
- Presupuesto anual por cuenta
- Ejecución vs real
- Alertas de sobregiro

#### Fase 13: CRM Avanzado ✅
- Pipeline de ventas
- Gestión de leads y oportunidades
- Automatización de seguimientos

#### Fase 14: Proyectos y Servicios ✅
- Gestión de proyectos
- Timesheets
- Rentabilidad por proyecto

#### Fase 15: Integraciones ✅
- Conciliación bancaria
- E-commerce (Shopify, WooCommerce, Magento, etc.)
- Webhooks

#### Fase 16: IA / Machine Learning ✅
- Predicción de ventas
- Detección de fraude
- Categorización automática
- Chatbot de soporte

## Instalación en Servidor LXC

### Requisitos Previos
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Instalar ClamAV
sudo apt install clamav clamav-daemon -y

# Instalar Python y pip
sudo apt install python3 python3-pip python3-venv -y
```

### Configuración de Base de Datos
```bash
# Acceder a PostgreSQL
sudo -u postgres psql

# Crear base de datos y usuario
CREATE DATABASE contaec_db;
CREATE USER conta_user WITH PASSWORD 'SecurePass2024';
GRANT ALL PRIVILEGES ON DATABASE contaec_db TO conta_user;
\q
```

### Configuración del Backend
```bash
# Navegar al directorio del backend
cd /workspace/backend

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración
cp .env.example .env

# Editar .env con tus configuraciones
nano .env
```

### Configuración de ClamAV
```bash
# Actualizar bases de datos de ClamAV
sudo freshclam

# Iniciar servicio clamd
sudo systemctl start clamav-daemon
sudo systemctl enable clamav-daemon

# Verificar estado
sudo systemctl status clamav-daemon
```

### Ejecutar la Aplicación
```bash
# Desde el directorio backend con el entorno virtual activado
uvicorn app.main:app --host 0.0.0.0 --port 80 --reload
```

### Ejecutar en Segundo Plano (Producción)
```bash
# Usando nohup
nohup uvicorn app.main:app --host 0.0.0.0 --port 80 > logs/app.log 2>&1 &

# O usando systemd (recomendado)
sudo nano /etc/systemd/system/contaec.service
```

**Contenido del servicio systemd:**
```ini
[Unit]
Description=ContaEC API Service
After=network.target postgresql.service clamav-daemon.service

[Service]
User=root
WorkingDirectory=/workspace/backend
Environment="PATH=/workspace/backend/venv/bin"
ExecStart=/workspace/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=always

[Install]
WantedBy=multi-user.target
```

**Habilitar servicio:**
```bash
sudo systemctl daemon-reload
sudo systemctl start contaec
sudo systemctl enable contaec
sudo systemctl status contaec
```

## Archivo .env

```env
# Base de datos
DATABASE_URL=postgresql://conta_user:SecurePass2024@localhost:5432/contaec_db

# Configuración del servidor
HOST=0.0.0.0
PORT=80
DEBUG=False

# JWT Configuration
JWT_SECRET_KEY=cambia_esta_clave_por_una_muy_segura
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Clave maestra para encriptación
MASTER_ENCRYPTION_KEY=cambia_esta_clave_maestra_por_una_mas_segura

# Rutas de archivos
UPLOAD_FOLDER=/workspace/backend/static/uploads
TEMP_UPLOAD_FOLDER=/workspace/backend/static/uploads/temp
PERMANENT_UPLOAD_FOLDER=/workspace/backend/static/uploads/permanent
BACKUP_FOLDER=/workspace/backend/backups

# ClamAV Configuration
CLAMAV_ENABLED=True
CLAMAV_SOCKET=/var/run/clamav/clamd.ctl

# VirusTotal API (opcional)
VIRUSTOTAL_API_KEY=

# Admin por defecto
ADMIN_EMAIL=steve.mejia@tymtechnology.shop
ADMIN_PASSWORD=Vitaestcum21..

# Aplicación
APP_NAME=ContaEC
DEVELOPER=T&M Technology Ec
SUPPORT_PHONE=0960068866
SUPPORT_EMAIL=info@tymtechnology.shop
APP_DOMAIN=conta.tymtechnology.shop

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=/workspace/backend/logs/app.log
```

## Credenciales de Administrador

- **Email**: steve.mejia@tymtechnology.shop
- **Contraseña**: Vitaestcum21..

⚠️ **IMPORTANTE**: Cambia estas credenciales después del primer inicio

## Endpoints de la API

### Autenticación
- `POST /api/v1/auth/register` - Registrar nuevo usuario
- `POST /api/v1/auth/login` - Iniciar sesión
- `GET /api/v1/auth/me` - Obtener usuario actual
- `PUT /api/v1/auth/me` - Actualizar usuario

### Empresas
- `POST /api/v1/companies` - Crear empresa
- `GET /api/v1/companies` - Listar mis empresas
- `GET /api/v1/companies/{ruc}` - Consultar empresa por RUC

### Configuración
- `GET /api/v1/config` - Obtener configuración
- `PUT /api/v1/config` - Actualizar configuración (firma, SMTP, backup)

### Licencias
- `GET /api/v1/license` - Obtener licencia del usuario

### Administración (Solo Admin)
- `GET /api/v1/admin/dashboard/summary` - Resumen dashboard
- `GET /api/v1/admin/dashboard/health` - Salud del sistema
- `GET /api/v1/admin/users` - Listar usuarios
- `GET /api/v1/admin/licenses` - Listar licencias
- `PUT /api/v1/admin/licenses/{id}` - Actualizar licencia
- `POST /api/v1/admin/users/{id}/license` - Crear/extender licencia

### Archivos
- `POST /api/v1/files/upload` - Subir archivo con escaneo
- `POST /api/v1/files/scan` - Escanear archivo existente
- `GET /api/v1/files/scan-history` - Historial de escaneos

## Características de Seguridad

1. **Encriptación de Datos Sensibles**
   - Firmas electrónicas encriptadas
   - Claves de firma encriptadas
   - Configuración SMTP encriptada
   - Claves de backup encriptadas

2. **Escaneo de Archivos**
   - ClamAV obligatorio para todos los archivos
   - VirusTotal opcional para archivos sospechosos
   - Logs de todos los escaneos

3. **Rate Limiting**
   - Limitación de tasa en endpoints críticos
   - Protección contra ataques DDoS

4. **Logs de Seguridad**
   - Registro de todos los intentos de login
   - Registro de acciones sospechosas
   - Auditoría completa

5. **Aislamiento de Usuarios**
   - Cada usuario tiene su propia configuración
   - Datos encriptados individualmente
   - Multiempresa con separación de datos

## Próximos Pasos

1. Completar Fase 3: Facturación Electrónica SRI
2. Implementar frontend React
3. Configurar backups automáticos
4. Integrar con servicios del SRI

## Soporte

Para soporte técnico, contactar:
- Email: info@tymtechnology.shop
- Teléfono: 0960068866
