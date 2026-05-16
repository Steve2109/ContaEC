"""
Companies API extended — RUC lookup, config, logo, signature.
Adaptado para SQLAlchemy sincrónico.
"""
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_sync, get_current_user_sync, get_current_admin_user_sync
from app.core.config import settings
from app.core.security import encrypt_sensitive_data, decrypt_sensitive_data

router = APIRouter(prefix="/api/v1/companies", tags=["Companies"])

UPLOAD_DIR = getattr(settings, 'UPLOAD_FOLDER', '/tmp/contaec_uploads')
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
    current_user = Depends(get_current_user_sync)
):
    """Consulta datos de una empresa en el SRI por RUC."""
    from app.services.facturacion_service import ConsultaSRI
    
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
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Obtiene configuración completa de una empresa."""
    from app.models import Company
    
    empresa = db.query(Company).filter(
        Company.id == company_id,
        Company.owner_id == current_user.id
    ).first()
    
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    return {
        "id": empresa.id,
        "ruc": empresa.ruc,
        "razon_social": empresa.razon_social,
        "nombre_comercial": empresa.nombre_comercial,
        "direccion": empresa.direccion,
        "telefono": empresa.telefono,
        "email": empresa.email,
        "tipo_contribuyente": getattr(empresa, 'tipo_contribuyente', None),
        "obligado_contabilidad": getattr(empresa, 'obligado_contabilidad', None),
        "rimpe_tipo": getattr(empresa, 'rimpe_tipo', None),
        "contribuyente_especial": getattr(empresa, 'contribuyente_especial', None),
        "agente_retencion": getattr(empresa, 'agente_retencion', None),
        "logo_url": getattr(empresa, 'logo_url', None),
        "sandbox": getattr(empresa, 'modo_sandbox', False),
        "firma_valida_hasta": getattr(empresa, 'firma_valida_hasta', None),
    }


@router.put("/{company_id}/config")
async def update_company_config(
    company_id: int,
    data: CompanyConfigUpdate,
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Actualiza configuración de una empresa."""
    from app.models import Company
    
    empresa = db.query(Company).filter(
        Company.id == company_id,
        Company.owner_id == current_user.id
    ).first()
    
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(empresa, field):
            setattr(empresa, field, value)

    db.commit()
    db.refresh(empresa)
    return {"success": True, "message": "Configuración actualizada"}


@router.post("/{company_id}/logo")
async def upload_logo(
    company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Sube logotipo de la empresa."""
    # Validar extensión
    allowed = {'.png', '.jpg', '.jpeg', '.svg', '.webp'}
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Formato no permitido: {ext}. Use: {allowed}")

    from app.models import Company
    
    empresa = db.query(Company).filter(
        Company.id == company_id,
        Company.owner_id == current_user.id
    ).first()
    
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Guardar archivo
    safe_name = f"logo_{company_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)

    empresa.logo_url = file_path
    db.commit()

    return {"success": True, "logo_url": file_path}


@router.post("/{company_id}/firma")
async def upload_signature(
    company_id: int,
    file: UploadFile = File(...),
    password: str = Form(...),
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Sube firma electrónica (.p12) y la encripta."""
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext != '.p12':
        raise HTTPException(status_code=400, detail="La firma debe ser un archivo .p12")

    from app.models import Company
    
    empresa = db.query(Company).filter(
        Company.id == company_id,
        Company.owner_id == current_user.id
    ).first()
    
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Leer y encriptar la firma
    content = await file.read()
    encrypted_content = encrypt_sensitive_data(content.decode('latin-1') if isinstance(content, bytes) else content)
    encrypted_password = encrypt_sensitive_data(password)

    empresa.firma_electronica = encrypted_content
    empresa.firma_password = encrypted_password

    # Extraer validez del certificado si es posible
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.primitives import serialization
        p12 = pkcs12.load_key_and_certificates(content, password.encode())
        cert = p12[1]
        if cert and hasattr(cert, 'not_valid_after_utc'):
            empresa.firma_valida_hasta = cert.not_valid_after_utc
        elif cert and hasattr(cert, 'not_valid_after'):
            empresa.firma_valida_hasta = cert.not_valid_after
    except Exception:
        pass

    db.commit()

    return {
        "success": True,
        "message": "Firma electrónica cargada",
        "valid_until": empresa.firma_valida_hasta.isoformat() if empresa.firma_valida_hasta else None
    }
