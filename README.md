# ContaEC

Sistema contable con facturación electrónica SRI para Ecuador.

**Stack:** FastAPI + PostgreSQL + React + TailwindCSS  
**Autor:** T&M Technology Ec  
**Contacto:** info@tymtechnology.shop · 0960068866  
**Dominio:** conta.tymtechnology.shop

---

## Instalación rápida (LXC Proxmox / Ubuntu / Debian)

```bash
git clone https://github.com/Steve2109/ContaEC.git
cd ContaEC
chmod +x install.sh
sudo ./install.sh
```

El script automatiza todo: dependencias del sistema, PostgreSQL, ClamAV, Node.js, build del frontend, Nginx, systemd service.

### Requisitos previos
- Ubuntu 20.04+ / Debian 11+ / AlmaLinux 9+
- 3 cores + 4GB RAM mínimo recomendado
- Acceso root o sudo
### Post-instalación
1. Cambia la contraseña de administrador en `/opt/contaec/backend/.env`:
   ```
   ADMIN_PASSWORD=TuNuevaContraseñaSegura123
   ```
2. Reinicia el servicio:
   ```bash
   sudo systemctl restart contaec
   ```
3. Verifica estado:
   ```bash
   sudo systemctl status contaec
   sudo journalctl -u contaec -f
   ```

---
# Instalar dependencias nuevas del frontend
cd frontend
npm install react-i18next i18next i18next-browser-languagedetector
npm install lucide-react recharts

# Build
npm run build

---

## Logs

```bash
# Backend
sudo journalctl -u contaec -f

# Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*.log

# ClamAV
sudo tail -f /var/log/clamav/clamav.log
```

---

## Soporte

**T&M Technology Ec**  
📧 info@tymtechnology.shop  
📱 0960068866  
🌐 conta.tymtechnology.shop
