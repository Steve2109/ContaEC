"""
Rutas de autenticación y gestión de usuarios
"""
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from pydantic import EmailStr

from ..core.database import get_db
from ..models import User, License, LicenseType
from ..schemas import (
    UserCreate, UserResponse, UserUpdate,
    CompanyCreate, CompanyResponse,
    LicenseResponse, LicenseTypeEnum,
    Token, LoginRequest, MessageResponse,
    UserConfigurationResponse, UserConfigurationCreate
)
from ..services.auth_service import (
    AuthService, UserService, CompanyService,
    LicenseService, UserConfigurationService
)
from ..utils.dependencies import get_current_user, get_current_admin_user, get_client_ip

router = APIRouter(prefix="/api/v1", tags=["Autenticación"])


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Registra un nuevo usuario en el sistema
    """
    try:
        # Crear usuario
        user = UserService.create_user(db, user_data, is_admin=False)
        
        # Log de seguridad
        ip = get_client_ip(request) if request else None
        AuthService.log_security_action(
            db=db,
            user_id=user.id,
            action="REGISTRO_USUARIO",
            ip_address=ip,
            details={"email": user.email}
        )
        
        return user
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/login", response_model=Token)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Inicia sesión y obtiene tokens de acceso
    """
    # Autenticar usuario
    user = AuthService.authenticate_user(db, login_data.email, login_data.password)
    
    if not user:
        # Log de intento fallido
        ip = get_client_ip(request) if request else None
        AuthService.log_security_action(
            db=db,
            user_id=None,
            action="INTENTO_LOGIN_FALLIDO",
            ip_address=ip,
            details={"email": login_data.email},
            is_suspicious=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar licencia (si no es admin)
    if not user.is_admin:
        is_valid, _ = LicenseService.check_license_validity(db, user.id)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Licencia expirada. Contacte al administrador."
            )
    
    # Crear tokens
    tokens = AuthService.create_tokens(user)
    
    # Actualizar último login
    AuthService.update_last_login(db, user)
    
    # Log de éxito
    ip = get_client_ip(request) if request else None
    AuthService.log_security_action(
        db=db,
        user_id=user.id,
        action="LOGIN_EXITOSO",
        ip_address=ip
    )
    
    return tokens


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene información del usuario actual
    """
    return current_user


@router.put("/auth/me", response_model=UserResponse)
def update_current_user(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza datos del usuario actual
    """
    updated_user = UserService.update_user(db, current_user.id, user_data)
    return updated_user


# === EMPRESAS ===

@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva empresa (multiempresa)
    """
    try:
        company = CompanyService.create_company(db, company_data, current_user.id)
        return company
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/companies", response_model=List[CompanyResponse])
def get_my_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las empresas del usuario actual
    """
    companies = CompanyService.get_companies_by_user(db, current_user.id)
    return companies


@router.get("/companies/{ruc}")
def query_company_by_ruc(
    ruc: str,
    db: Session = Depends(get_db)
):
    """
    Consulta información de empresa por RUC (incluye consulta al SRI)
    """
    # Primero buscar en base de datos local
    company = CompanyService.get_company_by_ruc(db, ruc)
    
    if company:
        return {
            "source": "local",
            "data": company
        }
    
    # Si no existe localmente, consultar al SRI
    sri_info = CompanyService.query_sri_info(ruc)
    
    if sri_info:
        return {
            "source": "sri",
            "data": sri_info
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="RUC no encontrado"
    )


# === CONFIGURACIÓN DE USUARIO ===

@router.get("/config", response_model=UserConfigurationResponse)
def get_user_configuration(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la configuración del usuario actual
    """
    config = UserConfigurationService.get_user_config(db, current_user.id)
    
    if not config:
        # Crear configuración vacía si no existe
        config = UserConfigurationService.update_configuration(
            db, current_user.id, UserConfigurationCreate()
        )
    
    # Verificar si tiene firma
    has_firma = bool(config.encrypted_firma_electronica)
    has_smtp = bool(config.encrypted_smtp_config)
    has_backup = bool(config.encrypted_backup_key)
    
    return UserConfigurationResponse(
        id=config.id,
        user_id=config.user_id,
        language=config.language,
        theme=config.theme,
        is_sandbox_mode=config.is_sandbox_mode,
        has_firma=has_firma,
        firma_validity=config.firma_validity,
        has_smtp_config=has_smtp,
        has_backup_key=has_backup,
        created_at=config.created_at
    )


@router.put("/config", response_model=UserConfigurationResponse)
def update_user_configuration(
    config_data: UserConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza la configuración del usuario
    Incluye: firma electrónica, clave de firma, SMTP, backup key
    """
    config = UserConfigurationService.update_configuration(db, current_user.id, config_data)
    
    has_firma = bool(config.encrypted_firma_electronica)
    has_smtp = bool(config.encrypted_smtp_config)
    has_backup = bool(config.encrypted_backup_key)
    
    return UserConfigurationResponse(
        id=config.id,
        user_id=config.user_id,
        language=config.language,
        theme=config.theme,
        is_sandbox_mode=config.is_sandbox_mode,
        has_firma=has_firma,
        firma_validity=config.firma_validity,
        has_smtp_config=has_smtp,
        has_backup_key=has_backup,
        created_at=config.created_at
    )


# === LICENCIAS ===

@router.get("/license", response_model=LicenseResponse)
def get_user_license(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la licencia del usuario actual
    """
    license_obj = LicenseService.get_user_license(db, current_user.id)
    
    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró licencia para este usuario"
        )
    
    # Calcular días restantes
    _, days_remaining = LicenseService.check_license_validity(db, current_user.id)
    
    return LicenseResponse(
        id=license_obj.id,
        user_id=license_obj.user_id,
        license_type=license_obj.license_type,
        start_date=license_obj.start_date,
        end_date=license_obj.end_date,
        is_active=license_obj.is_active,
        payment_reference=license_obj.payment_reference,
        created_at=license_obj.created_at,
        days_remaining=days_remaining
    )
