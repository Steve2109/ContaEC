"""
Utilidades de seguridad para ContaEC
- Hash de contraseñas
- Generación y validación de tokens JWT
- Encriptación de datos sensibles
"""
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
import hashlib
from .config import settings

# Contexto para hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Clave de encriptación para datos sensibles
def get_fernet() -> Fernet:
    """
    Obtiene instancia de Fernet para encriptación/desencriptación
    """
    raw_key = settings.MASTER_ENCRYPTION_KEY.encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw_key).digest())
    return Fernet(key)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña plana coincide con el hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera hash de una contraseña
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea token de acceso JWT
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea token de refresco JWT
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un token JWT
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def encrypt_sensitive_data(data: str) -> str:
    """
    Encripta datos sensibles (firmas electrónicas, claves, etc.)
    """
    fernet = get_fernet()
    encrypted = fernet.encrypt(data.encode())
    return encrypted.decode()


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Desencripta datos sensibles
    """
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_data.encode())
    return decrypted.decode()
