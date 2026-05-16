"""
Settings API — test SMTP, backup key, language, sandbox toggle.
"""
import os
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional

from app.core.dependencies import get_current_user, get_current_active_user
from app.core.security import encrypt_data, decrypt_data
from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["Settings"])


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


class SMTPTestResponse(BaseModel):
    success: bool
    message: str


# ─── Routes ───

@router.post("/test-smtp", response_model=SMTPTestResponse)
async def test_smtp(
    data: SMTPTestRequest,
    current_user = Depends(get_current_active_user)
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

        return SMTPTestResponse(success=True, message="Correo de prueba enviado correctamente")
    except Exception as e:
        return SMTPTestResponse(success=False, message=f"Error SMTP: {str(e)}")


@router.post("/backup-key")
async def set_backup_key(
    data: BackupKeyRequest,
    current_user = Depends(get_current_active_user)
):
    """Guarda la clave de encriptación de backups del usuario (encriptada)."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        # Encriptar la clave con la llave maestra del sistema
        encrypted = encrypt_data(data.backup_key)
        current_user.encrypted_backup_key = encrypted
        await db.commit()

    return {"success": True, "message": "Clave de backup configurada"}


@router.post("/language")
async def set_language(
    data: LanguageRequest,
    current_user = Depends(get_current_active_user)
):
    """Guarda preferencia de idioma del usuario."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        current_user.language = data.language
        await db.commit()

    return {"success": True, "language": data.language}


@router.post("/sandbox")
async def toggle_sandbox(
    data: SandboxToggleRequest,
    current_user = Depends(get_current_active_user)
):
    """Activa/desactiva modo sandbox para una empresa del usuario."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from app.core.database import async_session_maker
    from app.models.facturacion import Empresa

    async with async_session_maker() as db:
        result = await db.execute(
            select(Empresa).where(
                Empresa.id == data.company_id,
                Empresa.user_id == current_user.id
            )
        )
        empresa = result.scalar_one_or_none()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        empresa.modo_sandbox = data.sandbox
        await db.commit()

    mode = "pruebas" if data.sandbox else "producción"
    return {"success": True, "message": f"Modo {mode} activado", "sandbox": data.sandbox}
