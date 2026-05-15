"""
Schemas para Integraciones (Fase 15)
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class BankStatementCreate(BaseModel):
    company_id: int
    cuenta_bancaria: str
    fecha_transaccion: datetime
    descripcion: str
    tipo: str  # debito, credito
    monto: float
    saldo_despues: Optional[float] = None
    referencia: Optional[str] = None

class EcommerceConnectionCreate(BaseModel):
    company_id: int
    plataforma: str  # shopify, woocommerce, magento, prestashop, opencart
    url_tienda: str
    api_key: str
    api_secret: str
    configuracion: Optional[Dict[str, Any]] = None

class WebhookResponse(BaseModel):
    company_id: int
    origen: str
    evento: str
    payload: Dict[str, Any]
