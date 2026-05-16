"""
Companies API extended — RUC lookup, config, logo, signature.
"""
import os
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db, get_current_user, get_current_active_user
from app.core.config import settings
from app.core.security import encrypt_data
from app.models.facturacion import Empresa
from app.services.facturacion_service import ConsultaSRI

router = APIRouter(prefix="/companies", tags=["Companies"])

UPLOAD_DIR = getattr(settings, 'UPLOAD_DIR', '/tmp/contaec_uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Schemas ───

class CompanyConfigUpdate(BaseModel):
    razon_social: Optional[str] = None
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    tipo_contribuyente: Optional[str] = None
    obligado_contabilidad: Optional[bool] = None
    rimpe_tipo: Optional[str] = None
    contribuyente_especial: Optional[str] = None
    agente_retencion: Optional[str] = None


# ─── Routes ───

@router.get("/lookup-ruc")
async def lookup_ruc(
    ruc: str,
    current_user = Depends(get_current_active_user)
):
    """Consulta datos de una empresa en el SRI por RUC."""
    # Validar formato RUC ecuatoriano
    if not ruc or len(ruc) not in [13, 10]:
        raise HTTPException(status_code=400, detail="RUC inválido. Debe tener 10 o 13 dígitos.")

    try:
        data = await ConsultaSRI.consultar_ruc(ruc)
        if not data.get("valido"):
            raise HTTPException(status_code=404, detail="RUC no encontrado en el SRI")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error consultando SRI: {str(e)}")


@router.get("/{company_id}/config")
async def get_company_config(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Obtiene configuración completa de una empresa."""
    result = await db.execute(
        select(Empresa).where(
            Empresa.id == company_id,
            Empresa.user_id == current_user.id
        )
    )
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    return {
        "id": empresa.id,
        "ruc": empresa.ruc,
        "razon_social": empresa.razon_social,
        "nombre_comercial": empresa.nombre_comercial,
        "direccion": empresa.direccion_matriz,
        "telefono": empresa.telefono,
        "email": empresa.email,
        "tipo_contribuyente": empresa.tipo_contribuyente,
        "obligado_contabilidad": empresa.obligado_contabilidad,
        "rimpe_tipo": empresa.rimpe_tipo,
        "contribuyente_especial": empresa.contribuyente_especial,
        "agente_retencion": empresa.agente_retencion,
        "logo_url": empresa.logo_url,
        "sandbox": getattr(empresa, 'modo_sandbox', False),
        "firma_valida_hasta": getattr(empresa, 'firma_valida_hasta', None),
    }


@router.put("/{company_id}/config")
async def update_company_config(
    company_id: int,
    data: CompanyConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Actualiza configuración de una empresa."""
    result = await db.execute(
        select(Empresa).where(
            Empresa.id == company_id,
            Empresa.user_id == current_user.id
        )
    )
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(empresa, field):
            setattr(empresa, field, value)

    await db.commit()
    await db.refresh(empresa)
    return {"success": True, "message": "Configuración actualizada"}


@router.post("/{company_id}/logo")
async def upload_logo(
    company_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Sube logotipo de la empresa."""
    # Validar extensión
    allowed = {'.png', '.jpg', '.jpeg', '.svg', '.webp'}
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Formato no permitido: {ext}. Use: {allowed}")

    # Verificar empresa
    result = await db.execute(
        select(Empresa).where(
            Empresa.id == company_id,
            Empresa.user_id == current_user.id
        )
    )
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Guardar archivo
    safe_name = f"logo_{company_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    empresa.logo_url = file_path
    await db.commit()

    return {"success": True, "logo_url": file_path}


@router.post("/{company_id}/firma")
async def upload_signature(
    company_id: int,
    file: UploadFile = File(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Sube firma electrónica (.p12) y la encripta."""
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext != '.p12':
        raise HTTPException(status_code=400, detail="La firma debe ser un archivo .p12")

    result = await db.execute(
        select(Empresa).where(
            Empresa.id == company_id,
            Empresa.user_id == current_user.id
        )
    )
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Leer y encriptar la firma
    content = await file.read()
    encrypted_content = encrypt_data(content.decode('latin-1') if isinstance(content, bytes) else content)
    encrypted_password = encrypt_data(password)

    empresa.firma_electronica = encrypted_content
    empresa.firma_password = encrypted_password

    # Extraer validez del certificado si es posible
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.serialization import pkcs12
        p12 = pkcs12.load_key_and_certificates(content, password.encode())
        cert = p12[1]
        if cert and hasattr(cert, 'not_valid_after'):
            empresa.firma_valida_hasta = cert.not_valid_after_utc
    except Exception:
        pass  # Si falla la extracción, no es crítico

    await db.commit()

    return {
        "success": True,
        "message": "Firma electrónica cargada",
        "valid_until": empresa.firma_valida_hasta.isoformat() if empresa.firma_valida_hasta else None
    }
