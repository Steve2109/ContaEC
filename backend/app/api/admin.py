"""
Rutas de administración del sistema
Solo accesibles para usuarios administradores
"""
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..models import User, License, Company, UserConfiguration, MalwareScanLog, SecurityLog, UserRole, LicenseType
from ..schemas import (
    UserResponse, LicenseResponse, LicenseUpdate, LicenseTypeEnum,
    AdminDashboardSummary, SystemHealthStatus, MessageResponse,
    PaginatedResponse
)
from ..services.auth_service import UserService, LicenseService, CompanyService
from ..utils.dependencies import get_current_admin_user, get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["Administración"])


@router.get("/dashboard/summary", response_model=AdminDashboardSummary)
def get_admin_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtiene resumen del dashboard administrativo
    """
    # Total de usuarios
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # Total de empresas
    total_companies = db.query(Company).count()
    
    # Licencias próximas a expirar (30 días)
    licenses_expiring = LicenseService.get_expiring_licenses(db, days_threshold=30)
    
    # Licencias expiradas
    licenses_expired = LicenseService.get_expired_licenses(db)
    
    return AdminDashboardSummary(
        total_users=total_users,
        active_users=active_users,
        total_companies=total_companies,
        licenses_expiring_soon=len(licenses_expiring),
        licenses_expired=len(licenses_expired),
        system_health="healthy"
    )


@router.get("/dashboard/health", response_model=SystemHealthStatus)
def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtiene el estado de salud del sistema
    """
    import os
    import shutil
    
    # Verificar base de datos
    try:
        db.execute(func.now())
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    # Verificar ClamAV
    try:
        clamav_status = "active"
        # TODO: Verificar conexión real con ClamAV
    except:
        clamav_status = "inactive"
    
    # Uso de disco
    total, used, free = shutil.disk_usage("/")
    disk_usage = (used / total) * 100
    
    # Uso de memoria (aproximado)
    try:
        with open('/proc/meminfo', 'r') as mem:
            lines = mem.readlines()
            total_mem = int(lines[0].split()[1])
            available_mem = int(lines[2].split()[1])
            memory_usage = ((total_mem - available_mem) / total_mem) * 100
    except:
        memory_usage = 0.0
    
    # Uso de CPU (aproximado)
    try:
        with open('/proc/loadavg', 'r') as f:
            cpu_usage = float(f.readline().split()[0]) * 100
    except:
        cpu_usage = 0.0
    
    # Determinar estado general
    if db_status == "disconnected" or disk_usage > 90:
        overall_status = "critical"
    elif disk_usage > 70 or memory_usage > 80:
        overall_status = "warning"
    else:
        overall_status = "healthy"
    
    return SystemHealthStatus(
        database=db_status,
        clamav=clamav_status,
        disk_usage=round(disk_usage, 2),
        memory_usage=round(memory_usage, 2),
        cpu_usage=round(cpu_usage, 2),
        status=overall_status
    )


@router.get("/users", response_model=PaginatedResponse)
def get_all_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtiene todos los usuarios del sistema (paginado)
    """
    users = UserService.get_all_users(db, skip=skip, limit=limit)
    total = db.query(User).count()
    
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/licenses", response_model=List[LicenseResponse])
def get_all_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtiene todas las licencias del sistema
    """
    licenses = db.query(License).all()
    
    result = []
    for lic in licenses:
        _, days_remaining = LicenseService.check_license_validity(db, lic.user_id)
        result.append(LicenseResponse(
            id=lic.id,
            user_id=lic.user_id,
            license_type=lic.license_type,
            start_date=lic.start_date,
            end_date=lic.end_date,
            is_active=lic.is_active,
            payment_reference=lic.payment_reference,
            created_at=lic.created_at,
            days_remaining=days_remaining
        ))
    
    return result


@router.put("/licenses/{license_id}", response_model=LicenseResponse)
def update_license(
    license_id: int,
    license_data: LicenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualiza una licencia (extender tiempo, cambiar tipo, etc.)
    Solo accesible para administradores
    """
    updated_license = LicenseService.update_license(db, license_id, license_data)
    
    if not updated_license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licencia no encontrada"
        )
    
    _, days_remaining = LicenseService.check_license_validity(db, updated_license.user_id)
    
    return LicenseResponse(
        id=updated_license.id,
        user_id=updated_license.user_id,
        license_type=updated_license.license_type,
        start_date=updated_license.start_date,
        end_date=updated_license.end_date,
        is_active=updated_license.is_active,
        payment_reference=updated_license.payment_reference,
        created_at=updated_license.created_at,
        days_remaining=days_remaining
    )


@router.post("/users/{user_id}/license")
def create_or_extend_license(
    user_id: int,
    license_type: LicenseTypeEnum = Body(..., embed=True),
    months: int = Body(default=1, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Crea o extiende la licencia de un usuario
    """
    # Verificar que el usuario existe
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Calcular fechas
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=months * 30)
    
    # Mapear tipo de licencia
    license_type_map = {
        LicenseTypeEnum.MENSUAL: LicenseType.MENSUAL,
        LicenseTypeEnum.TRIMESTRAL: LicenseType.TRIMESTRAL,
        LicenseTypeEnum.SEMESTRAL: LicenseType.SEMESTRAL,
        LicenseTypeEnum.ANUAL: LicenseType.ANUAL
    }
    
    license_enum = license_type_map.get(license_type, LicenseType.MENSUAL)
    
    # Crear o actualizar licencia
    license_obj = LicenseService.create_license(
        db=db,
        user_id=user_id,
        license_type=license_enum,
        start_date=start_date,
        end_date=end_date
    )
    
    return MessageResponse(
        message=f"Licencia {license_type.value} creada/extendida hasta {end_date.strftime('%Y-%m-%d')}",
        success=True
    )


@router.get("/security/logs")
def get_security_logs(
    skip: int = 0,
    limit: int = 100,
    suspicious_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtiene logs de seguridad del sistema
    """
    query = db.query(SecurityLog)
    
    if suspicious_only:
        query = query.filter(SecurityLog.is_suspicious == True)
    
    logs = query.order_by(SecurityLog.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()
    
    return PaginatedResponse(
        items=logs,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/malware/logs")
def get_malware_logs(
    skip: int = 0,
    limit: int = 100,
    infected_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtiene logs de escaneo de malware
    """
    query = db.query(MalwareScanLog)
    
    if infected_only:
        query = query.filter(MalwareScanLog.scan_result == "INFECTED")
    
    logs = query.order_by(MalwareScanLog.scanned_at.desc()).offset(skip).limit(limit).all()
    total = query.count()
    
    return PaginatedResponse(
        items=logs,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        pages=(total + limit - 1) // limit
    )


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Desactiva un usuario del sistema
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivarte a ti mismo"
        )
    
    success = UserService.deactivate_user(db, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return MessageResponse(
        message=f"Usuario {user_id} desactivado correctamente",
        success=True
    )
