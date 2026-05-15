"""
Modelos para Integraciones (Fase 15)
Conexión bancaria, e-commerce y webhooks.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database.base_class import Base

class BankStatement(Base):
    __tablename__ = "bank_statements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    cuenta_bancaria = Column(String(50), nullable=False)
    fecha_transaccion = Column(DateTime, nullable=False)
    descripcion = Column(String(255))
    tipo = Column(String(20))  # debito, credito
    monto = Column(Float, nullable=False)
    saldo_despues = Column(Float)
    referencia = Column(String(100))
    conciliado = Column(Boolean, default=False)
    partida_contable_id = Column(Integer, ForeignKey("accounting_entries.id"))
    creado_en = Column(DateTime, default=datetime.utcnow)

class EcommerceConnection(Base):
    __tablename__ = "ecommerce_connections"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    plataforma = Column(String(50), nullable=False)  # shopify, woocommerce, magento, etc.
    url_tienda = Column(String(255))
    api_key = Column(String(255))
    api_secret = Column(String(255))
    activo = Column(Boolean, default=True)
    ultima_sincronizacion = Column(DateTime)
    configuracion = Column(JSON)  # Configuración específica de cada plataforma
    creado_en = Column(DateTime, default=datetime.utcnow)

class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    origen = Column(String(50))  # shopify, woocommerce, banco, etc.
    evento = Column(String(100))
    payload = Column(JSON)
    procesado = Column(Boolean, default=False)
    error = Column(Text)
    creado_en = Column(DateTime, default=datetime.utcnow)
