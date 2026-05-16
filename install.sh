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

PYTHON_VERSION="3.13"

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
echo "🔧 Versión Python: $PYTHON_VERSION"

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
        python3-full \
        build-essential \
        postgresql postgresql-contrib \
        nginx git curl wget \
        clamav clamav-daemon \
        nodejs npm \
        libpq-dev \
        libxml2-dev libxslt1-dev \
        libxmlsec1-dev libxmlsec1-openssl \
        pkg-config \
        meson ninja-build \
        libffi-dev \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        liblzma-dev \
        libgdbm-dev \
        libc6-dev

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
        pkgconfig \
        meson ninja-build \
        libffi-devel \
        openssl-devel \
        zlib-devel \
        bzip2-devel \
        readline-devel \
        sqlite-devel \
        ncurses-devel \
        xz-devel \
        tk-devel \
        gdbm-devel \
        glibc-devel
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
        if [ -S /var/run/clamav/clamd.ctl ] || [ -S /run/clamav/clamd.ctl ]; then
            echo "✅ Socket de clamd encontrado"
            break
        fi
        echo "⏳ Esperando socket de clamd... ($i/30)"
        sleep 2
    done
    if [ ! -S /var/run/clamav/clamd.ctl ] && [ ! -S /run/clamav/clamd.ctl ]; then
        echo "⚠️  Socket de clamd no encontrado. Se usará clamscan como fallback."
    fi
fi

# ── 5. Configurar PostgreSQL ──
echo "🐘 Configurando PostgreSQL..."
if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    systemctl enable postgresql
    systemctl start postgresql
    PG_VERSION=$(pg_lsclusters | grep online | awk '{print $1}' | head -1)
    if [ -z "$PG_VERSION" ]; then
        PG_VERSION=$(ls /etc/postgresql/ | sort -V | tail -1)
    fi
    echo "📦 Versión PostgreSQL detectada: $PG_VERSION"
    
    # Crear usuario y base de datos
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\" | grep -q 1 || createuser -s $DB_USER" || true
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\" | grep -q 1 || createdb $DB_NAME -O $DB_USER" || true
    su - postgres -c "psql -c \"ALTER USER $DB_USER WITH PASSWORD '$DB_USER'\"" || true
    su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER\"" || true
    
    # Configurar acceso local
    PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    if [ -f "$PG_HBA" ]; then
        sed -i 's/scram-sha-256/trust/g' "$PG_HBA" || true
        sed -i 's/peer/trust/g' "$PG_HBA" || true
        systemctl restart postgresql
    fi
elif [ "$OS" == "almalinux" ] || [ "$OS" == "rocky" ]; then
    postgresql-setup --initdb || true
    systemctl enable postgresql
    systemctl start postgresql
    
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\" | grep -q 1 || createuser -s $DB_USER" || true
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\" | grep -q 1 || createdb $DB_NAME -O $DB_USER" || true
    su - postgres -c "psql -c \"ALTER USER $DB_USER WITH PASSWORD '$DB_USER'\"" || true
fi

# ── 6. Crear usuario de aplicación ──
echo "👤 Creando usuario de aplicación: $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$APP_DIR" -m "$APP_USER" || true
fi

# ── 7. Clonar repositorio ──
echo "📥 Clonando repositorio $APP_NAME..."
if [ -d "$APP_DIR/.git" ]; then
    echo "⚠️  Repositorio ya existe. Haciendo pull..."
    cd "$APP_DIR" && git pull origin main || true
else
    rm -rf "$APP_DIR"
    git clone https://github.com/Steve2109/ContaEC.git "$APP_DIR" || {
        echo "❌ Error clonando repositorio. Verifica que sea público o que tengas acceso."
        exit 1
    }
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ── 8. Configurar entorno Python ──
echo "🐍 Configurando entorno Python..."
cd "$BACKEND_DIR"

# Crear venv con Python 3 si python3.13 no existe
PYTHON_BIN=$(command -v python3.13 || command -v python3 || command -v python)
echo "Usando Python: $PYTHON_BIN"

$PYTHON_BIN -m venv "$VENV_DIR" || {
    echo "❌ Error creando virtual environment"
    exit 1
}

source "$VENV_DIR/bin/activate"

# Actualizar pip, wheel, setuptools primero
pip install --upgrade pip wheel setuptools

# Instalar dependencias del requirements.txt
if [ -f "requirements.txt" ]; then
    echo "📦 Instalando dependencias desde requirements.txt..."
    pip install -r requirements.txt || {
        echo "⚠️  Algunas dependencias fallaron. Intentando instalar una por una..."
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ -z "$line" || "$line" =~ ^# ]] && continue
            echo "  → $line"
            pip install "$line" || echo "    ⚠️  Falló: $line"
        done < requirements.txt
    }
else
    echo "⚠️  No se encontró requirements.txt. Instalando dependencias mínimas..."
    pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose passlib python-multipart \
        pydantic pydantic-settings python-dotenv cryptography aiofiles openpyxl pandas numpy \
        lxml requests httpx reportlab aiosmtplib slowapi jinja2 aiohttp pypdf2
fi

# ── 9. Configurar variables de entorno ──
echo "⚙️  Configurando archivo .env..."
ENV_FILE="$BACKEND_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" <<EOF
# ContaEC — Configuración de entorno
# Generado automáticamente por install.sh

APP_NAME=ContaEC
DEVELOPER=T&M Technology Ec
SUPPORT_EMAIL=info@tymtechnology.shop
SUPPORT_PHONE=0960068866
SECRET_KEY=$(openssl rand -hex 32)
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Admin credentials — CAMBIA ESTA CONTRASEÑA INMEDIATAMENTE
ADMIN_EMAIL=steve.mejia@tymtechnology.shop
ADMIN_PASSWORD=Vitaestcum21..

# Base de datos
DATABASE_URL=postgresql://$DB_USER:$DB_USER@localhost:5432/$DB_NAME

# Servidor
HOST=0.0.0.0
PORT=8000

# CORS
CORS_ORIGINS=https://conta.tymtechnology.shop,https://10.0.1.20,http://localhost:3000

# Uploads
UPLOAD_FOLDER=/tmp/contaec_uploads
TEMP_UPLOAD_FOLDER=/tmp/contaec_temp
PERMANENT_UPLOAD_FOLDER=/tmp/contaec_permanent
EXPORT_TEMP_FOLDER=/tmp/contaec_exports
BACKUP_FOLDER=/tmp/contaec_backups
MAX_UPLOAD_SIZE=10485760

# Rate limiting
RATE_LIMIT_PER_MINUTE=100

# ClamAV
CLAMD_SOCKET=/var/run/clamav/clamd.ctl

# Logging
LOG_LEVEL=INFO
LOG_FILE=/tmp/contaec_logs/app.log
EOF
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "✅ Archivo .env creado en $ENV_FILE"
    echo "⚠️  IMPORTANTE: Revisa y actualiza las credenciales en $ENV_FILE"
else
    echo "⚠️  Archivo .env ya existe. No se sobrescribió."
fi

# ── 10. Configurar Nginx ──
echo "🌐 Configurando Nginx..."
if [ ! -f "$NGINX_CONF" ]; then
    cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name conta.tymtechnology.shop 10.0.1.20;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    location /static {
        alias $APP_DIR/frontend/dist;
        expires 30d;
    }

    error_log /var/log/nginx/contaec-error.log;
    access_log /var/log/nginx/contaec-access.log;
}
EOF

    rm -f /etc/nginx/sites-enabled/default
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/contaec
    nginx -t && systemctl restart nginx
    echo "✅ Nginx configurado"
else
    echo "⚠️  Configuración de Nginx ya existe"
fi

# ── 11. Instalar dependencias del frontend ──
echo "📦 Instalando dependencias del frontend..."
cd "$FRONTEND_DIR"

# Instalar dependencias adicionales
npm install react-i18next i18next i18next-browser-languagedetector recharts lucide-react || true

npm install || {
    echo "⚠️  Algunas dependencias del frontend fallaron. Verificando..."
    npm install --legacy-peer-deps || true
}

# Build del frontend
echo "🔨 Compilando frontend..."
npm run build || {
    echo "⚠️  Build del frontend falló. Verificando errores..."
    npm audit fix --force || true
    npm run build || echo "❌ Build falló. Revisa los errores manualmente."
}

# ── 12. Configurar systemd ──
echo "🔧 Configurando servicio systemd..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=ContaEC - Sistema Contable T&M Technology Ec
Documentation=https://conta.tymtechnology.shop
After=network.target postgresql.service clamav-daemon.service
Wants=postgresql.service clamav-daemon.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$VENV_DIR/bin
Environment=PYTHONPATH=$BACKEND_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=contaec

# Seguridad: restricciones de sistema de archivos
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/tmp/contaec_uploads /tmp/contaec_temp /tmp/contaec_permanent /tmp/contaec_exports /tmp/contaec_backups /tmp/contaec_logs

# Límites de recursos (ajustar según LXC: 3 cores, 6GB libres)
LimitAS=4G
LimitRSS=2G
LimitNOFILE=65535
LimitNPROC=512

# Tiempo de espera para shutdown graceful
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable contaec

# ── 13. Crear directorios necesarios ──
echo "📁 Creando directorios de trabajo..."
mkdir -p /tmp/contaec_uploads /tmp/contaec_temp /tmp/contaec_permanent \
         /tmp/contaec_exports /tmp/contaec_backups /tmp/contaec_logs
chown -R "$APP_USER:$APP_USER" /tmp/contaec_* || true
chmod 750 /tmp/contaec_*

# ── 14. Iniciar aplicación ──
echo "🚀 Iniciando $APP_NAME..."
systemctl start contaec || {
    echo "⚠️  Error iniciando el servicio. Verificando logs..."
    journalctl -u contaec --no-pager -n 50 || true
}

# ── 15. Verificar estado ──
echo ""
echo "=========================================="
echo "  ✅ Instalación de $APP_NAME completada"
echo "=========================================="
echo ""
echo "📌 URLs de acceso:"
echo "   • App:     https://conta.tymtechnology.shop"
echo "   • API:     http://10.0.1.20/api/v1"
echo "   • Docs:    http://10.0.1.20/docs"
echo "   • Admin:   steve.mejia@tymtechnology.shop"
echo ""
echo "📌 Archivos importantes:"
echo "   • .env:    $ENV_FILE"
echo "   • Logs:    journalctl -u contaec -f"
echo "   • Nginx:   /var/log/nginx/"
echo ""
echo "📌 Comandos útiles:"
echo "   • Iniciar:   systemctl start contaec"
echo "   • Detener:   systemctl stop contaec"
echo "   • Reiniciar: systemctl restart contaec"
echo "   • Estado:    systemctl status contaec"
echo "   • Logs:      journalctl -u contaec -f"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   1. Cambia la contraseña admin en $ENV_FILE si no la has cambiado"
echo "   2. Configura tu dominio SSL con certbot si es necesario"
echo "   3. Verifica que ClamAV está funcionando: systemctl status clamav-daemon"
echo ""
echo "=========================================="
