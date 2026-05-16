"""
API de manejo de archivos con:
- Límite de tamaño configurado (default 10MB)
- Validación de extensiones permitidas
- Escaneo con ClamAV (obligatorio)
- Escaneo con VirusTotal (opcional por usuario)
- Almacenamiento volátil: archivos temporales se eliminan después de procesar
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.security import encrypt_file, decrypt_file
from app.services.file_security_service import FileSecurityService
from app.models.facturacion import User

router = APIRouter(prefix="/files", tags=["Files"])

settings = get_settings()

# Carpeta volátil para uploads temporales
TMP_UPLOAD_DIR = Path("/tmp/contaec_uploads")
TMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Extensiones permitidas
ALLOWED_EXTENSIONS = settings.upload_allowed_extensions_list
MAX_SIZE_BYTES = settings.max_upload_size_bytes


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    scan_vt: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sube un archivo con las siguientes validaciones:
    1. Tamaño máximo configurado en .env (default 10MB).
    2. Extensión permitida.
    3. Escaneo obligatorio con ClamAV.
    4. Escaneo opcional con VirusTotal.
    5. Archivo se guarda en carpeta temporal volátil.
    """

    # ── 1. Validar tamaño leyendo chunks ──
    content = await _read_file_with_limit(file, MAX_SIZE_BYTES)
    if content is None:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo excede el tamaño máximo permitido de {settings.MAX_UPLOAD_SIZE_MB} MB. "
                   f"Reduzca el tamaño o contacte al administrador."
        )

    # Resetear puntero para lecturas posteriores
    await file.seek(0)

    # ── 2. Validar extensión ──
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión '{ext}' no permitida. Extensiones válidas: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # ── 3. Guardar temporalmente ──
    tmp_filename = f"{uuid.uuid4().hex}{ext}"
    tmp_path = TMP_UPLOAD_DIR / tmp_filename
    with open(tmp_path, "wb") as f:
        f.write(content)

    # ── 4. Escaneo ClamAV (obligatorio) ──
    security = FileSecurityService()
    clam_result = await security.scan_with_clamav(str(tmp_path))

    if not clam_result.get("clean", False):
        # Eliminar inmediatamente si hay malware
        _safe_delete(tmp_path)
        # Log del intento (audit trail)
        _log_security_event(db, current_user.id, filename, "CLAMAV_MALWARE", clam_result)
        raise HTTPException(
            status_code=400,
            detail=f"⚠️ El archivo contiene malware o no pasó el escaneo de seguridad. "
                   f"Detalle: {clam_result.get('message', 'Unknown')}. "
                   f"El archivo ha sido rechazado y eliminado."
        )

    # ── 5. Escaneo VirusTotal (opcional, no bloqueante) ──
    vt_result = None
    if scan_vt and settings.VT_API_KEY:
        vt_result = await security.scan_with_virustotal_hash(str(tmp_path))
        # Si VT reporta positivo, marcamos como sospechoso pero no bloqueamos
        # a menos que el usuario haya configurado bloqueo estricto.
        if vt_result and not vt_result.get("clean", True):
            _log_security_event(db, current_user.id, filename, "VT_SOSPECHOSO", vt_result)

    # ── 6. Si todo está limpio, mover a destino final o procesar ──
    # En este punto el backend puede procesar el archivo (ej. importar Excel).
    # Después del procesamiento, se debe eliminar el archivo temporal.
    # Por ahora, retornamos metadata y el path temporal para que el caller lo procese.
    file_stats = tmp_path.stat()

    return {
        "success": True,
        "filename": filename,
        "tmp_path": str(tmp_path),
        "size_bytes": file_stats.st_size,
        "size_human": _human_readable_size(file_stats.st_size),
        "extension": ext,
        "mime_type": file.content_type,
        "clamav": clam_result,
        "virustotal": vt_result,
        "message": "Archivo escaneado exitosamente. Procese el archivo y luego elimínelo del tmp_path.",
    }


@router.post("/process-and-cleanup")
async def process_and_cleanup(
    tmp_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para confirmar que un archivo temporal ya fue procesado
    y puede eliminarse de forma segura del disco.
    """
    path = Path(tmp_path)
    if not path.exists():
        return {"success": False, "message": "Archivo ya no existe o ya fue eliminado."}

    # Seguridad: asegurar que está dentro del directorio volátil permitido
    try:
        path.relative_to(TMP_UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Ruta no permitida para eliminación.")

    _safe_delete(path)
    _log_security_event(db, current_user.id, path.name, "CLEANUP_OK", {"path": str(path)})
    return {"success": True, "message": "Archivo temporal eliminado correctamente."}


@router.post("/encrypt-upload")
async def encrypt_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sube y encripta un archivo sensible (ej. firma electrónica).
    El archivo se encripta con Fernet y se almacena temporalmente.
    """
    content = await _read_file_with_limit(file, MAX_SIZE_BYTES)
    if content is None:
        raise HTTPException(status_code=413, detail="Archivo excede tamaño máximo.")

    ext = Path(file.filename or ".p12").suffix.lower()
    tmp_filename = f"{uuid.uuid4().hex}{ext}.enc"
    tmp_path = TMP_UPLOAD_DIR / tmp_filename

    encrypted = encrypt_file(content)
    with open(tmp_path, "wb") as f:
        f.write(encrypted)

    return {
        "success": True,
        "tmp_path": str(tmp_path),
        "encrypted": True,
        "message": "Archivo encriptado y guardado temporalmente.",
    }


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────

async def _read_file_with_limit(file: UploadFile, max_bytes: int) -> Optional[bytes]:
    """
    Lee el archivo en chunks, abortando si excede max_bytes.
    Retorna None si excede el límite.
    """
    chunks = []
    total = 0
    chunk_size = 8192

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            return None
        chunks.append(chunk)

    return b"".join(chunks)


def _safe_delete(path: Path) -> None:
    """Elimina un archivo de forma segura, ignorando errores."""
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _human_readable_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def _log_security_event(db: Session, user_id: int, filename: str, event_type: str, details: dict):
    """
    Registra un evento de seguridad en la base de datos para auditoría.
    Asume que existe un modelo SecurityLog; si no existe, falla silenciosamente.
    """
    try:
        from app.models.facturacion import SecurityLog
        log = SecurityLog(
            user_id=user_id,
            event_type=event_type,
            filename=filename,
            details=details,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
        # No bloquear el flujo principal por fallo de logging
        pass
