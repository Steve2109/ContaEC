import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENVIRONMENT: str = "production"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://10.0.1.20"

    # Admin (sin defaults de seguridad)
    ADMIN_EMAIL: str = "steve.mejia@tymtechnology.shop"
    ADMIN_PASSWORD: str  # REQUERIDO — sin valor por defecto

    # ClamAV
    CLAMD_SOCKET: str = "/var/run/clamav/clamd.ctl"
    CLAMD_TIMEOUT: int = 30

    # VirusTotal (opcional)
    VT_API_KEY: Optional[str] = None

    # Backup encryption
    BACKUP_KEY: str

    # SMTP (opcional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True

    # File uploads
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_ALLOWED_EXTENSIONS: str = ".xlsx,.xls,.csv,.pdf,.zip,.xml,.json,.png,.jpg,.jpeg"

    # SRI
    SRI_WS_URL_PROD: str = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl"
    SRI_WS_URL_TEST: str = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl"
    SRI_CONSULTA_RUC_URL: str = "https://srienlinea.sri.gob.ec/sri-catastro-sujeto-servicio-internet/rest/ConsolidadoContribuyente/existePorNumeroRuc"

    # App metadata
    APP_NAME: str = "ContaEC"
    APP_AUTHOR: str = "T&M Technology Ec"
    APP_CONTACT_PHONE: str = "0960068866"
    APP_SUPPORT_EMAIL: str = "info@tymtechnology.shop"
    APP_DOMAIN: str = "conta.tymtechnology.shop"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 🔒 Seguridad: forzar que ADMIN_PASSWORD venga del .env
        raw_admin_pass = os.environ.get("ADMIN_PASSWORD", "")
        if not raw_admin_pass or raw_admin_pass.strip() == "":
            raise ValueError(
                "[CRÍTICO] ADMIN_PASSWORD no está definido en el archivo .env. "
                "Por seguridad, la contraseña de administrador NO puede tener un valor por defecto. "
                "Agrega: ADMIN_PASSWORD=TuContraseñaSegura123 al archivo .env antes de iniciar la aplicación."
            )
        # Validar longitud mínima
        if len(self.ADMIN_PASSWORD) < 8:
            raise ValueError(
                "ADMIN_PASSWORD debe tener al menos 8 caracteres."
            )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def upload_allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.UPLOAD_ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()
