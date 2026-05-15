"""
Modelos para Gestión de Compras y Proveedores (Fase 8)
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database.base import Base

class OrderStatus(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADA = "enviada"
    RECIBIDA_PARCIAL = "recibida_parcial"
    RECIBIDA_TOTAL = "recibida_total"
    CANCELADA = "cancelada"

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    ruc = Column(String(13), unique=True, nullable=False, index=True)
    email = Column(String(100))
    phone = Column(String(20))
    address = Column(Text)
    contact_name = Column(String(100))
    credit_limit = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    company = relationship("Company", back_populates="suppliers")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False) # Destino
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    order_number = Column(String(50), unique=True, nullable=False) # Secuencial interno
    sri_authorization = Column(String(50), nullable=True) # Para cuando se emite factura del proveedor
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    
    subtotal = Column(Float, default=0.0)
    tax_iva = Column(Float, default=0.0) # Suma de IVAs
    tax_ice = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    
    status = Column(Enum(OrderStatus), default=OrderStatus.BORRADOR)
    observations = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")
    warehouse = relationship("Warehouse", back_populates="purchase_orders")
    company = relationship("Company", back_populates="purchase_orders")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    quantity = Column(Float, nullable=False)
    received_quantity = Column(Float, default=0.0) # Para recepciones parciales
    unit_price = Column(Float, nullable=False)
    
    # Impuestos detallados
    tax_rate = Column(Float, default=15.0) # Porcentaje IVA
    tax_code = Column(String(10), default="IVA15") # Código SRI
    ice_value = Column(Float, default=0.0)
    
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    
    # Relación
    order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")

class AccountsPayable(Base):
    __tablename__ = "accounts_payable"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    
    invoice_number = Column(String(50), nullable=False) # Factura del proveedor
    amount_due = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    balance = Column(Float, nullable=False)
    
    due_date = Column(DateTime, nullable=False)
    payment_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="pendiente") # pendiente, pagado, vencido
    
    created_at = Column(DateTime, default=datetime.utcnow)
