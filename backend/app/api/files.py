"""
Rutas de escaneo de archivos con ClamAV
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
import aiofiles

from ..core.database import get_db
from ..core.config import settings
from ..models import User
from ..services.file_security_service import FileSecurityService
from ..utils.dependencies import get_current_user, get_client_ip

router = APIRouter(prefix="/api/v1/files", tags=["Archivos"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    use_virustotal: bool = Form(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """
    Sube un archivo y lo escanea con ClamAV (y opcionalmente VirusTotal)
    
    Flujo:
    1. Guarda temporalmente
    2. Escanea con ClamAV
    3. Si está limpio, mueve a ubicación definitiva
    4. Si tiene malware, elimina y notifica
    """
    # Verificar que el tipo de archivo sea permitido
    allowed_extensions = ['.xlsx', '.xls', '.csv', '.zip', '.pdf', '.xml', '.txt']
    safe_name = Path(file.filename or "").name
    file_ext = os.path.splitext(safe_name)[1].lower() if safe_name else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(allowed_extensions)}"
        )
    
    # Crear directorios si no existen
    os.makedirs(settings.TEMP_UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(settings.PERMANENT_UPLOAD_FOLDER, exist_ok=True)
    
    # Guardar archivo temporalmente
    temp_file_path = os.path.join(settings.TEMP_UPLOAD_FOLDER, f"{current_user.id}_{safe_name}")
    
    try:
        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # Escanear archivo con ClamAV
        scanner = FileSecurityService()
        is_safe, message, threat_name = scanner.scan_file(
            db=db,
            file_path=temp_file_path,
            file_name=safe_name,
            user_id=current_user.id,
            use_virustotal=use_virustotal
        )
        
        if not is_safe:
            # El archivo ya fue eliminado por el scanner
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Mover archivo a ubicación permanente
        permanent_file_path = os.path.join(
            settings.PERMANENT_UPLOAD_FOLDER,
            f"user_{current_user.id}",
            safe_name
        )
        os.makedirs(os.path.dirname(permanent_file_path), exist_ok=True)
        shutil.move(temp_file_path, permanent_file_path)
        
        return {
            "message": "Archivo subido y escaneado exitosamente",
            "filename": safe_name,
            "path": permanent_file_path,
            "size": len(content),
            "scan_result": "CLEAN"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Limpiar archivo temporal en caso de error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar archivo: {str(e)}"
        )


@router.post("/scan")
async def scan_existing_file(
    file_path: str = Form(...),
    use_virustotal: bool = Form(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Escanea un archivo existente en el servidor
    """
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    scanner = FileSecurityService()
    is_safe, message, threat_name = scanner.scan_file(
        db=db,
        file_path=file_path,
        file_name=os.path.basename(file_path),
        user_id=current_user.id,
        use_virustotal=use_virustotal
    )
    
    return {
        "is_safe": is_safe,
        "message": message,
        "threat_name": threat_name,
        "scan_result": "CLEAN" if is_safe else "INFECTED"
    }


@router.delete("/temp/{file_name}")
async def delete_temp_file(
    file_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un archivo temporal (limpieza automática)
    """
    safe_name = Path(file_name).name
    temp_file_path = os.path.join(settings.TEMP_UPLOAD_FOLDER, f"{current_user.id}_{safe_name}")
    
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
        return {"message": f"Archivo temporal {file_name} eliminado"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Archivo temporal no encontrado"
    )


@router.get("/scan-history")
def get_scan_history(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el historial de escaneos del usuario actual
    """
    from ..models import MalwareScanLog
    
    logs = db.query(MalwareScanLog).filter(
        MalwareScanLog.user_id == current_user.id
    ).order_by(
        MalwareScanLog.scanned_at.desc()
    ).offset(skip).limit(limit).all()
    
    total = db.query(MalwareScanLog).filter(
        MalwareScanLog.user_id == current_user.id
    ).count()
    
    return {
        "items": logs,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit
    }
