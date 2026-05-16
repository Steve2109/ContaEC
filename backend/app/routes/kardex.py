"""
Kárdex — movimientos de inventario (entradas/salidas/ajustes).
Adaptado para SQLAlchemy sincrónico (igual que el resto del backend).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.utils.dependencies import get_current_user
from app.core.dependencies import get_current_empresa
from app.core.database import get_db
from app.models.inventario import Producto, MovimientoInventario

router = APIRouter(prefix="/inventario/kardex", tags=["Kárdex"])


# ─── Schemas ───

class KardexEntry(BaseModel):
    date: datetime
    type: str
    document: Optional[str] = None
    quantity: int
    unit_cost: float
    total_cost: float
    stock_after: int
    reference: Optional[str] = None
    concept: Optional[str] = None


class KardexSummary(BaseModel):
    product_id: int
    product_name: str
    product_code: str
    current_stock: int
    total_entries: int
    total_exits: int
    average_cost: float
    total_value: float
    movements: List[KardexEntry]


# ─── Routes ───

@router.get("/producto/{producto_id}", response_model=KardexSummary)
async def get_kardex_by_product(
    producto_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    empresa = Depends(get_current_empresa)
):
    """Obtiene el kárdex completo de un producto."""
    producto = db.query(Producto).filter(
        and_(Producto.id == producto_id, Producto.empresa_id == empresa.id)
    ).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    query = db.query(MovimientoInventario).filter(
        MovimientoInventario.producto_id == producto_id
    ).order_by(desc(MovimientoInventario.fecha))

    if start_date:
        query = query.filter(MovimientoInventario.fecha >= start_date)
    if end_date:
        query = query.filter(MovimientoInventario.fecha <= end_date)

    movements = query.limit(limit).all()

    entries = sum(1 for m in movements if m.tipo in ('entrada', 'compra', 'devolucion'))
    exits = sum(1 for m in movements if m.tipo in ('salida', 'venta'))
    avg_cost = float(producto.costo_promedio) if producto.costo_promedio else 0.0

    movement_data = []
    for m in movements:
        movement_data.append({
            "date": m.fecha,
            "type": m.tipo,
            "document": m.documento,
            "quantity": m.cantidad,
            "unit_cost": float(m.costo_unitario) if m.costo_unitario else 0.0,
            "total_cost": float(m.costo_total) if m.costo_total else 0.0,
            "stock_after": m.stock_posterior,
            "reference": m.referencia,
            "concept": m.concepto,
        })

    return {
        "product_id": producto.id,
        "product_name": producto.nombre,
        "product_code": producto.codigo_interno or producto.codigo_principal or str(producto.id),
        "current_stock": getattr(producto, 'stock', 0),
        "total_entries": entries,
        "total_exits": exits,
        "average_cost": round(avg_cost, 4),
        "total_value": round(avg_cost * getattr(producto, 'stock', 0), 2),
        "movements": movement_data,
    }


@router.get("/alertas-stock-bajo")
async def get_low_stock(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    empresa = Depends(get_current_empresa)
):
    """Productos con stock bajo (bajo el mínimo)."""
    productos = db.query(Producto).filter(
        and_(
            Producto.empresa_id == empresa.id,
            Producto.stock <= Producto.stock_minimo,
            Producto.stock_minimo > 0
        )
    ).order_by(desc(Producto.stock_minimo - Producto.stock)).all()

    return [
        {
            "id": p.id,
            "code": p.codigo_interno or p.codigo_principal,
            "name": p.nombre,
            "stock": getattr(p, 'stock', 0),
            "min_stock": p.stock_minimo,
            "shortage": p.stock_minimo - getattr(p, 'stock', 0),
            "unit": getattr(p, 'unidad_medida', 'UNID'),
            "category": getattr(p, 'categoria', None),
        }
        for p in productos
    ]


@router.get("/resumen")
async def get_kardex_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    empresa = Depends(get_current_empresa)
):
    """Resumen global de movimientos del inventario."""
    total_products = db.query(Producto).filter(Producto.empresa_id == empresa.id).count()

    low_stock = db.query(Producto).filter(
        and_(
            Producto.empresa_id == empresa.id,
            Producto.stock <= Producto.stock_minimo,
            Producto.stock_minimo > 0
        )
    ).count()

    # Valor total del inventario
    from sqlalchemy import func
    total_value = db.query(func.coalesce(
        func.sum(Producto.costo_promedio * Producto.stock), 0.0
    )).filter(Producto.empresa_id == empresa.id).scalar() or 0.0

    return {
        "total_products": total_products,
        "low_stock_count": low_stock,
        "inventory_value": round(float(total_value), 2),
        "alert": low_stock > 0,
    }
