"""
Rutas API para Facturación Electrónica - SRI Ecuador
ContaEC - Fase 3
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import os
import base64

from app.core.database import get_db
from app.models import User, Company as Empresa
from app.models.facturacion import (
    EmpresaConfiguracion, CertificadoDigital, Cliente, ProductoServicio,
    ComprobanteElectronico, ComprobanteDetalle, ComprobanteImpuesto,
    ComprobanteRetencion, GuiaRemision, Proforma, LogSRI,
    TipoComprobanteEnum, EstadoComprobanteEnum, TipoIVAEnum,
    TipoContribuyenteEnum, RegimenTributarioEnum
)
from app.services.facturacion_service import (
    GeneradorClaveAcceso, ConsultaSRI, GeneradorXML, FirmadorXML, ServicioSRI,
    sri_codigo_iva
)
from app.utils.dependencies import get_current_user
from app.core.security import encrypt_sensitive_data as encrypt_data
from app.core.dependencies import get_current_empresa
from app.core.sri_constants import (
    IVA_CODES, DEFAULT_IVA, ICE_CODES, RETENTION_IR_CODES, RETENTION_IVA_CODES,
    CONTRIBUTOR_TYPES, TAX_REGIMES, DOCUMENT_TYPES, DOCUMENT_STATUS, CONSUMIDOR_FINAL
)

router = APIRouter(prefix="/facturacion", tags=["Facturación Electrónica"])


# ==================== SCHEMAS ====================

class ClienteCreate(BaseModel):
    tipo_identificacion: str = "cedula"
    identificacion: str
    razon_social: Optional[str] = None
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    tipo_contribuyente: TipoContribuyenteEnum = TipoContribuyenteEnum.NO_OBLIGADO_CONTABILIDAD
    regimen_tributario: Optional[RegimenTributarioEnum] = None
    es_consumidor_final: bool = False


class ClienteResponse(BaseModel):
    id: int
    identificacion: str
    razon_social: Optional[str]
    email: Optional[str]
    telefono: Optional[str]
    tipo_contribuyente: str
    es_consumidor_final: bool
    
    class Config:
        from_attributes = True


class ProductoCreate(BaseModel):
    codigo_interno: Optional[str] = None
    codigo_auxiliar: Optional[str] = None
    descripcion: str
    codigo_principal: Optional[str] = None
    codigo_secundario: Optional[str] = None
    precio_unitario: float = 0.0
    tipo_iva_default: TipoIVAEnum = TipoIVAEnum.QUINCE
    porcentaje_iva: float = 15.0
    tiene_ice: bool = False
    porcentaje_ice: float = 0.0
    unidad_medida: str = "UNID"


class DetalleComprobanteCreate(BaseModel):
    producto_id: Optional[int] = None
    codigo_principal: str
    descripcion: str
    cantidad: float = 1.0
    unidad_medida: str = "UNID"
    precio_unitario: float
    descuento: float = 0.0
    tipo_iva: TipoIVAEnum = TipoIVAEnum.QUINCE
    porcentaje_iva: float = 15.0
    tiene_ice: bool = False
    porcentaje_ice: float = 0.0
    tipo_ice: Optional[str] = None


class FacturaCreate(BaseModel):
    cliente_id: Optional[int] = None
    identificacion_cliente: Optional[str] = None
    nombre_cliente: Optional[str] = None
    detalles: List[DetalleComprobanteCreate]
    observaciones: Optional[str] = None
    secuencial_personalizado: Optional[str] = None


class ComprobanteElectronicoCreate(BaseModel):
    tipo_comprobante: TipoComprobanteEnum
    cliente_id: Optional[int] = None
    detalles: List[DetalleComprobanteCreate] = []
    retenciones: List[Dict[str, Any]] = []
    comprobante_referencia: Optional[str] = None
    tipo_emision_referencia: Optional[str] = None
    motivo_modificacion: Optional[str] = None
    secuencial_personalizado: Optional[str] = None


class ComprobanteResponse(BaseModel):
    id: int
    tipo_comprobante: str
    establecimiento: str
    punto_emision: str
    secuencial: str
    clave_acceso: str
    estado: str
    fecha_emision: datetime
    importe_total: float
    numero_autorizacion: Optional[str]
    mensaje_sri: Optional[str]
    
    class Config:
        from_attributes = True


class ConfiguracionSRIUpdate(BaseModel):
    ruc: str
    razon_social: str
    nombre_comercial: Optional[str] = None
    direccion_matriz: str = "SIN DIRECCION"
    direccion_establecimiento: str = "SIN DIRECCION"
    contribuyente_especial: Optional[str] = None
    agente_retencion: Optional[str] = None
    tipo_contribuyente: TipoContribuyenteEnum = TipoContribuyenteEnum.OBLIGADO_CONTABILIDAD
    regimen_tributario: RegimenTributarioEnum = RegimenTributarioEnum.GENERAL
    establecimiento: str = "001"
    punto_emision: str = "001"
    ambiente: str = "pruebas"


class GuiaRemisionCreate(BaseModel):
    destinatario_ruc: str
    destinatario_razon_social: str
    destinatario_direccion: str
    motivo_traslado: str = "Venta"
    placa_vehiculo: str = "AAA0000"
    fecha_inicio_transporte: datetime
    fecha_fin_transporte: Optional[datetime] = None
    secuencial_personalizado: Optional[str] = None
    detalles: List[DetalleComprobanteCreate] = []


SECUENCIA_POR_TIPO = {
    TipoComprobanteEnum.FACTURA: "secuencia_factura",
    TipoComprobanteEnum.NOTA_CREDITO: "secuencia_nota_credito",
    TipoComprobanteEnum.NOTA_DEBITO: "secuencia_nota_debito",
    TipoComprobanteEnum.RETENCION: "secuencia_retencion",
    TipoComprobanteEnum.GUIA_REMISION: "secuencia_guia_remision",
}


def _configuracion_sri_activa(db: Session, empresa_id: int) -> EmpresaConfiguracion:
    config = db.query(EmpresaConfiguracion).filter(EmpresaConfiguracion.empresa_id == empresa_id).first()
    if not config:
        raise HTTPException(status_code=400, detail="Debe configurar primero la facturación electrónica")
    return config


def _certificado_activo(db: Session, config_id: int) -> CertificadoDigital:
    certificado = db.query(CertificadoDigital).filter(
        and_(CertificadoDigital.empresa_config_id == config_id, CertificadoDigital.activo == True)
    ).first()
    if not certificado:
        raise HTTPException(status_code=400, detail="No hay certificado digital activo")
    return certificado


def _obtener_cliente(db: Session, empresa_id: int, cliente_id: Optional[int]) -> Cliente:
    if cliente_id:
        cliente = db.query(Cliente).filter(and_(Cliente.id == cliente_id, Cliente.empresa_id == empresa_id)).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return cliente
    consumidor = db.query(Cliente).filter(
        and_(Cliente.empresa_id == empresa_id, Cliente.es_consumidor_final == True)
    ).first()
    if consumidor:
        return consumidor
    consumidor = Cliente(
        empresa_id=empresa_id,
        tipo_identificacion="cedula",
        identificacion="9999999999999",
        razon_social="CONSUMIDOR FINAL",
        es_consumidor_final=True,
    )
    db.add(consumidor)
    db.flush()
    return consumidor


def _siguiente_secuencial(config: EmpresaConfiguracion, tipo: TipoComprobanteEnum, personalizado: Optional[str]) -> str:
    if personalizado:
        return personalizado.zfill(9)
    attr = SECUENCIA_POR_TIPO[tipo]
    return str(getattr(config, attr)).zfill(9)


def _incrementar_secuencia(config: EmpresaConfiguracion, tipo: TipoComprobanteEnum, personalizado: Optional[str]) -> None:
    if personalizado:
        return
    attr = SECUENCIA_POR_TIPO[tipo]
    setattr(config, attr, getattr(config, attr) + 1)


def _agregar_detalles_e_impuestos(db: Session, comprobante: ComprobanteElectronico, detalles_data: List[DetalleComprobanteCreate]) -> None:
    impuestos_agrupados: Dict[tuple[str, str, float], Dict[str, float]] = {}
    total_sin_impuestos = 0.0
    total_iva = 0.0
    total_ice = 0.0
    total_descuentos = 0.0

    for detalle_data in detalles_data:
        subtotal = max((detalle_data.cantidad * detalle_data.precio_unitario) - detalle_data.descuento, 0)
        valor_iva = round(subtotal * (detalle_data.porcentaje_iva / 100), 2)
        valor_ice = round(subtotal * (detalle_data.porcentaje_ice / 100), 2) if detalle_data.tiene_ice else 0.0
        codigo_iva = sri_codigo_iva(detalle_data.tipo_iva, detalle_data.porcentaje_iva)

        detalle = ComprobanteDetalle(
            comprobante_id=comprobante.id,
            producto_id=detalle_data.producto_id,
            codigo_principal=detalle_data.codigo_principal,
            descripcion=detalle_data.descripcion,
            cantidad=detalle_data.cantidad,
            unidad_medida=detalle_data.unidad_medida,
            precio_unitario=detalle_data.precio_unitario,
            descuento=detalle_data.descuento,
            tipo_iva=detalle_data.tipo_iva,
            porcentaje_iva=detalle_data.porcentaje_iva,
            valor_iva=valor_iva,
            tiene_ice=detalle_data.tiene_ice,
            tipo_ice=detalle_data.tipo_ice,
            porcentaje_ice=detalle_data.porcentaje_ice,
            valor_ice=valor_ice,
            precio_total_sin_impuestos=subtotal,
            precio_total_con_impuestos=subtotal + valor_iva + valor_ice,
        )
        db.add(detalle)

        key = ("2", codigo_iva, detalle_data.porcentaje_iva)
        impuestos_agrupados.setdefault(key, {"base": 0.0, "valor": 0.0})
        impuestos_agrupados[key]["base"] += subtotal
        impuestos_agrupados[key]["valor"] += valor_iva
        if valor_ice:
            ice_key = ("3", detalle_data.tipo_ice or "0", detalle_data.porcentaje_ice)
            impuestos_agrupados.setdefault(ice_key, {"base": 0.0, "valor": 0.0})
            impuestos_agrupados[ice_key]["base"] += subtotal
            impuestos_agrupados[ice_key]["valor"] += valor_ice

        total_sin_impuestos += subtotal
        total_iva += valor_iva
        total_ice += valor_ice
        total_descuentos += detalle_data.descuento

    for (codigo, codigo_porcentaje, tarifa), values in impuestos_agrupados.items():
        db.add(ComprobanteImpuesto(
            comprobante_id=comprobante.id,
            codigo=codigo,
            codigo_porcentaje=str(codigo_porcentaje),
            base_imponible=round(values["base"], 2),
            tarifa=tarifa,
            valor=round(values["valor"], 2),
        ))

    comprobante.subtotal_sin_impuestos = round(total_sin_impuestos, 2)
    comprobante.total_iva = round(total_iva, 2)
    comprobante.total_ice = round(total_ice, 2)
    comprobante.total_descuentos = round(total_descuentos, 2)
    comprobante.importe_total = round(total_sin_impuestos + total_iva + total_ice, 2)


def _crear_comprobante_base(
    db: Session,
    empresa: Empresa,
    usuario: User,
    config: EmpresaConfiguracion,
    cliente: Cliente,
    tipo: TipoComprobanteEnum,
    secuencial: str,
    referencia: Optional[str] = None,
    tipo_referencia: Optional[str] = None,
    motivo: Optional[str] = None,
) -> ComprobanteElectronico:
    fecha = datetime.utcnow()
    ambiente_codigo = "2" if config.ambiente == "produccion" else "1"
    clave_acceso = GeneradorClaveAcceso.generar(
        fecha_emision=fecha,
        tipo_comprobante=tipo.value,
        ruc=config.ruc,
        ambiente=ambiente_codigo,
        establecimiento=config.establecimiento,
        punto_emision=config.punto_emision,
        secuencial=secuencial,
        tipo_emision=config.tipo_emision or "1",
    )
    comprobante = ComprobanteElectronico(
        empresa_id=empresa.id,
        cliente_id=cliente.id,
        tipo_comprobante=tipo,
        establecimiento=config.establecimiento,
        punto_emision=config.punto_emision,
        secuencial=secuencial,
        clave_acceso=clave_acceso,
        fecha_emision=fecha,
        estado=EstadoComprobanteEnum.BORRADOR,
        comprobante_referencia=referencia,
        tipo_emision_referencia=tipo_referencia,
        motivo_modificacion=motivo,
        creado_por=usuario.id,
    )
    db.add(comprobante)
    db.flush()
    return comprobante


# ==================== CLIENTES ====================

@router.post("/clientes/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
async def crear_cliente(
    cliente: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear un nuevo cliente"""
    existente = db.query(Cliente).filter(
        and_(Cliente.empresa_id == empresa.id, Cliente.identificacion == cliente.identificacion)
    ).first()
    
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un cliente con esta identificación")
    
    if cliente.es_consumidor_final or cliente.identificacion == "9999999999999":
        cliente.razon_social = "CONSUMIDOR FINAL"
        cliente.tipo_contribuyente = TipoContribuyenteEnum.NO_OBLIGADO_CONTABILIDAD
    
    db_cliente = Cliente(empresa_id=empresa.id, **cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    
    return db_cliente


@router.get("/clientes/", response_model=List[ClienteResponse])
async def listar_clientes(
    skip: int = 0,
    limit: int = 100,
    buscar: Optional[str] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Listar clientes de la empresa"""
    query = db.query(Cliente).filter(Cliente.empresa_id == empresa.id)
    
    if buscar:
        query = query.filter(
            (Cliente.identificacion.contains(buscar)) |
            (Cliente.razon_social.contains(buscar))
        )
    
    return query.offset(skip).limit(limit).all()


@router.get("/clientes/consumidor-final")
async def obtener_consumidor_final(
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Obtener o crear cliente consumidor final por defecto"""
    consumidor = db.query(Cliente).filter(
        and_(Cliente.empresa_id == empresa.id, Cliente.es_consumidor_final == True)
    ).first()
    
    if not consumidor:
        consumidor = Cliente(
            empresa_id=empresa.id,
            tipo_identificacion="cedula",
            identificacion="9999999999999",
            razon_social="CONSUMIDOR FINAL",
            es_consumidor_final=True
        )
        db.add(consumidor)
        db.commit()
        db.refresh(consumidor)
    
    return consumidor


# ==================== PRODUCTOS ====================

@router.post("/productos/", status_code=status.HTTP_201_CREATED)
async def crear_producto(
    producto: ProductoCreate,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear un nuevo producto o servicio"""
    db_producto = ProductoServicio(empresa_id=empresa.id, **producto.model_dump())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto


@router.get("/productos/")
async def listar_productos(
    skip: int = 0,
    limit: int = 100,
    buscar: Optional[str] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Listar productos y servicios"""
    query = db.query(ProductoServicio).filter(ProductoServicio.empresa_id == empresa.id)
    
    if buscar:
        query = query.filter(ProductoServicio.descripcion.contains(buscar))
    
    return query.offset(skip).limit(limit).all()


# ==================== CONFIGURACIÓN SRI ====================

@router.get("/configuracion-sri/")
async def obtener_configuracion_sri(
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Obtener configuración de facturación electrónica"""
    config = db.query(EmpresaConfiguracion).filter(
        EmpresaConfiguracion.empresa_id == empresa.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="No se ha configurado la facturación electrónica")
    
    certificado = db.query(CertificadoDigital).filter(
        and_(CertificadoDigital.empresa_config_id == config.id, CertificadoDigital.activo == True)
    ).first()
    
    return {
        "configuracion": config,
        "certificado": {
            "activo": certificado.activo if certificado else False,
            "sujeto": certificado.sujeto if certificado else None,
            "fecha_fin": certificado.fecha_fin if certificado else None,
            "dias_restantes": certificado.dias_restantes if certificado else None
        } if certificado else None
    }


@router.put("/configuracion-sri/")
async def actualizar_configuracion_sri(
    config_data: ConfiguracionSRIUpdate,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Actualizar configuración de facturación electrónica"""
    if len(config_data.ruc) != 13 or not config_data.ruc.isdigit():
        raise HTTPException(status_code=400, detail="RUC inválido. Debe tener 13 dígitos numéricos")
    
    config = db.query(EmpresaConfiguracion).filter(
        EmpresaConfiguracion.empresa_id == empresa.id
    ).first()
    
    if config:
        for field, value in config_data.model_dump().items():
            setattr(config, field, value)
    else:
        config = EmpresaConfiguracion(empresa_id=empresa.id, **config_data.model_dump())
        db.add(config)
    
    db.commit()
    db.refresh(config)
    return config


@router.post("/configuracion-sri/certificado/")
async def cargar_certificado(
    certificado_file: UploadFile = File(...),
    clave: str = Form(..., description="Clave del certificado"),
    clave_encriptacion: str = Form(..., description="Clave maestra de encriptación"),
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Cargar certificado digital para firma electrónica"""
    config = db.query(EmpresaConfiguracion).filter(
        EmpresaConfiguracion.empresa_id == empresa.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=400, detail="Primero configure los datos de la empresa")
    
    contenido_certificado = await certificado_file.read()
    certificado_encriptado = encrypt_data(base64.b64encode(contenido_certificado).decode("ascii"))
    clave_encriptada = encrypt_data(clave)
    
    certificado_existente = db.query(CertificadoDigital).filter(
        and_(CertificadoDigital.empresa_config_id == config.id, CertificadoDigital.activo == True)
    ).first()
    
    if certificado_existente:
        certificado_existente.activo = False
    
    nuevo_certificado = CertificadoDigital(
        empresa_config_id=config.id,
        certificado_encriptado=certificado_encriptado,
        clave_encriptada=clave_encriptada,
        activo=True,
        verificado=False
    )
    try:
        info_cert = FirmadorXML.extraer_info_certificado(certificado_encriptado, clave_encriptada)
        nuevo_certificado.sujeto = info_cert["sujeto"]
        nuevo_certificado.emisor = info_cert["emisor"]
        nuevo_certificado.numero_serial = info_cert["numero_serial"]
        nuevo_certificado.fecha_inicio = info_cert["fecha_inicio"]
        nuevo_certificado.fecha_fin = info_cert["fecha_fin"]
        nuevo_certificado.dias_restantes = info_cert["dias_restantes"]
        nuevo_certificado.verificado = True
    except Exception:
        nuevo_certificado.verificado = False
    
    db.add(nuevo_certificado)
    db.commit()
    
    return {
        "mensaje": "Certificado cargado exitosamente",
        "certificado_id": nuevo_certificado.id,
        "fecha_fin": nuevo_certificado.fecha_fin,
        "dias_restantes": nuevo_certificado.dias_restantes,
        "verificado": nuevo_certificado.verificado,
    }


@router.get("/configuracion-sri/validar-certificado/")
async def validar_certificado(
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Validar certificado digital y mostrar días restantes"""
    config = db.query(EmpresaConfiguracion).filter(
        EmpresaConfiguracion.empresa_id == empresa.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="No hay configuración SRI")
    
    certificado = db.query(CertificadoDigital).filter(
        and_(CertificadoDigital.empresa_config_id == config.id, CertificadoDigital.activo == True)
    ).first()
    
    if not certificado:
        raise HTTPException(status_code=404, detail="No hay certificado cargado")
    
    if certificado.fecha_fin:
        dias_restantes = (certificado.fecha_fin - datetime.utcnow()).days
        certificado.dias_restantes = dias_restantes
        certificado.verificado = True
        db.commit()
        
        return {
            "vigente": dias_restantes > 0,
            "dias_restantes": dias_restantes,
            "estado": "VIGENTE" if dias_restantes > 0 else "VENCIDO",
            "alerta_pronto_vencimiento": 0 <= dias_restantes < 30
        }
    
    return {"vigente": False, "mensaje": "No se pudo determinar la vigencia"}


# ==================== FACTURAS ====================

@router.post("/facturas/", response_model=ComprobanteResponse)
async def crear_factura(
    factura_data: FacturaCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear una nueva factura electrónica"""
    config = _configuracion_sri_activa(db, empresa.id)
    cliente = _obtener_cliente(db, empresa.id, factura_data.cliente_id)
    secuencial = _siguiente_secuencial(config, TipoComprobanteEnum.FACTURA, factura_data.secuencial_personalizado)
    comprobante = _crear_comprobante_base(
        db, empresa, usuario, config, cliente, TipoComprobanteEnum.FACTURA, secuencial
    )
    _agregar_detalles_e_impuestos(db, comprobante, factura_data.detalles)
    _incrementar_secuencia(config, TipoComprobanteEnum.FACTURA, factura_data.secuencial_personalizado)
    db.flush()
    db.refresh(comprobante)
    comprobante.xml_generado = GeneradorXML.generar(comprobante, config)
    db.commit()
    db.refresh(comprobante)
    
    return comprobante


@router.get("/facturas/")
async def listar_facturas(
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Listar facturas de la empresa"""
    query = db.query(ComprobanteElectronico).filter(
        and_(
            ComprobanteElectronico.empresa_id == empresa.id,
            ComprobanteElectronico.tipo_comprobante == TipoComprobanteEnum.FACTURA
        )
    )
    
    if estado:
        query = query.filter(ComprobanteElectronico.estado == estado)
    
    return query.order_by(ComprobanteElectronico.fecha_emision.desc()).offset(skip).limit(limit).all()


@router.get("/facturas/{comprobante_id}")
async def obtener_factura(
    comprobante_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Obtener detalles de una factura"""
    comprobante = db.query(ComprobanteElectronico).filter(
        and_(
            ComprobanteElectronico.id == comprobante_id,
            ComprobanteElectronico.empresa_id == empresa.id,
            ComprobanteElectronico.tipo_comprobante == TipoComprobanteEnum.FACTURA
        )
    ).first()
    
    if not comprobante:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    return {
        "comprobante": comprobante,
        "detalles": comprobante.detalles,
        "cliente": comprobante.cliente
    }


# ==================== CICLO ELECTRÓNICO SRI ====================

@router.post("/comprobantes/", response_model=ComprobanteResponse, status_code=status.HTTP_201_CREATED)
async def crear_comprobante_electronico(
    data: ComprobanteElectronicoCreate,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear factura, nota de crédito, nota de débito o retención con XML generado."""
    if data.tipo_comprobante == TipoComprobanteEnum.PROFORMA:
        raise HTTPException(status_code=400, detail="Use /facturacion/proformas/ para proformas")
    if data.tipo_comprobante == TipoComprobanteEnum.GUIA_REMISION:
        raise HTTPException(status_code=400, detail="Use /facturacion/guias-remision/ para guías")
    if data.tipo_comprobante in {TipoComprobanteEnum.FACTURA, TipoComprobanteEnum.NOTA_CREDITO, TipoComprobanteEnum.NOTA_DEBITO} and not data.detalles:
        raise HTTPException(status_code=400, detail="El comprobante requiere al menos un detalle")
    if data.tipo_comprobante == TipoComprobanteEnum.RETENCION and not data.retenciones:
        raise HTTPException(status_code=400, detail="La retención requiere al menos un impuesto retenido")

    config = _configuracion_sri_activa(db, empresa.id)
    cliente = _obtener_cliente(db, empresa.id, data.cliente_id)
    secuencial = _siguiente_secuencial(config, data.tipo_comprobante, data.secuencial_personalizado)
    comprobante = _crear_comprobante_base(
        db, empresa, usuario, config, cliente, data.tipo_comprobante, secuencial,
        referencia=data.comprobante_referencia,
        tipo_referencia=data.tipo_emision_referencia,
        motivo=data.motivo_modificacion,
    )

    if data.detalles:
        _agregar_detalles_e_impuestos(db, comprobante, data.detalles)

    for item in data.retenciones:
        base = float(item.get("base_imponible", 0))
        porcentaje = float(item.get("porcentaje_retener", 0))
        valor = round(base * (porcentaje / 100), 2)
        db.add(ComprobanteRetencion(
            comprobante_id=comprobante.id,
            codigo=str(item.get("codigo", "1")),
            codigo_retencion=str(item.get("codigo_retencion", "0")),
            base_imponible=base,
            porcentaje_retener=porcentaje,
            valor_retenido=valor,
        ))
        comprobante.importe_total += valor

    _incrementar_secuencia(config, data.tipo_comprobante, data.secuencial_personalizado)
    db.flush()
    db.refresh(comprobante)
    comprobante.xml_generado = GeneradorXML.generar(comprobante, config)
    db.commit()
    db.refresh(comprobante)
    return comprobante


@router.post("/comprobantes/{comprobante_id}/generar-xml")
async def generar_xml_comprobante(
    comprobante_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Regenera y guarda el XML SRI del comprobante."""
    config = _configuracion_sri_activa(db, empresa.id)
    comprobante = db.query(ComprobanteElectronico).filter(
        and_(ComprobanteElectronico.id == comprobante_id, ComprobanteElectronico.empresa_id == empresa.id)
    ).first()
    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    comprobante.xml_generado = GeneradorXML.generar(comprobante, config)
    db.commit()
    return {"xml": comprobante.xml_generado, "clave_acceso": comprobante.clave_acceso}


@router.post("/comprobantes/{comprobante_id}/firmar")
async def firmar_comprobante(
    comprobante_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Firma el XML del comprobante con el certificado digital activo."""
    config = _configuracion_sri_activa(db, empresa.id)
    certificado = _certificado_activo(db, config.id)
    comprobante = db.query(ComprobanteElectronico).filter(
        and_(ComprobanteElectronico.id == comprobante_id, ComprobanteElectronico.empresa_id == empresa.id)
    ).first()
    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if not comprobante.xml_generado:
        comprobante.xml_generado = GeneradorXML.generar(comprobante, config)
    try:
        comprobante.xml_firmado = FirmadorXML.firmar(
            comprobante.xml_generado,
            certificado.certificado_encriptado,
            certificado.clave_encriptada,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo firmar el XML: {exc}")
    comprobante.estado = EstadoComprobanteEnum.FIRMADO
    db.commit()
    return {"mensaje": "XML firmado", "estado": comprobante.estado, "clave_acceso": comprobante.clave_acceso}


@router.post("/comprobantes/{comprobante_id}/enviar-sri")
async def enviar_comprobante_sri(
    comprobante_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Envía el XML firmado al webservice de recepción del SRI."""
    config = _configuracion_sri_activa(db, empresa.id)
    comprobante = db.query(ComprobanteElectronico).filter(
        and_(ComprobanteElectronico.id == comprobante_id, ComprobanteElectronico.empresa_id == empresa.id)
    ).first()
    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if not comprobante.xml_firmado:
        raise HTTPException(status_code=400, detail="Primero debe firmar el comprobante")

    sri = ServicioSRI(config.ambiente, sandbox=config.ambiente == "pruebas")
    respuesta = await sri.enviar_comprobante(comprobante.xml_firmado)
    comprobante.xml_respuesta_sri = respuesta.get("respuesta")
    comprobante.mensaje_sri = respuesta.get("mensaje") or respuesta.get("estado")
    comprobante.estado = EstadoComprobanteEnum.ENVIADO_SRI if respuesta.get("exito") else EstadoComprobanteEnum.RECHAZADO
    db.add(LogSRI(
        empresa_id=empresa.id,
        comprobante_id=comprobante.id,
        accion="enviar",
        endpoint_sri=sri.URLS[sri.ambiente]["recepcion"],
        request_xml=comprobante.xml_firmado,
        response_xml=respuesta.get("respuesta"),
        exito=bool(respuesta.get("exito")),
        mensaje_error=None if respuesta.get("exito") else respuesta.get("mensaje"),
        codigo_error=respuesta.get("estado"),
    ))
    db.commit()
    return respuesta


@router.post("/comprobantes/{comprobante_id}/consultar-autorizacion")
async def consultar_autorizacion_comprobante(
    comprobante_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Consulta autorización SRI y actualiza estado del comprobante."""
    config = _configuracion_sri_activa(db, empresa.id)
    comprobante = db.query(ComprobanteElectronico).filter(
        and_(ComprobanteElectronico.id == comprobante_id, ComprobanteElectronico.empresa_id == empresa.id)
    ).first()
    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    sri = ServicioSRI(config.ambiente, sandbox=config.ambiente == "pruebas")
    respuesta = await sri.consultar_autorizacion(comprobante.clave_acceso)
    comprobante.xml_respuesta_sri = respuesta.get("raw_xml")
    comprobante.mensaje_sri = respuesta.get("mensaje")
    comprobante.numero_autorizacion = respuesta.get("numero_autorizacion")
    if respuesta.get("fecha_autorizacion"):
        try:
            comprobante.fecha_autorizacion = datetime.fromisoformat(str(respuesta["fecha_autorizacion"]).replace("Z", "+00:00"))
        except ValueError:
            comprobante.fecha_autorizacion = datetime.utcnow()
    comprobante.estado = EstadoComprobanteEnum.AUTORIZADO if respuesta.get("exito") else EstadoComprobanteEnum.RECHAZADO
    db.add(LogSRI(
        empresa_id=empresa.id,
        comprobante_id=comprobante.id,
        accion="consultar_autorizacion",
        endpoint_sri=sri.URLS[sri.ambiente]["autorizacion"],
        request_xml=comprobante.clave_acceso,
        response_xml=respuesta.get("raw_xml"),
        exito=bool(respuesta.get("exito")),
        mensaje_error=None if respuesta.get("exito") else respuesta.get("mensaje"),
        codigo_error=respuesta.get("estado"),
    ))
    db.commit()
    return respuesta


# ==================== GUÍAS DE REMISIÓN ====================

@router.post("/guias-remision/", status_code=status.HTTP_201_CREATED)
async def crear_guia_remision(
    data: GuiaRemisionCreate,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear guía de remisión electrónica con XML generado."""
    config = _configuracion_sri_activa(db, empresa.id)
    secuencial = _siguiente_secuencial(config, TipoComprobanteEnum.GUIA_REMISION, data.secuencial_personalizado)
    fecha = datetime.utcnow()
    ambiente_codigo = "2" if config.ambiente == "produccion" else "1"
    clave_acceso = GeneradorClaveAcceso.generar(
        fecha_emision=fecha,
        tipo_comprobante=TipoComprobanteEnum.GUIA_REMISION.value,
        ruc=config.ruc,
        ambiente=ambiente_codigo,
        establecimiento=config.establecimiento,
        punto_emision=config.punto_emision,
        secuencial=secuencial,
        tipo_emision=config.tipo_emision or "1",
    )
    guia = GuiaRemision(
        empresa_id=empresa.id,
        establecimiento=config.establecimiento,
        punto_emision=config.punto_emision,
        secuencial=secuencial,
        clave_acceso=clave_acceso,
        fecha_inicio_transporte=data.fecha_inicio_transporte,
        fecha_fin_transporte=data.fecha_fin_transporte,
        destinatario_ruc=data.destinatario_ruc,
        destinatario_razon_social=data.destinatario_razon_social,
        destinatario_direccion=data.destinatario_direccion,
        motivo_traslado=data.motivo_traslado,
        placa_vehiculo=data.placa_vehiculo,
        estado=EstadoComprobanteEnum.BORRADOR,
    )
    db.add(guia)
    _incrementar_secuencia(config, TipoComprobanteEnum.GUIA_REMISION, data.secuencial_personalizado)
    db.flush()
    guia.xml_firmado = GeneradorXML.generar_guia_remision(guia, config, data.detalles)
    db.commit()
    db.refresh(guia)
    return guia


@router.post("/guias-remision/{guia_id}/firmar")
async def firmar_guia_remision(
    guia_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Firma la guía de remisión electrónica."""
    config = _configuracion_sri_activa(db, empresa.id)
    certificado = _certificado_activo(db, config.id)
    guia = db.query(GuiaRemision).filter(and_(GuiaRemision.id == guia_id, GuiaRemision.empresa_id == empresa.id)).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guía de remisión no encontrada")
    xml = GeneradorXML.generar_guia_remision(guia, config)
    guia.xml_firmado = FirmadorXML.firmar(xml, certificado.certificado_encriptado, certificado.clave_encriptada)
    guia.estado = EstadoComprobanteEnum.FIRMADO
    db.commit()
    return {"mensaje": "Guía firmada", "clave_acceso": guia.clave_acceso}


# ==================== CONSULTAS SRI ====================

@router.get("/consultar-ruc/{ruc}")
async def consultar_ruc_sri(ruc: str):
    """Consultar información de un RUC en el SRI"""
    resultado = await ConsultaSRI.consultar_ruc(ruc)
    
    if not resultado["valido"]:
        raise HTTPException(status_code=400, detail=resultado.get("error", "RUC inválido"))
    
    return resultado


@router.get("/tipos-iva/")
async def listar_tipos_iva():
    """Listar todos los tipos de IVA disponibles según SRI"""
    return {
        "tipos_iva": [
            {"codigo_sri": info["code"], "codigo_interno": key, "nombre": info["name"], "porcentaje": info["value"] * 100}
            for key, info in IVA_CODES.items()
        ],
        "default": DEFAULT_IVA
    }


@router.get("/tarifas-ice/")
async def listar_tarifas_ice():
    """Listar tarifas ICE configuradas."""
    return {
        "tarifas_ice": [
            {"codigo_sri": info["code"], "codigo_interno": key, "nombre": info["name"], "porcentaje": info["value"] * 100}
            for key, info in ICE_CODES.items()
        ]
    }


@router.get("/tipos-retencion/")
async def listar_tipos_retencion():
    """Listar tipos de retención (IR e IVA)"""
    return {
        "retencion_renta": [
            {"codigo": info["code"], "porcentaje": info["value"] * 100, "descripcion": info["name"]}
            for key, info in RETENTION_IR_CODES.items()
        ],
        "retencion_iva": [
            {"codigo": info["code"], "porcentaje": info["value"] * 100, "descripcion": info["name"]}
            for key, info in RETENTION_IVA_CODES.items()
        ]
    }


@router.get("/tipos-contribuyente/")
async def listar_tipos_contribuyente():
    """Listar tipos de contribuyente según SRI"""
    return {
        "tipos": [
            {"codigo": codigo, "nombre": nombre}
            for codigo, nombre in CONTRIBUTOR_TYPES.items()
        ],
        "consumidor_final": CONSUMIDOR_FINAL
    }


@router.get("/regimenes-tributarios/")
async def listar_regimenes():
    """Listar regímenes tributarios según SRI"""
    return {
        "regimenes": [
            {"codigo": codigo, "nombre": nombre}
            for codigo, nombre in TAX_REGIMES.items()
        ]
    }


@router.get("/catalogos/")
async def listar_catalogos_sri():
    """Catálogos tributarios principales usados por ContaEC."""
    return {
        "iva": IVA_CODES,
        "ice": ICE_CODES,
        "retencion_renta": RETENTION_IR_CODES,
        "retencion_iva": RETENTION_IVA_CODES,
        "tipos_contribuyente": CONTRIBUTOR_TYPES,
        "regimenes": TAX_REGIMES,
        "tipos_comprobante": DOCUMENT_TYPES,
        "estados_comprobante": DOCUMENT_STATUS,
        "consumidor_final": CONSUMIDOR_FINAL,
    }


# ==================== PROFORMAS ====================

@router.post("/proformas/", status_code=status.HTTP_201_CREATED)
async def crear_proforma(
    proforma_data: dict,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa),
    current_user: User = Depends(get_current_user)
):
    """Crear una nueva proforma (no tributario)"""
    from sqlalchemy import func
    
    # Obtener siguiente secuencial
    ultimo_secuencial = db.query(func.max(Proforma.secuencial)).filter(
        Proforma.empresa_id == empresa.id
    ).scalar() or "000000000"
    
    nuevo_secuencial = str(int(ultimo_secuencial) + 1).zfill(9)
    
    # Crear proforma
    proforma = Proforma(
        empresa_id=empresa.id,
        cliente_id=proforma_data.get("cliente_id"),
        secuencial=nuevo_secuencial,
        fecha_validez=proforma_data.get("fecha_validez"),
        subtotal=proforma_data.get("subtotal", 0.0),
        descuento=proforma_data.get("descuento", 0.0),
        total_iva=proforma_data.get("total_iva", 0.0),
        total_ice=proforma_data.get("total_ice", 0.0),
        total_con_impuestos=proforma_data.get("total_con_impuestos", 0.0),
        observaciones=proforma_data.get("observaciones"),
        condiciones_comerciales=proforma_data.get("condiciones_comerciales")
    )
    
    db.add(proforma)
    db.commit()
    db.refresh(proforma)
    
    # Agregar detalles si existen
    detalles_data = proforma_data.get("detalles", [])
    for item in detalles_data:
        detalle = ComprobanteDetalle(
            proforma_id=proforma.id,
            producto_id=item.get("producto_id"),
            codigo_principal=item.get("codigo_principal"),
            descripcion=item.get("descripcion"),
            cantidad=item.get("cantidad", 1.0),
            unidad_medida=item.get("unidad_medida", "UNID"),
            precio_unitario=item.get("precio_unitario", 0.0),
            descuento=item.get("descuento", 0.0),
            tipo_iva=TipoIVAEnum(item.get("tipo_iva", "15")),
            porcentaje_iva=item.get("porcentaje_iva", 15.0),
            valor_iva=item.get("valor_iva", 0.0),
            tiene_ice=item.get("tiene_ice", False),
            precio_total_sin_impuestos=item.get("precio_total_sin_impuestos", 0.0),
            precio_total_con_impuestos=item.get("precio_total_con_impuestos", 0.0)
        )
        db.add(detalle)
    
    db.commit()
    db.refresh(proforma)
    
    return {"proforma": proforma, "mensaje": "Proforma creada exitosamente"}


@router.get("/proformas/")
async def listar_proformas(
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Listar proformas de la empresa"""
    query = db.query(Proforma).filter(Proforma.empresa_id == empresa.id)
    
    if estado:
        query = query.filter(Proforma.estado == estado)
    
    proformas = query.order_by(Proforma.fecha_emision.desc()).all()
    
    return {"proformas": proformas}


@router.get("/proformas/{proforma_id}")
async def obtener_proforma(
    proforma_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Obtener detalles de una proforma"""
    proforma = db.query(Proforma).filter(
        and_(
            Proforma.id == proforma_id,
            Proforma.empresa_id == empresa.id
        )
    ).first()
    
    if not proforma:
        raise HTTPException(status_code=404, detail="Proforma no encontrada")
    
    return {
        "proforma": proforma,
        "detalles": proforma.detalles,
        "cliente": proforma.cliente
    }


@router.put("/proformas/{proforma_id}/convertir-factura")
async def convertir_proforma_a_factura(
    proforma_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa),
    current_user: User = Depends(get_current_user)
):
    """Convertir proforma en factura electrónica"""
    proforma = db.query(Proforma).filter(
        and_(
            Proforma.id == proforma_id,
            Proforma.empresa_id == empresa.id
        )
    ).first()
    
    if not proforma:
        raise HTTPException(status_code=404, detail="Proforma no encontrada")
    
    if proforma.estado != "vigente":
        raise HTTPException(status_code=400, detail="La proforma no está vigente")
    
    # Aquí se llamaría a la lógica de creación de factura
    # Por ahora solo actualizamos el estado
    proforma.estado = "convertida_factura"
    db.commit()
    
    return {"mensaje": "Proforma convertida a factura exitosamente", "proforma": proforma}


@router.delete("/proformas/{proforma_id}")
async def eliminar_proforma(
    proforma_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Eliminar una proforma"""
    proforma = db.query(Proforma).filter(
        and_(
            Proforma.id == proforma_id,
            Proforma.empresa_id == empresa.id
        )
    ).first()
    
    if not proforma:
        raise HTTPException(status_code=404, detail="Proforma no encontrada")
    
    db.delete(proforma)
    db.commit()
    
    return {"mensaje": "Proforma eliminada exitosamente"}
