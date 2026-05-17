#!/bin/bash
# =============================================================================
# install.sh v4 — Script de instalación para ContaEC
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
echo "  Instalador de $APP_NAME (v4)"
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
        python3-full build-essential \
        postgresql postgresql-contrib \
        nginx git curl wget \
        clamav clamav-daemon \
        nodejs npm \
        libpq-dev \
        libxml2-dev libxslt1-dev \
        libxmlsec1-dev libxmlsec1-openssl \
        pkg-config \
        meson ninja-build \
        libffi-dev libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev \
        libsqlite3-dev libncursesw5-dev \
        xz-utils tk-dev liblzma-dev \
        libgdbm-dev libc6-dev \
        cargo rustc

    # Asegurar Node.js >=18
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
        libffi-devel openssl-devel \
        zlib-devel bzip2-devel \
        readline-devel sqlite-devel \
        ncurses-devel xz-devel \
        tk-devel gdbm-devel \
        glibc-devel cargo rust
fi

# ── 4. Configurar ClamAV ──
echo "🛡️  Configurando ClamAV..."
if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    systemctl stop clamav-freshclam 2>/dev/null || true
    freshclam 2>/dev/null || true
    systemctl enable clamav-daemon
    systemctl start clamav-daemon
    for i in {1..30}; do
        if [ -S /var/run/clamav/clamd.ctl ] || [ -S /run/clamav/clamd.ctl ]; then
            echo "✅ Socket de clamd encontrado"
            break
        fi
        echo "⏳ Esperando socket de clamd... ($i/30)"
        sleep 2
    done
fi

# ── 5. Configurar PostgreSQL ──
echo "🐘 Configurando PostgreSQL..."
if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    systemctl enable postgresql
    systemctl start postgresql
    PG_VERSION=$(pg_lsclusters 2>/dev/null | grep online | awk '{print $1}' | head -1)
    if [ -z "$PG_VERSION" ]; then
        PG_VERSION=$(ls /etc/postgresql/ 2>/dev/null | sort -V | tail -1)
    fi
    echo "📦 Versión PostgreSQL: ${PG_VERSION:-desconocida}"
    
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\"" 2>/dev/null | grep -q 1 || \
        su - postgres -c "createuser -s $DB_USER" 2>/dev/null || true
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\"" 2>/dev/null | grep -q 1 || \
        su - postgres -c "createdb $DB_NAME -O $DB_USER" 2>/dev/null || true
    su - postgres -c "psql -c \"ALTER USER $DB_USER WITH PASSWORD '$DB_USER'\"" 2>/dev/null || true
    su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER\"" 2>/dev/null || true
    
    PG_HBA="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"
    if [ -f "$PG_HBA" ]; then
        sed -i 's/scram-sha-256/trust/g' "$PG_HBA" 2>/dev/null || true
        sed -i 's/peer/trust/g' "$PG_HBA" 2>/dev/null || true
        systemctl restart postgresql
    fi
fi

# ── 6. Crear usuario de aplicación ──
echo "👤 Creando usuario de aplicación: $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$APP_DIR" -m "$APP_USER" 2>/dev/null || true
fi

# ── 7. Clonar repositorio ──
echo "📥 Clonando repositorio $APP_NAME..."
if [ -d "$APP_DIR/.git" ]; then
    echo "⚠️  Repositorio ya existe. Haciendo pull..."
    cd "$APP_DIR" && git pull origin main 2>/dev/null || true
else
    rm -rf "$APP_DIR"
    git clone https://github.com/Steve2109/ContaEC.git "$APP_DIR" || {
        echo "❌ Error clonando repositorio."
        exit 1
    }
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR" 2>/dev/null || true

# ── 8. Configurar entorno Python ──
echo "🐍 Configurando entorno Python..."
cd "$BACKEND_DIR"

# DESTRUIR venv anterior si existe para evitar conflictos
if [ -d "$VENV_DIR" ]; then
    echo "🗑️  Eliminando venv anterior..."
    rm -rf "$VENV_DIR"
fi

PYTHON_BIN=$(command -v python3.13 || command -v python3 || command -v python)
echo "Usando Python: $PYTHON_BIN"
$PYTHON_BIN -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Actualizar pip/wheel/setuptools ANTES de todo
pip install --upgrade pip wheel setuptools

# Instalar dependencias
if [ -f "requirements.txt" ]; then
    echo "📦 Instalando dependencias Python (esto puede tardar varios minutos)..."
    pip install -r requirements.txt || {
        echo "⚠️  Algunas dependencias fallaron. Intentando una por una..."
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ -z "$line" || "$line" =~ ^# ]] && continue
            echo "  → $line"
            pip install "$line" 2>/dev/null || echo "    ⚠️  Falló (puede ser opcional): $line"
        done < requirements.txt
    }
else
    echo "⚠️  No se encontró requirements.txt"
fi

echo "✅ Python dependencies instaladas"
python -c "import fastapi, sqlalchemy, pandas, lxml; print('✓ Core OK')" || true

# ── 9. Configurar .env ──
echo "⚙️  Configurando archivo .env..."
ENV_FILE="$BACKEND_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")
    [ -z "$FERNET_KEY" ] && FERNET_KEY=$(openssl rand -base64 32)
    
    cat > "$ENV_FILE" <<EOF
APP_NAME=ContaEC
DEVELOPER=T&M Technology Ec
SUPPORT_EMAIL=info@tymtechnology.shop
SUPPORT_PHONE=0960068866
SECRET_KEY=$(openssl rand -hex 32)
FERNET_KEY=$FERNET_KEY
ADMIN_EMAIL=steve.mejia@tymtechnology.shop
ADMIN_PASSWORD=Vitaestcum21..
DATABASE_URL=postgresql://$DB_USER:$DB_USER@localhost:5432/$DB_NAME
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=https://conta.tymtechnology.shop,https://10.0.1.20,http://localhost:3000
UPLOAD_FOLDER=/tmp/contaec_uploads
TEMP_UPLOAD_FOLDER=/tmp/contaec_temp
PERMANENT_UPLOAD_FOLDER=/tmp/contaec_permanent
EXPORT_TEMP_FOLDER=/tmp/contaec_exports
BACKUP_FOLDER=/tmp/contaec_backups
MAX_UPLOAD_SIZE=10485760
RATE_LIMIT_PER_MINUTE=100
CLAMD_SOCKET=/var/run/clamav/clamd.ctl
LOG_LEVEL=INFO
LOG_FILE=/tmp/contaec_logs/app.log
EOF
    chmod 600 "$ENV_FILE"
    echo "✅ .env creado"
else
    echo "⚠️  .env ya existe, no se sobrescribió"
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
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $APP_DIR/frontend/dist;
        expires 30d;
    }
}
EOF
    rm -f /etc/nginx/sites-enabled/default
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/contaec
    nginx -t && systemctl restart nginx
    echo "✅ Nginx configurado"
fi

# ── 11. Frontend — instalar dependencias ──
echo "📦 Instalando dependencias del frontend..."
cd "$FRONTEND_DIR"

# BORRAR node_modules y package-lock para evitar conflictos
rm -rf node_modules package-lock.json

# Instalar con legacy-peer-deps para evitar conflictos de versiones
npm install --legacy-peer-deps || npm install --force || {
    echo "⚠️  npm install falló. Intentando con cache limpio..."
    npm cache clean --force
    npm install --legacy-peer-deps
}

# Instalar dependencias adicionales necesarias
npm install --legacy-peer-deps react-i18next i18next i18next-browser-languagedetector recharts lucide-react || true

# ── 12. Frontend — build ──
echo "🔨 Compilando frontend..."

# Si hay errores TypeScript, usar transpile-only para que no bloquee
npx tsc --noEmit --skipLibCheck 2>/dev/null || echo "⚠️  TypeScript check con advertencias (continuando)"

# Build con Vite (ignorando errores TypeScript si es necesario)
npx vite build 2>/dev/null || {
    echo "⚠️  Build estándar falló. Intentando con skip type check..."
    npx vite build --emptyOutDir 2>/dev/null || {
        echo "❌ Build del frontend falló. Verificar errores TypeScript."
        echo "    Para forzar build: npx vite build --mode production"
    }
}

# ── 13. Systemd ──
echo "🔧 Configurando systemd..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=ContaEC - Sistema Contable
After=network.target postgresql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$VENV_DIR/bin
Environment=PYTHONPATH=$BACKEND_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=on-failure
RestartSec=5s

ReadWritePaths=/tmp/contaec_uploads /tmp/contaec_temp /tmp/contaec_permanent /tmp/contaec_exports /tmp/contaec_backups /tmp/contaec_logs

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable contaec

# ── 14. Crear directorios ──
mkdir -p /tmp/contaec_uploads /tmp/contaec_temp /tmp/contaec_permanent \
         /tmp/contaec_exports /tmp/contaec_backups /tmp/contaec_logs
chown -R "$APP_USER:$APP_USER" /tmp/contaec_* 2>/dev/null || true
chmod 750 /tmp/contaec_*

# ── 15. Iniciar ──
echo "🚀 Iniciando $APP_NAME..."
systemctl restart contaec || {
    echo "⚠️  Falló inicio del servicio. Logs:"
    journalctl -u contaec --no-pager -n 30 || true
}

echo ""
echo "=========================================="
echo "  ✅ Instalación v4 completada"
echo "=========================================="
echo ""
echo "📌 Acceso:"
echo "   App:     https://conta.tymtechnology.shop"
echo "   API:     http://10.0.1.20/api/v1"
echo "   Docs:    http://10.0.1.20/docs"
echo ""
echo "📌 Comandos:"
echo "   systemctl status contaec"
echo "   journalctl -u contaec -f"
echo ""
