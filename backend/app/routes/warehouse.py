"""
Rutas para Multi-Almacén y Logística - Fase 9
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.core.security import get_current_user, verify_company_access
from app.models.user import User
from app.models.company import Company

router = APIRouter(prefix="/api/warehouse", tags=["Multi-Almacén y Logística"])

@router.post("/warehouses")
async def create_warehouse(
    warehouse_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Crear nuevo almacén
    """
    from app.models.warehouse import Warehouse
    
    new_warehouse = Warehouse(
        company_id=company.id,
        name=warehouse_data.get("name"),
        code=warehouse_data.get("code"),
        address=warehouse_data.get("address"),
        is_main=warehouse_data.get("is_main", False)
    )
    
    db.add(new_warehouse)
    db.commit()
    db.refresh(new_warehouse)
    
    return {"message": "Almacén creado exitosamente", "warehouse_id": new_warehouse.id}

@router.get("/warehouses")
async def list_warehouses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Listar todos los almacenes de la empresa
    """
    from app.models.warehouse import Warehouse
    
    warehouses = db.query(Warehouse).filter(
        Warehouse.company_id == company.id,
        Warehouse.is_active == True
    ).order_by(Warehouse.is_main.desc(), Warehouse.name).all()
    
    return {
        "total": len(warehouses),
        "warehouses": [
            {
                "id": w.id,
                "name": w.name,
                "code": w.code,
                "address": w.address,
                "is_main": w.is_main
            }
            for w in warehouses
        ]
    }

@router.post("/locations")
async def create_location(
    location_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Crear ubicación física dentro de un almacén (Rack, Estante, Nivel, Bin)
    """
    from app.models.warehouse import WarehouseLocation
    
    new_location = WarehouseLocation(
        warehouse_id=location_data.get("warehouse_id"),
        zone=location_data.get("zone"),
        rack=location_data.get("rack"),
        shelf=location_data.get("shelf"),
        level=location_data.get("level"),
        bin=location_data.get("bin"),
        description=location_data.get("description")
    )
    
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    
    return {"message": "Ubicación creada exitosamente", "location_id": new_location.id}

@router.get("/stock-levels")
async def get_stock_levels(
    warehouse_id: Optional[int] = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Obtener niveles de stock con filtros opcionales
    """
    from app.models.warehouse import StockLevel
    from app.models.product import Product
    
    query = db.query(StockLevel).join(Product).filter(
        StockLevel.company_id == company.id,
        Product.is_active == True
    )
    
    if warehouse_id:
        query = query.filter(StockLevel.warehouse_id == warehouse_id)
    
    if low_stock_only:
        query = query.filter(
            StockLevel.quantity_available <= StockLevel.min_stock,
            StockLevel.min_stock > 0
        )
    
    stock_levels = query.all()
    
    return {
        "total": len(stock_levels),
        "stock_levels": [
            {
                "id": sl.id,
                "product_id": sl.product_id,
                "product_name": sl.product.name if hasattr(sl, 'product') else None,
                "warehouse_id": sl.warehouse_id,
                "quantity_on_hand": sl.quantity_on_hand,
                "quantity_reserved": sl.quantity_reserved,
                "quantity_available": sl.quantity_available,
                "min_stock": sl.min_stock,
                "max_stock": sl.max_stock,
                "reorder_point": sl.reorder_point,
                "status": "BAJO" if sl.quantity_available <= sl.min_stock and sl.min_stock > 0 else "OK"
            }
            for sl in stock_levels
        ]
    }

@router.post("/transfers")
async def create_warehouse_transfer(
    transfer_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Crear transferencia entre almacenes
    """
    from app.models.warehouse import WarehouseTransfer, WarehouseTransferItem
    
    # Generar número de transferencia
    last_transfer = db.query(WarehouseTransfer).filter(
        WarehouseTransfer.company_id == company.id
    ).order_by(WarehouseTransfer.id.desc()).first()
    
    seq_number = 1
    if last_transfer:
        try:
            last_num = int(last_transfer.transfer_number.split("-")[-1])
            seq_number = last_num + 1
        except:
            pass
    
    transfer_number = f"TR-{company.id}-{seq_number:06d}"
    
    # Crear transferencia
    new_transfer = WarehouseTransfer(
        company_id=company.id,
        origin_warehouse_id=transfer_data.get("origin_warehouse_id"),
        destination_warehouse_id=transfer_data.get("destination_warehouse_id"),
        user_id=current_user.id,
        transfer_number=transfer_number,
        notes=transfer_data.get("notes")
    )
    
    db.add(new_transfer)
    db.commit()
    db.refresh(new_transfer)
    
    # Agregar items
    items = transfer_data.get("items", [])
    for item_data in items:
        transfer_item = WarehouseTransferItem(
            transfer_id=new_transfer.id,
            product_id=item_data.get("product_id"),
            quantity=item_data.get("quantity")
        )
        db.add(transfer_item)
    
    db.commit()
    
    return {
        "message": "Transferencia creada exitosamente",
        "transfer_id": new_transfer.id,
        "transfer_number": transfer_number
    }

@router.get("/movements")
async def get_stock_movements(
    product_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Obtener kardex detallado - movimientos de inventario
    """
    from app.models.warehouse import StockMovement
    from datetime import timedelta
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    query = db.query(StockMovement).filter(
        StockMovement.company_id == company.id,
        StockMovement.movement_date >= start_date
    )
    
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)
    
    movements = query.order_by(StockMovement.movement_date.desc()).limit(100).all()
    
    return {
        "period_days": days,
        "total_movements": len(movements),
        "movements": [
            {
                "id": m.id,
                "product_id": m.product_id,
                "warehouse_id": m.warehouse_id,
                "movement_type": m.movement_type,
                "reference_type": m.reference_type,
                "reference_number": m.reference_number,
                "quantity_in": m.quantity_in,
                "quantity_out": m.quantity_out,
                "unit_cost": m.unit_cost,
                "total_value": m.total_value,
                "movement_date": m.movement_date.isoformat() if m.movement_date else None,
                "notes": m.notes
            }
            for m in movements
        ]
    }

@router.get("/locations/{warehouse_id}")
async def get_warehouse_locations(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Obtener todas las ubicaciones de un almacén
    """
    from app.models.warehouse import WarehouseLocation
    
    locations = db.query(WarehouseLocation).filter(
        WarehouseLocation.warehouse_id == warehouse_id,
        WarehouseLocation.is_active == True
    ).all()
    
    return {
        "warehouse_id": warehouse_id,
        "total_locations": len(locations),
        "locations": [
            {
                "id": loc.id,
                "zone": loc.zone,
                "rack": loc.rack,
                "shelf": loc.shelf,
                "level": loc.level,
                "bin": loc.bin,
                "description": loc.description
            }
            for loc in locations
        ]
    }
