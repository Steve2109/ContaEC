"""
Rutas API para Facturación Electrónica - SRI Ecuador
ContaEC - Fase 3
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import os

from app.core.database import get_db
from app.models import User, Company as Empresa
from app.models.facturacion import (
    EmpresaConfiguracion, CertificadoDigital, Cliente, ProductoServicio,
    ComprobanteElectronico, ComprobanteDetalle, ComprobanteImpuesto,
    ComprobanteRetencion, GuiaRemision, Proforma, LogSRI,
    TipoComprobanteEnum, EstadoComprobanteEnum, TipoIVAEnum,
    TipoContribuyenteEnum, RegimenTributarioEnum
)
from app.services.facturacion_service import GeneradorClaveAcceso, ConsultaSRI
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


class FacturaCreate(BaseModel):
    cliente_id: Optional[int] = None
    identificacion_cliente: Optional[str] = None
    nombre_cliente: Optional[str] = None
    detalles: List[DetalleComprobanteCreate]
    observaciones: Optional[str] = None
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
    tipo_contribuyente: TipoContribuyenteEnum = TipoContribuyenteEnum.OBLIGADO_CONTABILIDAD
    regimen_tributario: RegimenTributarioEnum = RegimenTributarioEnum.GENERAL
    establecimiento: str = "001"
    punto_emision: str = "001"
    ambiente: str = "pruebas"


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
    certificado_encriptado = encrypt_data(contenido_certificado, clave_encriptacion)
    clave_encriptada = encrypt_data(clave.encode('utf-8'), clave_encriptacion)
    
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
    
    db.add(nuevo_certificado)
    db.commit()
    
    return {"mensaje": "Certificado cargado exitosamente", "certificado_id": nuevo_certificado.id}


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
    config = db.query(EmpresaConfiguracion).filter(
        EmpresaConfiguracion.empresa_id == empresa.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=400, detail="Debe configurar primero la facturación electrónica")
    
    certificado = db.query(CertificadoDigital).filter(
        and_(CertificadoDigital.empresa_config_id == config.id, CertificadoDigital.activo == True)
    ).first()
    
    if not certificado:
        raise HTTPException(status_code=400, detail="No hay certificado digital activo")
    
    # Obtener o crear cliente
    if factura_data.cliente_id:
        cliente = db.query(Cliente).filter(
            and_(Cliente.id == factura_data.cliente_id, Cliente.empresa_id == empresa.id)
        ).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
    else:
        cliente = db.query(Cliente).filter(
            and_(Cliente.empresa_id == empresa.id, Cliente.es_consumidor_final == True)
        ).first()
        
        if not cliente:
            cliente = Cliente(
                empresa_id=empresa.id,
                tipo_identificacion="cedula",
                identificacion="9999999999999",
                razon_social="CONSUMIDOR FINAL",
                es_consumidor_final=True
            )
            db.add(cliente)
            db.commit()
            db.refresh(cliente)
    
    secuencial = factura_data.secuencial_personalizado or str(config.secuencia_factura).zfill(9)
    ambiente_codigo = "1" if config.ambiente == "pruebas" else "2"
    
    clave_acceso = GeneradorClaveAcceso.generar(
        fecha_emision=datetime.utcnow(),
        tipo_comprobante=TipoComprobanteEnum.FACTURA.value,
        ruc=config.ruc,
        ambiente=ambiente_codigo,
        secuencial=secuencial
    )
    
    comprobante = ComprobanteElectronico(
        empresa_id=empresa.id,
        cliente_id=cliente.id,
        tipo_comprobante=TipoComprobanteEnum.FACTURA,
        establecimiento=config.establecimiento,
        punto_emision=config.punto_emision,
        secuencial=secuencial,
        clave_acceso=clave_acceso,
        fecha_emision=datetime.utcnow(),
        estado=EstadoComprobanteEnum.BORRADOR,
        creado_por=usuario.id
    )
    
    db.add(comprobante)
    db.flush()
    
    # Calcular totales
    total_sin_impuestos = 0.0
    total_iva = 0.0
    
    for detalle_data in factura_data.detalles:
        subtotal_linea = detalle_data.cantidad * detalle_data.precio_unitario - detalle_data.descuento
        valor_iva = subtotal_linea * (detalle_data.porcentaje_iva / 100)
        
        detalle = ComprobanteDetalle(
            comprobante_id=comprobante.id,
            producto_id=detalle_data.producto_id,
            codigo_principal=detalle_data.codigo_principal,
            descripcion=detalle_data.descripcion,
            cantidad=detalle_data.cantidad,
            precio_unitario=detalle_data.precio_unitario,
            descuento=detalle_data.descuento,
            tipo_iva=detalle_data.tipo_iva,
            porcentaje_iva=detalle_data.porcentaje_iva,
            valor_iva=valor_iva,
            precio_total_sin_impuestos=subtotal_linea,
            precio_total_con_impuestos=subtotal_linea + valor_iva
        )
        db.add(detalle)
        
        total_sin_impuestos += subtotal_linea
        total_iva += valor_iva
    
    comprobante.subtotal_sin_impuestos = total_sin_impuestos
    comprobante.total_iva = total_iva
    comprobante.importe_total = total_sin_impuestos + total_iva
    
    config.secuencia_factura += 1
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
            {"codigo": info["code"], "nombre": info["name"], "valor": info["value"] * 100 if info["value"] else None}
            for key, info in IVA_CODES.items()
        ],
        "default": DEFAULT_IVA
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
