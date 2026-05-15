"""
Configuración central de la aplicación ContaEC
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str = "postgresql://conta_user:SecurePass2024@localhost:5432/contaec_db"
    
    # Configuración del servidor
    HOST: str = "0.0.0.0"
    PORT: int = 80
    DEBUG: bool = False
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "tu_clave_secreta_muy_segura_cambiala_en_produccion"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Clave maestra para encriptación
    MASTER_ENCRYPTION_KEY: str = "cambia_esta_clave_maestra_por_una_mas_segura"
    
    # Rutas de archivos
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_FOLDER: str = "/workspace/backend/static/uploads"
    TEMP_UPLOAD_FOLDER: str = "/workspace/backend/static/uploads/temp"
    PERMANENT_UPLOAD_FOLDER: str = "/workspace/backend/static/uploads/permanent"
    BACKUP_FOLDER: str = "/workspace/backend/backups"
    
    # ClamAV Configuration
    CLAMAV_ENABLED: bool = True
    CLAMAV_SOCKET: str = "/var/run/clamav/clamd.ctl"
    
    # VirusTotal API
    VIRUSTOTAL_API_KEY: Optional[str] = None
    
    # Admin por defecto
    ADMIN_EMAIL: str = "steve.mejia@tymtechnology.shop"
    ADMIN_PASSWORD: str = "Vitaestcum21.."
    
    # Aplicación
    APP_NAME: str = "ContaEC"
    DEVELOPER: str = "T&M Technology Ec"
    SUPPORT_PHONE: str = "0960068866"
    SUPPORT_EMAIL: str = "info@tymtechnology.shop"
    APP_DOMAIN: str = "conta.tymtechnology.shop"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/workspace/backend/logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
