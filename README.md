ContaEC
Sistema contable con facturación electrónica SRI para Ecuador.
Stack: FastAPI + PostgreSQL + React + TailwindCSS  
Autor: T&M Technology Ec  
Contacto: info@tymtechnology.shop · 0960068866  
Dominio: conta.tymtechnology.shop
---
Instalación rápida (LXC Proxmox / Ubuntu / Debian)
```bash
git clone https://github.com/Steve2109/ContaEC.git
cd ContaEC
chmod +x install.sh
sudo ./install.sh
```
El script automatiza todo: dependencias del sistema, PostgreSQL, ClamAV, Node.js, build del frontend, Nginx, systemd service.
Requisitos previos
Ubuntu 20.04+ / Debian 11+ / AlmaLinux 9+
3 cores + 4GB RAM mínimo recomendado
Acceso root o sudo
Post-instalación
Cambia la contraseña de administrador en `/opt/contaec/backend/.env`:
```
   ADMIN_PASSWORD=TuNuevaContraseñaSegura123
   ```
Reinicia el servicio:
```bash
   sudo systemctl restart contaec
   ```
Verifica estado:
```bash
   sudo systemctl status contaec
   sudo journalctl -u contaec -f
   ```
# Instalar dependencias nuevas del frontend
cd frontend
npm install react-i18next i18next i18next-browser-languagedetector
npm install lucide-react recharts

# Build
npm run build