"""
Dashboard API — estadísticas, actividad reciente, estado de licencia.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.core.dependencies import get_db, get_current_user
from app.models.facturacion import Comprobante, Cliente, Empresa
from app.models.inventario import Producto
from app.models.nomina import Empleado
from app.services.auth_service import AuthService
from app.api.admin import get_system_health

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Devuelve estadísticas globales del usuario para el Dashboard."""
    user_id = current_user.id

    # Facturas
    total_invoices = await db.scalar(
        select(func.count(Comprobante.id)).where(
            Comprobante.user_id == user_id
        )
    ) or 0

    # Productos
    total_products = await db.scalar(
        select(func.count(Producto.id)).where(
            Producto.user_id == user_id
        )
    ) or 0

    # Clientes
    total_clients = await db.scalar(
        select(func.count(Cliente.id)).where(
            Cliente.user_id == user_id
        )
    ) or 0

    # Ingresos (suma de comprobantes autorizados últimos 30 días)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    revenue = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.total), 0.0)).where(
            and_(
                Comprobante.user_id == user_id,
                Comprobante.estado == "autorizado",
                Comprobante.fecha >= thirty_days_ago
            )
        )
    ) or 0.0

    # Empresas
    total_companies = await db.scalar(
        select(func.count(Empresa.id)).where(
            Empresa.user_id == user_id
        )
    ) or 0

    # Empleados
    total_employees = await db.scalar(
        select(func.count(Empleado.id)).where(
            Empleado.user_id == user_id
        )
    ) or 0

    # Comprobantes por estado
    statuses = {}
    for estado in ["borrador", "firmado", "enviado", "autorizado", "rechazado", "anulado"]:
        count = await db.scalar(
            select(func.count(Comprobante.id)).where(
                and_(Comprobante.user_id == user_id, Comprobante.estado == estado)
            )
        ) or 0
        statuses[estado] = count

    # Alerta de stock bajo
    low_stock = await db.scalar(
        select(func.count(Producto.id)).where(
            and_(
                Producto.user_id == user_id,
                Producto.stock <= Producto.stock_minimo,
                Producto.stock_minimo > 0
            )
        )
    ) or 0

    return {
        "invoices": total_invoices,
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
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Actividad reciente: últimos comprobantes, productos, empleados."""
    user_id = current_user.id

    # Últimos comprobantes
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.user_id == user_id
        ).order_by(Comprobante.created_at.desc()).limit(limit)
    )
    comprobantes = result.scalars().all()

    activity = []
    for c in comprobantes:
        activity.append({
            "type": "invoice",
            "id": c.id,
            "title": f"{c.tipo_comprobante} {c.serie}-{c.secuencial}",
            "status": c.estado,
            "amount": float(c.total),
            "date": c.created_at.isoformat() if c.created_at else None,
        })

    return {"activity": activity, "count": len(activity)}


@router.get("/license/status")
async def get_license_status(current_user = Depends(get_current_user)):
    """Estado de la licencia del usuario actual."""
    license_expiry = getattr(current_user, 'license_expiry', None)
    license_type = getattr(current_user, 'license_type', 'trial')

    if not license_expiry:
        return {
            "valid": False,
            "expired": True,
            "days_remaining": 0,
            "license_type": license_type,
            "message": "Sin licencia activa"
        }

    now = datetime.utcnow()
    days = (license_expiry - now).days

    return {
        "valid": days > 0,
        "expired": days <= 0,
        "expiry_date": license_expiry.isoformat(),
        "days_remaining": max(0, days),
        "license_type": license_type,
        "near_expiry": days <= 15,
        "message": f"Licencia vence en {days} días" if days > 0 else "Licencia expirada"
    }
