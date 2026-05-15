"""
Rutas para CRM (Fase 13)
Gestión de Leads, Oportunidades y Pipeline.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.models.crm import Lead, Opportunity, FollowUp, LeadStatus, OpportunityStage
from app.schemas.crm import LeadCreate, LeadResponse, OpportunityCreate, OpportunityResponse, FollowUpCreate
from app.utils.dependencies import get_current_user, verify_company_access
from app.models.user import User
from app.models.company import Company

router = APIRouter(prefix="/api/crm", tags=["CRM"])

@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    lead_data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear un nuevo lead"""
    company = verify_company_access(db, current_user.id, lead_data.company_id)
    
    lead = Lead(**lead_data.dict(), creado_en=datetime.utcnow())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

@router.get("/leads", response_model=List[LeadResponse])
def get_leads(
    company_id: int,
    estado: Optional[LeadStatus] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener lista de leads con filtros"""
    verify_company_access(db, current_user.id, company_id)
    
    query = db.query(Lead).filter(Lead.company_id == company_id)
    if estado:
        query = query.filter(Lead.estado == estado)
    
    leads = query.offset(skip).limit(limit).all()
    return leads

@router.put("/leads/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    lead_data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar lead existente"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    verify_company_access(db, current_user.id, lead.company_id)
    
    for key, value in lead_data.dict(exclude_unset=True).items():
        setattr(lead, key, value)
    
    lead.actualizado_en = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return lead

@router.post("/opportunities", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    opportunity_data: OpportunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear nueva oportunidad"""
    company = verify_company_access(db, current_user.id, opportunity_data.company_id)
    
    opportunity = Opportunity(**opportunity_data.dict(), creado_en=datetime.utcnow())
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity

@router.get("/opportunities", response_model=List[OpportunityResponse])
def get_opportunities(
    company_id: int,
    etapa: Optional[OpportunityStage] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener pipeline de oportunidades"""
    verify_company_access(db, current_user.id, company_id)
    
    query = db.query(Opportunity).filter(Opportunity.company_id == company_id)
    if etapa:
        query = query.filter(Opportunity.etapa == etapa)
    
    opportunities = query.offset(skip).limit(limit).all()
    return opportunities

@router.post("/followups", status_code=status.HTTP_201_CREATED)
def create_followup(
    followup_data: FollowUpCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Programar seguimiento para lead"""
    lead = db.query(Lead).filter(Lead.id == followup_data.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    verify_company_access(db, current_user.id, lead.company_id)
    
    followup = FollowUp(**followup_data.dict(), creado_en=datetime.utcnow())
    db.add(followup)
    db.commit()
    return {"message": "Seguimiento programado exitosamente"}

@router.get("/pipeline/summary")
def get_pipeline_summary(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resumen del pipeline de ventas"""
    verify_company_access(db, current_user.id, company_id)
    
    total_leads = db.query(Lead).filter(Lead.company_id == company_id).count()
    total_opportunities = db.query(Opportunity).filter(Opportunity.company_id == company_id).count()
    
    # Monto total por etapa
    stages_summary = db.query(
        Opportunity.etapa,
        db.func.sum(Opportunity.monto_esperado).label("monto_total"),
        db.func.count(Opportunity.id).label("cantidad")
    ).filter(Opportunity.company_id == company_id).group_by(Opportunity.etapa).all()
    
    return {
        "total_leads": total_leads,
        "total_opportunities": total_opportunities,
        "por_etapa": [
            {"etapa": s.etapa, "monto_total": float(s.monto_total or 0), "cantidad": s.cantidad}
            for s in stages_summary
        ]
    }
