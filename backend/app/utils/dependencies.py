"""
Dependencias y utilidades para las rutas de la API
"""
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from ..core.database import get_db
from ..core.security import decode_token
from ..core.config import settings
from ..models import User
from ..services.auth_service import UserService, LicenseService


# Configuración de OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Obtiene el usuario actual desde el token JWT
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales no válidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        if payload is None:
            raise credentials_exception
        
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if email is None or user_id is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verifica que el usuario esté activo
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verifica que el usuario sea administrador
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return current_user


def check_valid_license(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Verifica que el usuario tenga una licencia válida
    """
    is_valid, days_remaining = LicenseService.check_license_validity(db, current_user.id)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Licencia inválida o expirada. Por favor renueve su licencia."
        )
    
    # Guardar días restantes en el objeto usuario para usar en respuestas
    current_user.days_remaining = days_remaining  # type: ignore
    
    return current_user


def get_client_ip(request: Request) -> Optional[str]:
    """
    Obtiene la IP del cliente considerando proxies
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else None


def sanitize_input(value: str) -> str:
    """
    Sanitiza entradas de texto para prevenir XSS e inyecciones
    """
    if not value:
        return value
    
    # Eliminar caracteres peligrosos
    dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/']
    for char in dangerous_chars:
        value = value.replace(char, '')
    
    # Limitar longitud
    max_length = 1000
    if len(value) > max_length:
        value = value[:max_length]
    
    return value.strip()
