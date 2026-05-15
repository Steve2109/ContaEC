"""
Rutas para Integraciones (Fase 15)
Conciliación bancaria, e-commerce y webhooks.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.models.integrations import BankStatement, EcommerceConnection, WebhookLog
from app.schemas.integrations import BankStatementCreate, EcommerceConnectionCreate, WebhookResponse
from app.utils.dependencies import get_current_user, verify_company_access, encrypt_data
from app.models.user import User

router = APIRouter(prefix="/api/integrations", tags=["Integraciones"])

@router.post("/bank-statements", status_code=status.HTTP_201_CREATED)
def import_bank_statement(
    statement_data: BankStatementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Importar extracto bancario para conciliación"""
    verify_company_access(db, current_user.id, statement_data.company_id)
    
    statement = BankStatement(**statement_data.dict(), creado_en=datetime.utcnow())
    db.add(statement)
    db.commit()
    return {"message": "Transacción bancaria importada exitosamente"}

@router.get("/bank-statements")
def get_bank_statements(
    company_id: int,
    conciliado: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener extractos bancarios para conciliación"""
    verify_company_access(db, current_user.id, company_id)
    
    query = db.query(BankStatement).filter(BankStatement.company_id == company_id)
    if conciliado is not None:
        query = query.filter(BankStatement.conciliado == conciliado)
    
    statements = query.order_by(BankStatement.fecha_transaccion.desc()).offset(skip).limit(limit).all()
    return statements

@router.post("/bank-statements/{statement_id}/reconcile")
def reconcile_transaction(
    statement_id: int,
    partida_contable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Conciliar transacción bancaria con partida contable"""
    statement = db.query(BankStatement).filter(BankStatement.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    
    verify_company_access(db, current_user.id, statement.company_id)
    
    statement.conciliado = True
    statement.partida_contable_id = partida_contable_id
    db.commit()
    
    return {"message": "Transacción conciliada exitosamente"}

@router.post("/ecommerce", status_code=status.HTTP_201_CREATED)
def create_ecommerce_connection(
    connection_data: EcommerceConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear conexión con plataforma e-commerce"""
    verify_company_access(db, current_user.id, connection_data.company_id)
    
    # Encriptar credenciales antes de guardar
    connection_dict = connection_data.dict()
    if connection_dict.get("api_key"):
        connection_dict["api_key"] = encrypt_data(connection_dict["api_key"])
    if connection_dict.get("api_secret"):
        connection_dict["api_secret"] = encrypt_data(connection_dict["api_secret"])
    
    connection = EcommerceConnection(**connection_dict, creado_en=datetime.utcnow())
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection

@router.get("/ecommerce")
def get_ecommerce_connections(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener conexiones e-commerce configuradas"""
    verify_company_access(db, current_user.id, company_id)
    
    connections = db.query(EcommerceConnection).filter(EcommerceConnection.company_id == company_id).all()
    
    # No devolver las keys encriptadas en la respuesta
    result = []
    for conn in connections:
        conn_dict = {
            "id": conn.id,
            "company_id": conn.company_id,
            "plataforma": conn.plataforma,
            "url_tienda": conn.url_tienda,
            "activo": conn.activo,
            "ultima_sincronizacion": conn.ultima_sincronizacion,
            "creado_en": conn.creado_en
        }
        result.append(conn_dict)
    
    return result

@router.post("/webhooks/log")
def log_webhook(
    webhook_data: WebhookResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registrar webhook recibido para procesamiento asíncrono"""
    verify_company_access(db, current_user.id, webhook_data.company_id)
    
    log = WebhookLog(
        company_id=webhook_data.company_id,
        origen=webhook_data.origen,
        evento=webhook_data.evento,
        payload=webhook_data.payload,
        creado_en=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return {"message": "Webhook registrado para procesamiento"}

@router.get("/webhooks/pending")
def get_pending_webhooks(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener webhooks pendientes de procesamiento"""
    verify_company_access(db, current_user.id, company_id)
    
    webhooks = db.query(WebhookLog).filter(
        WebhookLog.company_id == company_id,
        WebhookLog.procesado == False
    ).all()
    
    return webhooks
