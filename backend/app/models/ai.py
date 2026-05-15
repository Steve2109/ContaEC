"""
Modelos para IA y Machine Learning (Fase 16)
Predicción de ventas, detección de fraude, categorización automática.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base

class PredictionType(str, enum.Enum):
    VENTAS = "ventas"
    FLUJO_CAJA = "flujo_caja"
    INVENTARIO = "inventario"

class FraudAlertType(str, enum.Enum):
    TRANSACCION_SOSPECHOSA = "transaccion_sospechosa"
    PATRON_ANOMALO = "patron_anomalo"
    DUPLICADO = "duplicado"
    MONTO_INUSUAL = "monto_inusual"

class SalesPrediction(Base):
    __tablename__ = "ai_sales_predictions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    tipo = Column(Enum(PredictionType), default=PredictionType.VENTAS)
    periodo_prediccion = Column(String(20))  # diario, semanal, mensual
    fecha_prediccion = Column(DateTime, nullable=False)
    valor_predicho = Column(Float, nullable=False)
    valor_real = Column(Float)  # Se llena cuando pasa el tiempo
    confianza = Column(Float)  # 0-1 porcentaje de confianza del modelo
    caracteristicas = Column(JSON)  # Features usadas para la predicción
    creado_en = Column(DateTime, default=datetime.utcnow)

class FraudAlert(Base):
    __tablename__ = "ai_fraud_alerts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    tipo_alerta = Column(Enum(FraudAlertType), nullable=False)
    descripcion = Column(Text, nullable=False)
    severidad = Column(String(20), default="media")  # baja, media, alta, critica
    entidad_relacionada = Column(String(50))  # factura, transaccion, usuario
    entidad_id = Column(Integer)
    datos_analisis = Column(JSON)
    resuelta = Column(Boolean, default=False)
    resuelta_por = Column(Integer, ForeignKey("users.id"))
    nota_resolucion = Column(Text)
    creado_en = Column(DateTime, default=datetime.utcnow)

class AutoCategory(Base):
    __tablename__ = "ai_auto_categories"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    patron_descripcion = Column(String(255), nullable=False)  # Patrón regex o texto
    cuenta_contable_sugerida = Column(String(20))
    categoria_producto = Column(String(100))
    confianza = Column(Float, default=1.0)
    veces_usado = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

class ChatbotConversation(Base):
    __tablename__ = "ai_chatbot_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mensaje_usuario = Column(Text, nullable=False)
    respuesta_bot = Column(Text, nullable=False)
    contexto = Column(JSON)
    satisfaccion = Column(Integer)  # 1-5 estrellas si el usuario califica
    creado_en = Column(DateTime, default=datetime.utcnow)
