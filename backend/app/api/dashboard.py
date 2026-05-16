"""
Dashboard API — estadísticas, actividad reciente, estado de licencia.
Adaptado para SQLAlchemy sincrónico.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, text
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.core.dependencies import get_db_sync, get_current_user_sync
from app.models.facturacion import ComprobanteElectronico, Cliente, EmpresaConfiguracion
from app.models.inventario import Producto
from app.models.nomina import Employee

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Devuelve estadísticas globales del usuario para el Dashboard."""
    user_id = current_user.id

    # Facturas (últimos 30 días)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    total_invoices = db.query(func.count(ComprobanteElectronico.id)).filter(
        ComprobanteElectronico.user_id == user_id
    ).scalar() or 0

    invoices_30d = db.query(func.count(ComprobanteElectronico.id)).filter(
        and_(
            ComprobanteElectronico.user_id == user_id,
            ComprobanteElectronico.created_at >= thirty_days_ago
        )
    ).scalar() or 0

    # Productos
    total_products = db.query(func.count(Producto.id)).filter(
        Producto.user_id == user_id
    ).scalar() or 0

    # Clientes
    total_clients = db.query(func.count(Cliente.id)).filter(
        Cliente.user_id == user_id
    ).scalar() or 0

    # Ingresos (suma de comprobantes autorizados últimos 30 días)
    revenue = db.query(func.coalesce(func.sum(ComprobanteElectronico.importe_total), 0.0)).filter(
        and_(
            ComprobanteElectronico.user_id == user_id,
            ComprobanteElectronico.estado == "autorizado",
            ComprobanteElectronico.fecha_emision >= thirty_days_ago
        )
    ).scalar() or 0.0

    # Empresas
    total_companies = db.query(func.count(EmpresaConfiguracion.id)).filter(
        EmpresaConfiguracion.user_id == user_id
    ).scalar() or 0

    # Empleados
    total_employees = db.query(func.count(Employee.id)).filter(
        Employee.user_id == user_id
    ).scalar() or 0

    # Comprobantes por estado
    statuses = {}
    for estado in ["borrador", "firmado", "enviado", "autorizado", "rechazado", "anulado"]:
        count = db.query(func.count(ComprobanteElectronico.id)).filter(
            and_(ComprobanteElectronico.user_id == user_id, ComprobanteElectronico.estado == estado)
        ).scalar() or 0
        statuses[estado] = count

    # Alerta de stock bajo
    from app.models.inventario import Producto as ProductoModel
    low_stock = db.query(func.count(ProductoModel.id)).filter(
        and_(
            ProductoModel.user_id == user_id,
            ProductoModel.stock_actual <= ProductoModel.stock_minimo,
            ProductoModel.stock_minimo > 0
        )
    ).scalar() or 0

    return {
        "invoices": total_invoices,
        "invoices_30d": invoices_30d,
        "products": total_products,
        "clients": total_clients,
        "companies": total_companies,
        "employees": total_employees,
        "revenue_30d": round(float(revenue), 2),
        "status_breakdown": statuses,
        "low_stock_count": low_stock,
    }


@router.get("/activity")
async def get_recent_activity(
    limit: int = 10,
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Actividad reciente: últimos comprobantes, productos, empleados."""
    user_id = current_user.id

    # Últimos comprobantes
    comprobantes = db.query(ComprobanteElectronico).filter(
        ComprobanteElectronico.user_id == user_id
    ).order_by(ComprobanteElectronico.created_at.desc()).limit(limit).all()

    activity = []
    for c in comprobantes:
        activity.append({
            "type": "invoice",
            "id": c.id,
            "title": f"{c.tipo_comprobante} {c.establecimiento}-{c.punto_emision}-{c.secuencial}",
            "status": c.estado,
            "amount": float(c.importe_total) if c.importe_total else 0.0,
            "date": c.created_at.isoformat() if c.created_at else None,
        })

    return {"activity": activity, "count": len(activity)}


@router.get("/license/status")
async def get_license_status(
    db: Session = Depends(get_db_sync),
    current_user = Depends(get_current_user_sync)
):
    """Estado de la licencia del usuario actual."""
    from app.models import License
    
    license = db.query(License).filter(
        License.user_id == current_user.id
    ).order_by(License.created_at.desc()).first()

    if not license:
        return {
            "valid": False,
            "expired": True,
            "days_remaining": 0,
            "license_type": "trial",
            "message": "Sin licencia activa"
        }

    now = datetime.utcnow()
    days = (license.end_date - now).days if license.end_date else -1

    return {
        "valid": days > 0,
        "expired": days <= 0,
        "expiry_date": license.end_date.isoformat() if license.end_date else None,
        "days_remaining": max(0, days),
        "license_type": license.license_type.value if hasattr(license.license_type, 'value') else str(license.license_type),
        "near_expiry": 0 < days <= 15,
        "message": f"Licencia vence en {days} días" if days > 0 else "Licencia expirada"
    }
