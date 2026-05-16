"""
Modelos para Multi-Almacén y Logística (Fase 9)
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False) # Código corto para identificación
    address = Column(Text)
    is_main = Column(Boolean, default=False) # Almacén principal
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    company = relationship("Company", back_populates="warehouses")
    stock_levels = relationship("StockLevel", back_populates="warehouse")
    purchase_orders = relationship("PurchaseOrder", back_populates="warehouse")
    transfer_origins = relationship("WarehouseTransfer", foreign_keys="WarehouseTransfer.origin_warehouse_id", back_populates="origin_warehouse")
    transfer_destinations = relationship("WarehouseTransfer", foreign_keys="WarehouseTransfer.destination_warehouse_id", back_populates="destination_warehouse")

class WarehouseLocation(Base):
    """Ubicaciones físicas dentro del almacén (Rack, Estante, Nivel, Bin)"""
    __tablename__ = "warehouse_locations"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    
    zone = Column(String(50), nullable=True) # Zona del almacén
    rack = Column(String(50), nullable=True) # Rack o estantería
    shelf = Column(String(50), nullable=True) # Estante
    level = Column(String(50), nullable=True) # Nivel
    bin = Column(String(50), nullable=True) # Contenedor específico
    
    description = Column(String(200))
    is_active = Column(Boolean, default=True)
    
    # Relación única por almacén
    __table_args__ = (UniqueConstraint('warehouse_id', 'rack', 'shelf', 'level', 'bin', name='unique_location'),)

    warehouse = relationship("Warehouse", backref="locations")

class StockLevel(Base):
    """Niveles de stock actuales por producto y almacén"""
    __tablename__ = "stock_levels"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("warehouse_locations.id"), nullable=True)
    
    quantity_on_hand = Column(Float, default=0.0) # Cantidad física actual
    quantity_reserved = Column(Float, default=0.0) # Reservado para ventas/pedidos
    quantity_available = Column(Float, default=0.0) # Disponible (on_hand - reserved)
    min_stock = Column(Float, default=0.0) # Stock mínimo para alerta
    max_stock = Column(Float, default=0.0) # Stock máximo sugerido
    reorder_point = Column(Float, default=0.0) # Punto de reorden
    
    last_count_date = Column(DateTime, nullable=True) # Último conteo físico
    last_movement_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    warehouse = relationship("Warehouse", back_populates="stock_levels")
    product = relationship("Producto", back_populates="stock_levels")
    location = relationship("WarehouseLocation", backref="stock_levels")
    company = relationship("Company", back_populates="stock_levels")

class StockMovement(Base):
    """Kardex detallado - Todos los movimientos de inventario"""
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    movement_type = Column(String(50), nullable=False) # COMPRA, VENTA, TRANSFERENCIA, AJUSTE, DEVOLUCION, PRODUCCION
    reference_type = Column(String(50), nullable=True) # FACTURA, ORDEN_COMPRA, ORDEN_VENTA, etc.
    reference_id = Column(Integer, nullable=True) # ID del documento relacionado
    reference_number = Column(String(100), nullable=True) # Número visible del documento
    
    quantity_in = Column(Float, default=0.0) # Entrada positiva
    quantity_out = Column(Float, default=0.0) # Salida negativa
    unit_cost = Column(Float, default=0.0) # Costo unitario en el movimiento
    total_value = Column(Float, default=0.0) # Valor total del movimiento
    
    origin_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True) # Para transferencias
    destination_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True) # Para transferencias
    
    notes = Column(Text, nullable=True)
    movement_date = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    product = relationship("Producto", back_populates="movements")
    user = relationship("User")
    company = relationship("Company")
    origin_warehouse = relationship("Warehouse", foreign_keys=[origin_warehouse_id])
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id])

class WarehouseTransfer(Base):
    """Transferencias entre almacenes"""
    __tablename__ = "warehouse_transfers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    origin_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    destination_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    transfer_number = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="pendiente") # pendiente, en_transito, completada, cancelada
    
    transfer_date = Column(DateTime, default=datetime.utcnow)
    completed_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    origin_warehouse = relationship("Warehouse", foreign_keys=[origin_warehouse_id], back_populates="transfer_origins")
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id], back_populates="transfer_destinations")
    items = relationship("WarehouseTransferItem", back_populates="transfer", cascade="all, delete-orphan")
    company = relationship("Company")

class WarehouseTransferItem(Base):
    __tablename__ = "warehouse_transfer_items"

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(Integer, ForeignKey("warehouse_transfers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    
    quantity = Column(Float, nullable=False)
    quantity_received = Column(Float, default=0.0) # Puede diferir si hay mermas
    
    # Relación
    transfer = relationship("WarehouseTransfer", back_populates="items")
    product = relationship("Producto")
