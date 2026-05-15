"""
Schemas para CRM (Fase 13)
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.crm import LeadStatus, OpportunityStage

class LeadCreate(BaseModel):
    company_id: int
    nombre: str
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    empresa: Optional[str] = None
    cargo: Optional[str] = None
    estado: Optional[LeadStatus] = LeadStatus.NUEVO
    fuente: Optional[str] = None
    valor_estimado: Optional[float] = 0.0
    notas: Optional[str] = None

class LeadResponse(LeadCreate):
    id: int
    creado_en: datetime
    actualizado_en: Optional[datetime] = None

    class Config:
        from_attributes = True

class OpportunityCreate(BaseModel):
    company_id: int
    lead_id: Optional[int] = None
    titulo: str
    etapa: Optional[OpportunityStage] = OpportunityStage.PROSPECCION
    probabilidad: Optional[int] = 10
    monto_esperado: Optional[float] = 0.0
    fecha_cierre_estimada: Optional[datetime] = None
    descripcion: Optional[str] = None

class OpportunityResponse(OpportunityCreate):
    id: int
    creado_en: datetime

    class Config:
        from_attributes = True

class FollowUpCreate(BaseModel):
    lead_id: int
    tipo: str
    descripcion: Optional[str] = None
    fecha_programada: Optional[datetime] = None
