"""
Modelos para Presupuestos - Fase 12
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    year = Column(Integer, nullable=False, index=True)
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="BORRADOR")  # BORRADOR, APROBADO, CERRADO
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    company = relationship("Company", back_populates="budgets")
    lines = relationship("BudgetLine", back_populates="budget", cascade="all, delete-orphan")

class BudgetLine(Base):
    """Líneas presupuestarias por cuenta contable"""
    __tablename__ = "budget_lines"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(Integer, ForeignKey("budgets.id"), nullable=False)
    
    account_code = Column(String(20), nullable=False, index=True)
    account_name = Column(String(200), nullable=False)
    
    # Montos mensuales (12 meses)
    monthly_amounts = Column(ARRAY(Float), default=[0.0] * 12)
    annual_total = Column(Float, default=0.0)
    
    description = Column(Text, nullable=True)
    
    # Relación
    budget = relationship("Budget", back_populates="lines")
