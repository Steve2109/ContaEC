"""
Rutas para IA y Machine Learning (Fase 16)
Predicción de ventas, detección de fraude, categorización automática.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json

from app.database.session import get_db
from app.models.ai import SalesPrediction, FraudAlert, AutoCategory, ChatbotConversation, PredictionType, FraudAlertType
from app.schemas.ai import PredictionResponse, FraudAlertResponse, AutoCategoryCreate, ChatbotRequest, ChatbotResponse
from app.utils.dependencies import get_current_user, verify_company_access
from app.models.user import User
from app.models.invoice import Invoice

router = APIRouter(prefix="/api/ai", tags=["IA y Machine Learning"])

@router.get("/predictions/sales")
def get_sales_predictions(
    company_id: int,
    periodo: str = "mensual",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener predicciones de ventas.
    En producción, esto usaría un modelo ML entrenado.
    Aquí implementamos una versión simplificada basada en histórico.
    """
    verify_company_access(db, current_user.id, company_id)
    
    # Obtener ventas históricas de los últimos 6 meses
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    invoices = db.query(Invoice).filter(
        Invoice.company_id == company_id,
        Invoice.fecha_emision >= six_months_ago,
        Invoice.estado == "AUTORIZADO"
    ).all()
    
    # Calcular promedio mensual simple (en producción usaría ARIMA, Prophet, etc.)
    if not invoices:
        return {"predicciones": [], "mensaje": "No hay datos históricos suficientes"}
    
    total_ventas = sum(inv.total_sin_impuestos + inv.total_impuestos for inv in invoices)
    meses = 6
    promedio_mensual = total_ventas / meses
    
    # Proyección simple con tendencia del 5%
    proyeccion_next_month = promedio_mensual * 1.05
    
    prediction_data = {
        "periodo": periodo,
        "valor_predicho": proyeccion_next_month,
        "confianza": 0.75,  # Confianza simulada
        "basado_en_meses": meses,
        "promedio_historico": promedio_mensual
    }
    
    # Guardar predicción en BD
    prediction = SalesPrediction(
        company_id=company_id,
        tipo=PredictionType.VENTAS,
        periodo_prediccion=periodo,
        fecha_prediccion=datetime.utcnow() + timedelta(days=30),
        valor_predicho=proyeccion_next_month,
        confianza=0.75,
        caracteristicas={"meses_analisis": meses, "promedio": promedio_mensual}
    )
    db.add(prediction)
    db.commit()
    
    return {"predicciones": [prediction_data], "modelo": "promedio_movil_simple"}

@router.get("/fraud/alerts")
def get_fraud_alerts(
    company_id: int,
    resuelta: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener alertas de fraude detectadas"""
    verify_company_access(db, current_user.id, company_id)
    
    query = db.query(FraudAlert).filter(FraudAlert.company_id == company_id)
    if resuelta is not None:
        query = query.filter(FraudAlert.resuelta == resuelta)
    
    alerts = query.order_by(FraudAlert.creado_en.desc()).all()
    return alerts

@router.post("/fraud/check/{invoice_id}")
def check_invoice_fraud(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analizar factura en busca de patrones sospechosos.
    Implementa reglas básicas de detección de anomalías.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    verify_company_access(db, current_user.id, invoice.company_id)
    
    alertas_detectadas = []
    
    # Regla 1: Monto inusualmente alto (mayor a 3 desviaciones estándar del promedio)
    avg_amount = db.query(
        db.func.avg(Invoice.total_sin_impuestos + Invoice.total_impuestos)
    ).filter(Invoice.company_id == invoice.company_id).scalar() or 0
    
    monto_total = invoice.total_sin_impuestos + invoice.total_impuestos
    if avg_amount > 0 and monto_total > (avg_amount * 3):
        alertas_detectadas.append({
            "tipo": FraudAlertType.MONTO_INUSUAL,
            "descripcion": f"Monto ${monto_total:.2f} excede 3 veces el promedio (${avg_amount:.2f})"
        })
    
    # Regla 2: Factura duplicada (mismo cliente, mismo monto, mismo día)
    duplicates = db.query(Invoice).filter(
        Invoice.company_id == invoice.company_id,
        Invoice.cliente_id == invoice.cliente_id,
        Invoice.fecha_emision == invoice.fecha_emision,
        Invoice.id != invoice.id
    ).all()
    
    for dup in duplicates:
        dup_monto = dup.total_sin_impuestos + dup.total_impuestos
        if abs(dup_monto - monto_total) < 0.01:  # Mismo monto
            alertas_detectadas.append({
                "tipo": FraudAlertType.DUPLICADO,
                "descripcion": f"Posible factura duplicada con ID {dup.id}"
            })
    
    # Crear alertas en BD si se detectaron anomalías
    resultados = []
    for alerta in alertas_detectadas:
        fraud_alert = FraudAlert(
            company_id=invoice.company_id,
            tipo_alerta=alerta["tipo"],
            descripcion=alerta["descripcion"],
            severidad="alta" if alerta["tipo"] == FraudAlertType.DUPLICADO else "media",
            entidad_relacionada="factura",
            entidad_id=invoice.id,
            datos_analisis={"monto": monto_total, "promedio": avg_amount}
        )
        db.add(fraud_alert)
        resultados.append(fraud_alert)
    
    db.commit()
    
    return {
        "factura_id": invoice_id,
        "alertas_encontradas": len(resultados),
        "detalle": [
            {"tipo": a.tipo_alerta.value, "descripcion": a.descripcion, "severidad": a.severidad}
            for a in resultados
        ],
        "estado": "SOSPECHOSO" if resultados else "LIMPIO"
    }

@router.post("/auto-categorize", response_model=List[AutoCategory])
def create_auto_category_rule(
    category_data: AutoCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear regla de categorización automática"""
    verify_company_access(db, current_user.id, category_data.company_id)
    
    rule = AutoCategory(**category_data.dict(), creado_en=datetime.utcnow())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.get("/auto-categorize/suggest")
def suggest_category(
    company_id: int,
    descripcion: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sugerir categoría basada en patrones aprendidos"""
    verify_company_access(db, current_user.id, company_id)
    
    # Buscar reglas que coincidan con la descripción
    rules = db.query(AutoCategory).filter(
        AutoCategory.company_id == company_id,
        AutoCategory.activo == True,
        AutoCategory.patron_descripcion.ilike(f"%{descripcion}%")
    ).order_by(AutoCategory.confianza.desc()).limit(3).all()
    
    if rules:
        return {
            "sugerencia": {
                "cuenta_contable": rules[0].cuenta_contable_sugerida,
                "categoria_producto": rules[0].categoria_producto,
                "confianza": rules[0].confianza
            },
            "reglas_coincidentes": len(rules)
        }
    
    return {"sugerencia": None, "mensaje": "No se encontraron patrones coincidentes"}

@router.post("/chatbot", response_model=ChatbotResponse)
def chatbot_query(
    request: ChatbotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chatbot de soporte contable.
    Implementación básica con respuestas predefinidas.
    En producción integraría con LLM o base de conocimiento.
    """
    mensaje = request.mensaje.lower()
    
    # Respuestas predefinidas basadas en palabras clave
    respuestas = {
        "factura": "Para crear una factura electrónica, ve al módulo de Facturación > Nueva Factura. Asegúrate de tener configurada tu firma digital.",
        "retencion": "Las retenciones se generan automáticamente al crear una factura. Los porcentajes disponibles son: 0%, 10%, 20%, 30%, 50%, 70%, 100%.",
        "iva": "El IVA por defecto es 15%. También manejamos: 0%, 5%, 8%, 12%, 13%, 14%, No objeto, Exento, y IVA diferenciado.",
        "nomina": "El módulo de nómina calcula automáticamente décimos, fondos de reserva, utilidades y genera los archivos para IESS y SRI.",
        "backup": "Los backups se realizan automáticamente a medianoche. Puedes restaurarlos desde el panel de Administración > Respaldo.",
        "licencia": "Tu licencia puede ser mensual, trimestral, semestral o anual. Contacta a info@tymtechnology.shop para renovaciones.",
        "sri": "ContaEC está alineado con las normativas del SRI para facturación electrónica, RDEP, anexos y reportes tributarios.",
        "inventario": "El sistema maneja kardex detallado, múltiples almacenes, transferencias y alertas de stock mínimo.",
    }
    
    respuesta = "No estoy seguro de entender. ¿Podrías reformular tu pregunta? Temas disponibles: factura, retención, IVA, nómina, backup, licencia, SRI, inventario."
    
    for keyword, resp in respuestas.items():
        if keyword in mensaje:
            respuesta = resp
            break
    
    # Guardar conversación
    conversation = ChatbotConversation(
        user_id=current_user.id,
        mensaje_usuario=request.mensaje,
        respuesta_bot=respuesta,
        contexto={"timestamp": datetime.utcnow().isoformat()}
    )
    db.add(conversation)
    db.commit()
    
    return ChatbotResponse(respuesta=respuesta, sugerencias=list(respuestas.keys()))
