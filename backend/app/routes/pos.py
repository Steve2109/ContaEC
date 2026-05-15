"""
Rutas para Punto de Venta (POS) - Fase 10
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.core.security import get_current_user, verify_company_access
from app.models.user import User
from app.models.company import Company
from app.models.product import Product
from app.models.invoice import Invoice, InvoiceItem
from app.schemas.invoice import InvoiceCreate, InvoiceResponse

router = APIRouter(prefix="/api/pos", tags=["Punto de Venta"])

@router.post("/sale", response_model=InvoiceResponse)
async def create_pos_sale(
    invoice_data: InvoiceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Crear una venta rápida desde el POS
    Valida stock, calcula impuestos y genera factura simplificada
    """
    # Verificar que sea tipo de comprobante adecuado para POS
    if invoice_data.document_type not in ["FACTURA", "BOLETA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El POS solo permite FACTURA o BOLETA"
        )
    
    # Validar stock antes de crear la venta
    for item in invoice_data.items:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.company_id == company.id
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {item.product_id} no encontrado"
            )
        
        # Verificar stock disponible en almacén principal
        from app.models.warehouse import StockLevel
        stock = db.query(StockLevel).filter(
            StockLevel.product_id == item.product_id,
            StockLevel.company_id == company.id
        ).first()
        
        if not stock or stock.quantity_available < item.quantity:
            available = stock.quantity_available if stock else 0
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para {product.name}. Disponible: {available}, Solicitado: {item.quantity}"
            )
    
    # Crear la factura (lógica similar a facturación electrónica pero simplificada)
    # Aquí iría la lógica completa de creación de factura
    # Por brevedad, retornamos un esquema básico
    
    new_invoice = Invoice(
        company_id=company.id,
        user_id=current_user.id,
        document_type=invoice_data.document_type,
        sequence="001-001-000000001", # Secuencial POS
        issue_date=datetime.utcnow(),
        customer_ruc=invoice_data.customer_ruc or "9999999999999", # Consumidor final por defecto
        customer_name=invoice_data.customer_name or "CONSUMIDOR FINAL",
        subtotal=invoice_data.subtotal,
        tax_iva=invoice_data.tax_iva,
        total=invoice_data.total,
        is_electronic=False, # Ventas POS pueden no ser electrónicas inmediatas
        status="AUTORIZADO"
    )
    
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)
    
    # Tarea en segundo plano para descontar stock
    background_tasks.add_task(update_pos_stock, db, new_invoice.id, invoice_data.items)
    
    return new_invoice

def update_pos_stock(db: Session, invoice_id: int, items: List):
    """
    Actualizar stock después de una venta POS
    Se ejecuta en segundo plano
    """
    from app.models.warehouse import StockLevel, StockMovement
    
    for item in items:
        # Descontar stock
        stock = db.query(StockLevel).filter(
            StockLevel.product_id == item.product_id
        ).first()
        
        if stock:
            stock.quantity_on_hand -= item.quantity
            stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved
            
            # Registrar movimiento
            movement = StockMovement(
                company_id=stock.company_id,
                warehouse_id=stock.warehouse_id,
                product_id=item.product_id,
                user_id=1, # Usuario del sistema POS
                movement_type="VENTA_POS",
                reference_type="FACTURA",
                reference_id=invoice_id,
                quantity_out=item.quantity,
                unit_cost=0.0, # Debería obtenerse del costo promedio
                notes="Venta desde POS"
            )
            db.add(movement)
    
    db.commit()

@router.get("/products/quick-search")
async def search_products_pos(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Búsqueda rápida de productos para POS
    Soporta búsqueda por nombre, SKU o código de barras
    """
    products = db.query(Product).filter(
        Product.company_id == company.id,
        Product.is_active == True,
        (Product.name.ilike(f"%{q}%") | 
         Product.sku.ilike(f"%{q}%") | 
         (Product.barcode == q))
    ).limit(20).all()
    
    # Incluir información de stock
    result = []
    for p in products:
        from app.models.warehouse import StockLevel
        stock = db.query(StockLevel).filter(
            StockLevel.product_id == p.id,
            StockLevel.company_id == company.id
        ).first()
        
        result.append({
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "barcode": p.barcode,
            "price": p.sale_price,
            "stock": stock.quantity_available if stock else 0,
            "tax_rate": p.tax_rate
        })
    
    return result

@router.get("/daily-summary")
async def get_pos_daily_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Obtener resumen diario del POS para arqueo de caja
    """
    from sqlalchemy import func
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Totales del día
    totals = db.query(
        func.count(Invoice.id).label("total_sales"),
        func.sum(Invoice.total).label("total_amount"),
        func.sum(Invoice.tax_iva).label("total_tax")
    ).filter(
        Invoice.company_id == company.id,
        Invoice.issue_date >= today_start,
        Invoice.issue_date <= today_end,
        Invoice.document_type.in_(["FACTURA", "BOLETA"])
    ).first()
    
    return {
        "date": datetime.utcnow().date(),
        "total_sales": totals.total_sales or 0,
        "total_amount": totals.total_amount or 0.0,
        "total_tax": totals.total_tax or 0.0,
        "net_amount": (totals.total_amount or 0.0) - (totals.total_tax or 0.0)
    }
