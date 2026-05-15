"""
Schemas para IA (Fase 16)
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class PredictionResponse(BaseModel):
    periodo: str
    valor_predicho: float
    confianza: float
    basado_en_meses: Optional[int] = None
    promedio_historico: Optional[float] = None

class FraudAlertResponse(BaseModel):
    tipo_alerta: str
    descripcion: str
    severidad: str
    entidad_relacionada: str
    entidad_id: Optional[int] = None
    creado_en: datetime

class AutoCategoryCreate(BaseModel):
    company_id: int
    patron_descripcion: str
    cuenta_contable_sugerida: Optional[str] = None
    categoria_producto: Optional[str] = None
    confianza: Optional[float] = 1.0

class ChatbotRequest(BaseModel):
    mensaje: str

class ChatbotResponse(BaseModel):
    respuesta: str
    sugerencias: List[str]
