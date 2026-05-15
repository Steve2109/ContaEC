"""
Rutas para Gestión de Compras y Proveedores - Fase 8
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.core.security import get_current_user, verify_company_access
from app.models.user import User
from app.models.company import Company

router = APIRouter(prefix="/api/purchases", tags=["Compras y Proveedores"])

@router.post("/suppliers")
async def create_supplier(
    supplier_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Crear nuevo proveedor
    """
    from app.models.purchase import Supplier
    
    # Verificar que el RUC no exista ya
    existing = db.query(Supplier).filter(
        Supplier.ruc == supplier_data.get("ruc"),
        Supplier.company_id == company.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El RUC del proveedor ya está registrado"
        )
    
    new_supplier = Supplier(
        company_id=company.id,
        name=supplier_data.get("name"),
        ruc=supplier_data.get("ruc"),
        email=supplier_data.get("email"),
        phone=supplier_data.get("phone"),
        address=supplier_data.get("address"),
        contact_name=supplier_data.get("contact_name"),
        credit_limit=supplier_data.get("credit_limit", 0.0)
    )
    
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    
    return {"message": "Proveedor creado exitosamente", "supplier_id": new_supplier.id}

@router.get("/suppliers")
async def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Listar todos los proveedores de la empresa
    """
    from app.models.purchase import Supplier
    
    suppliers = db.query(Supplier).filter(
        Supplier.company_id == company.id,
        Supplier.is_active == True
    ).order_by(Supplier.name).all()
    
    return {
        "total": len(suppliers),
        "suppliers": [
            {
                "id": s.id,
                "name": s.name,
                "ruc": s.ruc,
                "email": s.email,
                "phone": s.phone,
                "contact_name": s.contact_name,
                "credit_limit": s.credit_limit
            }
            for s in suppliers
        ]
    }

@router.post("/purchase-orders")
async def create_purchase_order(
    order_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Crear orden de compra
    """
    from app.models.purchase import PurchaseOrder, PurchaseOrderItem
    from app.models.warehouse import Warehouse
    
    # Validar almacén destino
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == order_data.get("warehouse_id"),
        Warehouse.company_id == company.id
    ).first()
    
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén no encontrado"
        )
    
    # Generar número secuencial
    last_order = db.query(PurchaseOrder).filter(
        PurchaseOrder.company_id == company.id
    ).order_by(PurchaseOrder.id.desc()).first()
    
    seq_number = 1
    if last_order:
        try:
            last_num = int(last_order.order_number.split("-")[-1])
            seq_number = last_num + 1
        except:
            pass
    
    order_number = f"OC-{company.id}-{seq_number:06d}"
    
    # Crear orden de compra
    new_order = PurchaseOrder(
        company_id=company.id,
        supplier_id=order_data.get("supplier_id"),
        warehouse_id=warehouse.id,
        user_id=current_user.id,
        order_number=order_number,
        issue_date=datetime.utcnow(),
        due_date=order_data.get("due_date"),
        observations=order_data.get("observations")
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    # Agregar items
    items = order_data.get("items", [])
    subtotal = 0.0
    tax_iva = 0.0
    total = 0.0
    
    for item_data in items:
        # Calcular totales por item
        item_subtotal = item_data.get("quantity") * item_data.get("unit_price")
        item_tax = item_subtotal * (item_data.get("tax_rate", 15.0) / 100)
        item_total = item_subtotal + item_tax + item_data.get("ice_value", 0.0)
        
        subtotal += item_subtotal
        tax_iva += item_tax
        total += item_total
        
        order_item = PurchaseOrderItem(
            order_id=new_order.id,
            product_id=item_data.get("product_id"),
            quantity=item_data.get("quantity"),
            unit_price=item_data.get("unit_price"),
            tax_rate=item_data.get("tax_rate", 15.0),
            tax_code=item_data.get("tax_code", "IVA15"),
            ice_value=item_data.get("ice_value", 0.0),
            subtotal=item_subtotal,
            tax_amount=item_tax,
            total=item_total
        )
        db.add(order_item)
    
    # Actualizar totales de la orden
    new_order.subtotal = subtotal
    new_order.tax_iva = tax_iva
    new_order.total = total
    db.commit()
    
    return {
        "message": "Orden de compra creada exitosamente",
        "order_id": new_order.id,
        "order_number": order_number
    }

@router.get("/purchase-orders")
async def list_purchase_orders(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Listar órdenes de compra con filtro opcional por estado
    """
    from app.models.purchase import PurchaseOrder
    
    query = db.query(PurchaseOrder).filter(
        PurchaseOrder.company_id == company.id
    )
    
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)
    
    orders = query.order_by(PurchaseOrder.issue_date.desc()).all()
    
    return {
        "total": len(orders),
        "orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "supplier_id": o.supplier_id,
                "status": o.status,
                "total": o.total,
                "issue_date": o.issue_date.isoformat() if o.issue_date else None,
                "due_date": o.due_date.isoformat() if o.due_date else None
            }
            for o in orders
        ]
    }

@router.get("/accounts-payable")
async def list_accounts_payable(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Listar cuentas por pagar
    """
    from app.models.purchase import AccountsPayable
    
    query = db.query(AccountsPayable).filter(
        AccountsPayable.company_id == company.id
    )
    
    if status_filter:
        query = query.filter(AccountsPayable.status == status_filter)
    
    payables = query.order_by(AccountsPayable.due_date.asc()).all()
    
    return {
        "total": len(payables),
        "payables": [
            {
                "id": p.id,
                "supplier_id": p.supplier_id,
                "invoice_number": p.invoice_number,
                "amount_due": p.amount_due,
                "amount_paid": p.amount_paid,
                "balance": p.balance,
                "due_date": p.due_date.isoformat() if p.due_date else None,
                "status": p.status
            }
            for p in payables
        ]
    }
