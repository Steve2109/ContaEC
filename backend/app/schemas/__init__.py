"""
Esquemas Pydantic para validación de datos
Fase 1-2: Usuarios, Empresas, Licencias, Auth
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    USER = "user"
    ACCOUNTANT = "accountant"


class LicenseTypeEnum(str, Enum):
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"


# === USUARIOS ===

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Contraseña mínima 8 caracteres")


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    role: UserRoleEnum
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None


# === EMPRESAS ===

class CompanyBase(BaseModel):
    ruc: str = Field(..., min_length=13, max_length=13, pattern=r'^\d{13}$')
    business_name: str
    trade_name: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    business_name: Optional[str] = None
    trade_name: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    owner_id: int
    logo_path: Optional[str] = None
    is_active: bool
    created_at: datetime


class UserCompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    company_id: int
    role: UserRoleEnum
    created_at: datetime
    company: CompanyResponse


# === LICENCIAS ===

class LicenseBase(BaseModel):
    license_type: LicenseTypeEnum


class LicenseCreate(LicenseBase):
    user_id: int
    start_date: datetime
    end_date: datetime


class LicenseUpdate(BaseModel):
    license_type: Optional[LicenseTypeEnum] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    payment_reference: Optional[str] = None


class LicenseResponse(LicenseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    start_date: datetime
    end_date: datetime
    is_active: bool
    payment_reference: Optional[str] = None
    created_at: datetime
    days_remaining: Optional[int] = None


# === CONFIGURACIÓN DE USUARIO ===

class SMTPConfig(BaseModel):
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False
    from_email: Optional[EmailStr] = None


class UserConfigurationBase(BaseModel):
    language: str = "es_EC"
    theme: str = "light"
    is_sandbox_mode: bool = False


class UserConfigurationCreate(UserConfigurationBase):
    firma_electronica: Optional[str] = None
    firma_clave: Optional[str] = None
    firma_validity: Optional[datetime] = None
    smtp_config: Optional[SMTPConfig] = None
    backup_key: Optional[str] = None


class UserConfigurationUpdate(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None
    is_sandbox_mode: Optional[bool] = None
    firma_validity: Optional[datetime] = None
    smtp_config: Optional[SMTPConfig] = None


class UserConfigurationResponse(UserConfigurationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    has_firma: bool = False
    firma_validity: Optional[datetime] = None
    has_smtp_config: bool = False
    has_backup_key: bool = False
    created_at: datetime


# === AUTH ===

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# === ADMINISTRADOR ===

class AdminDashboardSummary(BaseModel):
    total_users: int
    active_users: int
    total_companies: int
    licenses_expiring_soon: int
    licenses_expired: int
    system_health: str


class SystemHealthStatus(BaseModel):
    database: str
    clamav: str
    disk_usage: float
    memory_usage: float
    cpu_usage: float
    status: str


# === RESPUESTAS GENÉRICAS ===

class MessageResponse(BaseModel):
    message: str
    success: bool = True


class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    pages: int
