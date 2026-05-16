#!/bin/bash
# =============================================================================
# install.sh — Script de instalación automatizado para ContaEC
# Stack: FastAPI + PostgreSQL + React + ClamAV (sin Docker)
# Servidor: LXC Proxmox | IP: 10.0.1.20 | Puerto: 80
# =============================================================================
set -euo pipefail

APP_NAME="ContaEC"
APP_USER="contaec"
APP_DIR="/opt/contaec"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"
DB_NAME="contaec_db"
DB_USER="contaec_user"
SERVICE_FILE="/etc/systemd/system/contaec.service"
NGINX_CONF="/etc/nginx/sites-available/contaec"

echo "=========================================="
echo "  Instalador de $APP_NAME"
echo "  T&M Technology Ec"
echo "=========================================="

# ── 1. Detectar OS ──
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ No se pudo detectar el sistema operativo."
    exit 1
fi

echo "🔧 Sistema detectado: $OS"

# ── 2. Actualizar sistema ──
echo "📦 Actualizando paquetes del sistema..."
if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    apt-get update && apt-get upgrade -y
elif [ "$OS" == "almalinux" ] || [ "$OS" == "rocky" ] || [ "$OS" == "rhel" ]; then
    dnf update -y
fi

# ── 3. Instalar dependencias del sistema ──
echo "📦 Instalando dependencias del sistema..."
if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    apt-get install -y \
        python3 python3-venv python3-pip python3-dev \
        postgresql postgresql-contrib \
        nginx git curl wget build-essential \
        clamav clamav-daemon \
        nodejs npm \
        libpq-dev \
        libxml2-dev libxslt1-dev \
        libxmlsec1-dev libxmlsec1-openssl \
        pkg-config

    # Asegurar que Node.js sea versión reciente (>=18)
    if ! command -v node &> /dev/null || [ "$(node -v | cut -d'v' -f2 | cut -d'.' -f1)" -lt 18 ]; then
        echo "📦 Instalando Node.js 20 LTS..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt-get install -y nodejs
    fi

elif [ "$OS" == "almalinux" ] || [ "$OS" == "rocky" ] || [ "$OS" == "rhel" ]; then
    dnf install -y \
        python3 python3-pip python3-devel \
        postgresql-server postgresql-contrib \
        nginx git curl wget gcc make \
        clamav clamav-update \
        nodejs npm \
        libpq-devel \
        libxml2-devel libxslt-devel \
        xmlsec1-devel xmlsec1-openssl-devel \
        pkgconfig
fi

# ── 4. Configurar ClamAV ──
echo "🛡️  Configurando ClamAV..."
if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    systemctl stop clamav-freshclam || true
    freshclam || true
    systemctl enable clamav-daemon
    systemctl start clamav-daemon
    # Esperar a que clamd cree el socket
    for i in {1..30}; do
        if [ -S /var/run/clamav/clamd.ctl ]; then
            break
        fi
        echo "⏳ Esperando socket de clamd... ($i/30)"
        sleep 2
    done
    if [ ! -S /var/run/clamav/clamd.ctl ]; then
        echo "⚠️  Socket de clamd no encontrado. Se usará clamscan como fallback."
    fi
fi

# ── 5. Configurar PostgreSQL ──
echo "🐘 Configurando PostgreSQL..."
if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    systemctl enable postgresql
    systemctl start postgresql
elif [ "$OS" == "almalinux" ] || [ "$OS" == "rocky" ] || [ "$OS" == "rhel" ]; then
    postgresql-setup --initdb || true
    systemctl enable postgresql
    systemctl start postgresql
fi

# Generar contraseñas aleatorias seguras
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)
BACKUP_KEY=$(openssl rand -base64 32)
ADMIN_PASS="Vitaestcum21.."  # El usuario debe cambiar esto post-instalación

sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || true
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || true

# ── 6. Crear usuario de aplicación ──
echo "👤 Creando usuario de aplicación: $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$APP_DIR" "$APP_USER"
fi

# ── 7. Clonar repositorio ──
echo "📥 Clonando repositorio ContaEC..."
if [ -d "$APP_DIR" ]; then
    echo "⚠️  Directorio $APP_DIR ya existe. Actualizando..."
    cd "$APP_DIR"
    git pull origin main || true
else
    git clone https://github.com/Steve2109/ContaEC.git "$APP_DIR"
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ── 8. Backend: Python venv + dependencias ──
echo "🐍 Configurando entorno Python..."
cd "$BACKEND_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel
pip install -r requirements.txt

# ── 9. Crear .env ──
echo "🔐 Creando archivo de configuración .env..."
cat > "$BACKEND_DIR/.env" <<EOF
# ContaEC — Configuración de entorno
# Generado automáticamente por install.sh el $(date)

DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
SECRET_KEY=$SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ADMIN_EMAIL=steve.mejia@tymtechnology.shop
ADMIN_PASSWORD=$ADMIN_PASS
CORS_ORIGINS=http://localhost:5173,http://10.0.1.20
ENVIRONMENT=production
CLAMD_SOCKET=/var/run/clamav/clamd.ctl
CLAMD_TIMEOUT=30
VT_API_KEY=
BACKUP_KEY=$BACKUP_KEY
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_TLS=true
MAX_UPLOAD_SIZE_MB=10
UPLOAD_ALLOWED_EXTENSIONS=.xlsx,.xls,.csv,.pdf,.zip,.xml,.json,.png,.jpg,.jpeg
SRI_WS_URL_PROD=https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl
SRI_WS_URL_TEST=https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl
SRI_CONSULTA_RUC_URL=https://srienlinea.sri.gob.ec/sri-catastro-sujeto-servicio-internet/rest/ConsolidadoContribuyente/existePorNumeroRuc
APP_NAME=ContaEC
APP_AUTHOR=T&M Technology Ec
APP_CONTACT_PHONE=0960068866
APP_SUPPORT_EMAIL=info@tymtechnology.shop
APP_DOMAIN=conta.tymtechnology.shop
EOF

chown "$APP_USER:$APP_USER" "$BACKEND_DIR/.env"
chmod 600 "$BACKEND_DIR/.env"

# ── 10. Inicializar base de datos ──
echo "🗄️  Inicializando base de datos..."
cd "$BACKEND_DIR"
python -c "from app.core.database import Base, engine; from app.models import *; Base.metadata.create_all(bind=engine)" || true

# ── 11. Frontend: Build ──
echo "⚛️  Construyendo frontend..."
cd "$FRONTEND_DIR"
npm install
npm run build

# ── 12. Configurar Nginx ──
echo "🌐 Configurando Nginx..."
cat > "$NGINX_CONF" <<'EOF'
server {
    listen 80;
    server_name conta.tymtechnology.shop;
    client_max_body_size 20M;

    root /opt/contaec/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    location /static {
        alias /opt/contaec/backend/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/contaec
rm -f /etc/nginx/sites-enabled/default || true
nginx -t && systemctl restart nginx
systemctl enable nginx

# ── 13. Instalar systemd service ──
echo "⚙️  Instalando servicio systemd..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=ContaEC - Sistema Contable T&M Technology Ec
After=network.target postgresql.service clamav-daemon.service
Wants=postgresql.service clamav-daemon.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$VENV_DIR/bin
Environment=PYTHONPATH=$BACKEND_DIR
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 3
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=contaec

# Límites de recursos (ajustar según LXC: 3 cores, 6GB libres)
LimitAS=4G
LimitRSS=2G
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable contaec
systemctl start contaec

# ── 14. Resumen ──
echo ""
echo "=========================================="
echo "  ✅ Instalación de $APP_NAME completa!"
echo "=========================================="
echo ""
echo "📁 Aplicación:      $APP_DIR"
echo "🐍 Backend:         http://10.0.1.20:8000"
echo "⚛️  Frontend:        http://10.0.1.20 (Nginx)"
echo "🐘 PostgreSQL:      localhost:5432 / $DB_NAME"
echo "🛡️  ClamAV socket:  /var/run/clamav/clamd.ctl"
echo "⚙️  Service:         systemctl status contaec"
echo ""
echo "🔐 Credenciales administrador:"
echo "   Email:    steve.mejia@tymtechnology.shop"
echo "   Password: $ADMIN_PASS"
echo "   ⚠️  CAMBIA ESTA CONTRASEÑA INMEDIATAMENTE en $BACKEND_DIR/.env"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Edita $BACKEND_DIR/.env y cambia ADMIN_PASSWORD."
echo "   2. Agrega tu VT_API_KEY si deseas escaneo con VirusTotal."
echo "   3. Configura SMTP_HOST para envío de correos."
echo "   4. Configura el DNS A de conta.tymtechnology.shop → 10.0.1.20"
echo "   5. Nginx Proxy Manager ya debe apuntar a esta IP."
echo ""
echo "📜 Logs: journalctl -u contaec -f"
echo "=========================================="
