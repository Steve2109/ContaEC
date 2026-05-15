"""
Modelos para CRM (Fase 13)
Gestión de Leads, Oportunidades y Pipeline de Ventas.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database.base_class import Base

class LeadStatus(str, enum.Enum):
    NUEVO = "nuevo"
    CONTACTADO = "contactado"
    CALIFICADO = "calificado"
    NO_INTERESADO = "no_interesado"
    CONVERTIDO = "convertido"

class OpportunityStage(str, enum.Enum):
    PROSPECCION = "prospeccion"
    PROPUESTA = "propuesta"
    NEGOCIACION = "negociacion"
    CIERRE_GANADO = "cierre_ganado"
    CIERRE_PERDIDO = "cierre_perdido"

class Lead(Base):
    __tablename__ = "crm_leads"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100))
    telefono = Column(String(20))
    empresa = Column(String(100))
    cargo = Column(String(50))
    estado = Column(Enum(LeadStatus), default=LeadStatus.NUEVO)
    fuente = Column(String(50))  # Web, Referido, Redes, etc.
    valor_estimado = Column(Float, default=0.0)
    notas = Column(Text)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación para automatización
    seguimientos = relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan")

class Opportunity(Base):
    __tablename__ = "crm_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    lead_id = Column(Integer, ForeignKey("crm_leads.id"))
    titulo = Column(String(150), nullable=False)
    etapa = Column(Enum(OpportunityStage), default=OpportunityStage.PROSPECCION)
    probabilidad = Column(Integer, default=10)  # 0-100%
    monto_esperado = Column(Float, default=0.0)
    fecha_cierre_estimada = Column(DateTime)
    descripcion = Column(Text)
    creado_en = Column(DateTime, default=datetime.utcnow)

class FollowUp(Base):
    __tablename__ = "crm_followups"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=False)
    tipo = Column(String(50))  # Llamada, Email, Reunión
    descripcion = Column(Text)
    fecha_programada = Column(DateTime)
    completado = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="seguimientos")
