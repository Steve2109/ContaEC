"""
Settings API — test SMTP, backup key, language, sandbox toggle.
Adaptado para SQLAlchemy sincrónico.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_sync, get_current_admin_user_sync, get_db_sync
from app.core.security import encrypt_sensitive_data, decrypt_sensitive_data
from app.core.config import settings

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


# ─── Schemas ───

class SMTPTestRequest(BaseModel):
    host: str
    port: int = Field(default=587)
    username: str
    password: str
    use_tls: bool = True
    to_email: str = Field(default="test@example.com")
    from_email: str


class BackupKeyRequest(BaseModel):
    backup_key: str = Field(min_length=8, max_length=64)


class LanguageRequest(BaseModel):
    language: str = Field(default="es-EC", pattern="^(es-EC|en)$")


class SandboxToggleRequest(BaseModel):
    company_id: int
    sandbox: bool


# ─── Routes ───

@router.post("/test-smtp")
async def test_smtp(
    data: SMTPTestRequest,
    current_user = Depends(get_current_user_sync)
):
    """Envía un correo de prueba con los parámetros SMTP proporcionados."""
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = data.from_email
        msg['To'] = data.to_email
        msg['Subject'] = 'ContaEC — Prueba de configuración SMTP'
        msg.attach(MIMEText(
            '<h3>¡Funciona!</h3><p>La configuración SMTP de ContaEC está correcta.</p>',
            'html'
        ))

        smtp = aiosmtplib.SMTP(hostname=data.host, port=data.port, use_tls=data.use_tls)
        await smtp.connect()
        if data.use_tls and data.port == 587:
            await smtp.starttls()
        await smtp.login(data.username, data.password)
        await smtp.send_message(msg)
        await smtp.quit()

        return {"success": True, "message": "Correo de prueba enviado correctamente"}
    except Exception as e:
        return {"success": False, "message": f"Error SMTP: {str(e)}"}


@router.post("/backup-key")
async def set_backup_key(
    data: BackupKeyRequest,
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Guarda la clave de encriptación de backups del usuario (encriptada en BD)."""
    # Encriptar la clave con la llave maestra del sistema
    encrypted = encrypt_sensitive_data(data.backup_key)
    
    from app.models import UserConfiguration
    
    # Buscar o crear configuración del usuario
    config = db.query(UserConfiguration).filter(
        UserConfiguration.user_id == current_user.id
    ).first()
    
    if not config:
        config = UserConfiguration(user_id=current_user.id)
        db.add(config)
    
    config.encrypted_backup_key = encrypted
    db.commit()

    return {"success": True, "message": "Clave de backup configurada"}


@router.post("/language")
async def set_language(
    data: LanguageRequest,
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Guarda preferencia de idioma del usuario."""
    from app.models import UserConfiguration
    
    config = db.query(UserConfiguration).filter(
        UserConfiguration.user_id == current_user.id
    ).first()
    
    if not config:
        config = UserConfiguration(user_id=current_user.id)
        db.add(config)
    
    config.language = data.language
    db.commit()

    return {"success": True, "language": data.language}


@router.post("/sandbox")
async def toggle_sandbox(
    data: SandboxToggleRequest,
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Activa/desactiva modo sandbox para una empresa del usuario."""
    from app.models import Company
    
    empresa = db.query(Company).filter(
        Company.id == data.company_id,
        Company.owner_id == current_user.id
    ).first()
    
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    empresa.modo_sandbox = data.sandbox
    db.commit()

    mode = "pruebas" if data.sandbox else "producción"
    return {"success": True, "message": f"Modo {mode} activado", "sandbox": data.sandbox}
