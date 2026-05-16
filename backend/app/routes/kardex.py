"""
Kárdex — movimientos de inventario (entradas/salidas/ajustes).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.dependencies import get_db, get_current_active_user
from app.models.inventario import Producto, MovimientoInventario

router = APIRouter(prefix="/kardex", tags=["Kárdex"])


# ─── Schemas ───

class KardexEntry(BaseModel):
    date: datetime
    type: str  # 'entrada', 'salida', 'ajuste', 'devolucion', 'compra', 'venta'
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

@router.get("/product/{product_id}", response_model=KardexSummary)
async def get_kardex_by_product(
    product_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Obtiene el kárdex completo de un producto."""
    # Verificar producto
    product_result = await db.execute(
        select(Producto).where(
            Producto.id == product_id,
            Producto.user_id == current_user.id
        )
    )
    producto = product_result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Movimientos
    query = select(MovimientoInventario).where(
        MovimientoInventario.producto_id == product_id
    ).order_by(desc(MovimientoInventario.fecha))

    if start_date:
        query = query.where(MovimientoInventario.fecha >= start_date)
    if end_date:
        query = query.where(MovimientoInventario.fecha <= end_date)

    query = query.limit(limit)
    result = await db.execute(query)
    movements = result.scalars().all()

    # Calcular totales
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
        "product_code": producto.codigo,
        "current_stock": producto.stock,
        "total_entries": entries,
        "total_exits": exits,
        "average_cost": round(avg_cost, 4),
        "total_value": round(avg_cost * producto.stock, 2),
        "movements": movement_data,
    }


@router.get("/low-stock")
async def get_low_stock(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Productos con stock bajo (bajo el mínimo)."""
    result = await db.execute(
        select(Producto).where(
            and_(
                Producto.user_id == current_user.id,
                Producto.stock <= Producto.stock_minimo,
                Producto.stock_minimo > 0
            )
        ).order_by(desc(Producto.stock_minimo - Producto.stock))
    )
    productos = result.scalars().all()

    return [
        {
            "id": p.id,
            "code": p.codigo,
            "name": p.nombre,
            "stock": p.stock,
            "min_stock": p.stock_minimo,
            "shortage": p.stock_minimo - p.stock,
            "unit": p.unidad_medida,
            "category": p.categoria,
        }
        for p in productos
    ]
