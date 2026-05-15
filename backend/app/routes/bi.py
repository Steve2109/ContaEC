"""
Rutas para Business Intelligence y Dashboards - Fase 11
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from datetime import datetime, timedelta
from typing import Optional

from app.database.session import get_db
from app.utils.dependencies import get_current_user, verify_company_access
from app.models.user import User
from app.models.company import Company
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.warehouse import StockLevel

router = APIRouter(prefix="/api/bi", tags=["Business Intelligence"])

@router.get("/dashboard/kpi")
async def get_kpi_dashboard(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Dashboard principal con KPIs en tiempo real
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Ventas totales del período
    sales_total = db.query(func.sum(Invoice.total)).filter(
        Invoice.company_id == company.id,
        Invoice.issue_date >= start_date,
        Invoice.issue_date <= end_date,
        Invoice.status.in_(["AUTORIZADO", "ENVIADO"])
    ).scalar() or 0.0
    
    # Número de ventas
    sales_count = db.query(func.count(Invoice.id)).filter(
        Invoice.company_id == company.id,
        Invoice.issue_date >= start_date,
        Invoice.issue_date <= end_date
    ).scalar() or 0
    
    # Total impuestos (IVA)
    tax_total = db.query(func.sum(Invoice.tax_iva)).filter(
        Invoice.company_id == company.id,
        Invoice.issue_date >= start_date,
        Invoice.issue_date <= end_date
    ).scalar() or 0.0
    
    # Productos con stock bajo
    low_stock_products = db.query(func.count(Product.id)).filter(
        Product.company_id == company.id,
        Product.is_active == True
    ).join(StockLevel).filter(
        StockLevel.quantity_available < StockLevel.min_stock,
        StockLevel.min_stock > 0
    ).scalar() or 0
    
    # Clientes activos en el período
    active_customers = db.query(func.count(func.distinct(Invoice.customer_ruc))).filter(
        Invoice.company_id == company.id,
        Invoice.issue_date >= start_date,
        Invoice.issue_date <= end_date
    ).scalar() or 0
    
    # Ticket promedio
    avg_ticket = sales_total / sales_count if sales_count > 0 else 0.0
    
    return {
        "period_days": days,
        "kpi": {
            "total_sales": round(sales_total, 2),
            "total_transactions": sales_count,
            "avg_ticket": round(avg_ticket, 2),
            "total_tax": round(tax_total, 2),
            "net_sales": round(sales_total - tax_total, 2),
            "low_stock_alerts": low_stock_products,
            "active_customers": active_customers
        },
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/dashboard/sales-trend")
async def get_sales_trend(
    period: str = "month",  # day, week, month, year
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Tendencia de ventas para gráficos
    """
    end_date = datetime.utcnow()
    
    if period == "day":
        start_date = end_date - timedelta(days=30)
        date_trunc = func.date_trunc('day', Invoice.issue_date)
    elif period == "week":
        start_date = end_date - timedelta(weeks=12)
        date_trunc = func.date_trunc('week', Invoice.issue_date)
    elif period == "month":
        start_date = end_date - timedelta(days=365)
        date_trunc = func.date_trunc('month', Invoice.issue_date)
    else:
        start_date = end_date - timedelta(days=365)
        date_trunc = func.date_trunc('month', Invoice.issue_date)
    
    results = db.query(
        date_trunc.label('date'),
        func.sum(Invoice.total).label('total'),
        func.count(Invoice.id).label('count')
    ).filter(
        Invoice.company_id == company.id,
        Invoice.issue_date >= start_date,
        Invoice.issue_date <= end_date,
        Invoice.status.in_(["AUTORIZADO", "ENVIADO"])
    ).group_by(date_trunc).order_by(date_trunc).all()
    
    chart_data = []
    for row in results:
        chart_data.append({
            "date": row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]),
            "total": float(row[1]) if row[1] else 0.0,
            "transactions": row[2] if row[2] else 0
        })
    
    return {
        "period": period,
        "data": chart_data
    }

@router.get("/dashboard/top-products")
async def get_top_products(
    limit: int = 10,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Top productos más vendidos
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    results = db.query(
        Product.name,
        Product.sku,
        func.sum(InvoiceItem.quantity).label('total_sold'),
        func.sum(InvoiceItem.total).label('total_revenue')
    ).join(
        Invoice, Invoice.id == InvoiceItem.invoice_id
    ).filter(
        Invoice.company_id == company.id,
        Invoice.issue_date >= start_date,
        Invoice.issue_date <= end_date,
        Invoice.status.in_(["AUTORIZADO", "ENVIADO"])
    ).group_by(Product.id, Product.name, Product.sku
    ).order_by(func.sum(InvoiceItem.quantity).desc()
    ).limit(limit).all()
    
    return {
        "period_days": days,
        "top_products": [
            {
                "name": row[0],
                "sku": row[1],
                "quantity_sold": int(row[2]) if row[2] else 0,
                "revenue": float(row[3]) if row[3] else 0.0
            }
            for row in results
        ]
    }

@router.get("/dashboard/inventory-status")
async def get_inventory_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Estado del inventario con alertas inteligentes
    """
    # Productos sin stock
    out_of_stock = db.query(Product).join(StockLevel).filter(
        Product.company_id == company.id,
        Product.is_active == True,
        StockLevel.quantity_available <= 0
    ).count()
    
    # Stock bajo
    low_stock = db.query(Product).join(StockLevel).filter(
        Product.company_id == company.id,
        Product.is_active == True,
        StockLevel.quantity_available > 0,
        StockLevel.quantity_available <= StockLevel.min_stock,
        StockLevel.min_stock > 0
    ).count()
    
    # Stock crítico (por debajo del punto de reorden)
    critical_stock = db.query(Product).join(StockLevel).filter(
        Product.company_id == company.id,
        Product.is_active == True,
        StockLevel.quantity_available <= StockLevel.reorder_point,
        StockLevel.reorder_point > 0
    ).count()
    
    # Valor total del inventario
    inventory_value = db.query(
        func.sum(StockLevel.quantity_on_hand * Product.cost_price)
    ).join(Product).filter(
        Product.company_id == company.id
    ).scalar() or 0.0
    
    return {
        "inventory_summary": {
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "critical_stock": critical_stock,
            "total_inventory_value": round(inventory_value, 2)
        },
        "alerts": [
            {
                "type": "CRITICAL",
                "message": f"{out_of_stock} productos sin stock",
                "priority": "HIGH" if out_of_stock > 0 else "LOW"
            },
            {
                "type": "WARNING",
                "message": f"{low_stock} productos con stock bajo",
                "priority": "MEDIUM" if low_stock > 5 else "LOW"
            }
        ]
    }

@router.get("/dashboard/export-powerbi")
async def export_powerbi_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Exportar datos en formato compatible con Power BI
    Retorna estructura JSON optimizada para conexión directa
    """
    # Datos de ventas consolidados
    sales_data = db.query(
        Invoice.id,
        Invoice.document_type,
        Invoice.sequence,
        Invoice.customer_name,
        Issue_date=Invoice.issue_date,
        Invoice.subtotal,
        Invoice.tax_iva,
        Invoice.total,
        Invoice.status
    ).filter(
        Invoice.company_id == company.id
    ).all()
    
    return {
        "metadata": {
            "company_id": company.id,
            "company_name": company.name,
            "export_date": datetime.utcnow().isoformat(),
            "record_count": len(sales_data)
        },
        "tables": {
            "ventas": [
                {
                    "id_venta": row.id,
                    "tipo_documento": row.document_type,
                    "secuencial": row.sequence,
                    "cliente": row.customer_name,
                    "fecha": row.Issue_date.isoformat() if row.Issue_date else None,
                    "subtotal": float(row.subtotal) if row.subtotal else 0.0,
                    "iva": float(row.tax_iva) if row.tax_iva else 0.0,
                    "total": float(row.total) if row.total else 0.0,
                    "estado": row.status
                }
                for row in sales_data
            ]
        }
    }
