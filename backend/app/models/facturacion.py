"""
Modelos para Facturación Electrónica - SRI Ecuador
ContaEC - Fase 3
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class TipoComprobanteEnum(str, enum.Enum):
    FACTURA = "01"
    NOTA_CREDITO = "04"
    NOTA_DEBITO = "05"
    RETENCION = "07"
    GUIA_REMISION = "08"
    PROFORMA = "99"


class EstadoComprobanteEnum(str, enum.Enum):
    BORRADOR = "borrador"
    FIRMADO = "firmado"
    ENVIADO_SRI = "enviado_sri"
    AUTORIZADO = "autorizado"
    RECHAZADO = "rechazado"
    ANULADO = "anulado"


class TipoContribuyenteEnum(str, enum.Enum):
    NO_OBLIGADO_CONTABILIDAD = "01"
    OBLIGADO_CONTABILIDAD = "02"
    RIMPE_EMPRENDEDOR = "03"
    RIMPE_NEGOCIO_POPULAR = "04"
    ESPECIAL = "05"


class RegimenTributarioEnum(str, enum.Enum):
    GENERAL = "general"
    RIMPE_EMPRENDEDOR = "rimpe_emprendedor"
    RIMPE_NEGOCIO_POPULAR = "rimpe_negocio_popular"
    EXENTO = "exento"


class TipoIVAEnum(str, enum.Enum):
    CERO = "0"
    CINCO = "5"
    OCHO = "8"
    DOCE = "12"
    TRECE = "13"
    CATORCE = "14"
    QUINCE = "15"
    NO_OBJETO = "no_objeto"
    EXENTO = "exento"
    DIFERENCIADO = "diferenciado"


class TipoRetencionEnum(str, enum.Enum):
    CERO = "0"
    DIEZ = "10"
    VEINTE = "20"
    TREINTA = "30"
    CINCUENTA = "50"
    SETENTA = "70"
    CIEN = "100"


class EmpresaConfiguracion(Base):
    """Configuración de facturación electrónica por empresa"""
    __tablename__ = "empresa_configuracion"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    
    # Datos del SRI
    ruc = Column(String(13), unique=True, nullable=False, index=True)
    razon_social = Column(String(200), nullable=False)
    nombre_comercial = Column(String(200))
    tipo_contribuyente = Column(SQLEnum(TipoContribuyenteEnum), default=TipoContribuyenteEnum.OBLIGADO_CONTABILIDAD)
    regimen_tributario = Column(SQLEnum(RegimenTributarioEnum), default=RegimenTributarioEnum.GENERAL)
    
    # Configuración de facturación
    establecimiento = Column(String(3), default="001")
    punto_emision = Column(String(3), default="001")
    secuencia_factura = Column(Integer, default=1)
    secuencia_nota_credito = Column(Integer, default=1)
    secuencia_nota_debito = Column(Integer, default=1)
    secuencia_retencion = Column(Integer, default=1)
    secuencia_guia_remision = Column(Integer, default=1)
    
    # Ambiente de operación
    ambiente = Column(String(20), default="produccion")  # pruebas o produccion
    tipo_emision = Column(String(1), default="1")  # 1: normal, 2: contingencia
    
    # Fechas
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="configuracion_sri")
    certificados = relationship("CertificadoDigital", back_populates="empresa_config", uselist=False)


class CertificadoDigital(Base):
    """Certificado digital para firma electrónica"""
    __tablename__ = "certificados_digitales"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_config_id = Column(Integer, ForeignKey("empresa_configuracion.id"), nullable=False)
    
    # Datos encriptados
    certificado_encriptado = Column(Text, nullable=False)  # Contenido del .p12 o .pem
    clave_encriptada = Column(Text, nullable=False)  # Clave del certificado
    ruta_certificado = Column(String(500))  # Ruta segura en servidor
    
    # Información del certificado
    sujeto = Column(String(500))
    emisor = Column(String(500))
    numero_serial = Column(String(100))
    fecha_inicio = Column(DateTime)
    fecha_fin = Column(DateTime)
    dias_restantes = Column(Integer)
    
    # Estado
    activo = Column(Boolean, default=True)
    verificado = Column(Boolean, default=False)
    
    # Auditoría
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación
    empresa_config = relationship("EmpresaConfiguracion", back_populates="certificados")


class Cliente(Base):
    """Clientes para facturación"""
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    
    # Datos personales
    tipo_identificacion = Column(String(20), default="cedula")  # cedula, ruc, pasaporte
    identificacion = Column(String(20), nullable=False)
    razon_social = Column(String(200))
    nombres = Column(String(200))
    apellidos = Column(String(200))
    
    # Datos de contacto
    email = Column(String(100))
    telefono = Column(String(20))
    direccion = Column(String(500))
    
    # Datos SRI
    tipo_contribuyente = Column(SQLEnum(TipoContribuyenteEnum), default=TipoContribuyenteEnum.NO_OBLIGADO_CONTABILIDAD)
    regimen_tributario = Column(SQLEnum(RegimenTributarioEnum))
    
    # Por defecto consumidor final
    es_consumidor_final = Column(Boolean, default=False)
    
    # Estado
    activo = Column(Boolean, default=True)
    
    # Auditoría
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="clientes")
    facturas = relationship("ComprobanteElectronico", back_populates="cliente")
    proformas = relationship("Proforma", back_populates="cliente", cascade="all, delete-orphan")


class ProductoServicio(Base):
    """Productos y servicios para facturación"""
    __tablename__ = "productos_servicios"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    
    # Datos básicos
    codigo_interno = Column(String(50))
    codigo_auxiliar = Column(String(50))
    descripcion = Column(String(500), nullable=False)
    
    # Clasificación SRI
    codigo_principal = Column(String(10))  # Código CPC/NAICE
    codigo_secundario = Column(String(10))
    
    # Precios e impuestos
    precio_unitario = Column(Float, default=0.0)
    tipo_iva_default = Column(SQLEnum(TipoIVAEnum), default=TipoIVAEnum.QUINCE)
    porcentaje_iva = Column(Float, default=15.0)
    tiene_ice = Column(Boolean, default=False)
    porcentaje_ice = Column(Float, default=0.0)
    tarifa_ice_especifica = Column(Float, default=0.0)
    
    # Unidad
    unidad_medida = Column(String(20), default="UNID")  # UNID, KG, LT, M, etc.
    
    # Estado
    activo = Column(Boolean, default=True)
    
    # Auditoría
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="productos_servicios")


class ComprobanteElectronico(Base):
    """Comprobantes electrónicos (facturas, notas, retenciones)"""
    __tablename__ = "comprobantes_electronicos"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    
    # Tipo de comprobante
    tipo_comprobante = Column(SQLEnum(TipoComprobanteEnum), nullable=False)
    
    # Numeración
    establecimiento = Column(String(3), nullable=False)
    punto_emision = Column(String(3), nullable=False)
    secuencial = Column(String(9), nullable=False)
    
    # Clave de acceso SRI (generada automáticamente)
    clave_acceso = Column(String(49), unique=True, index=True)
    digito_verificador = Column(String(1))
    
    # Fecha de emisión
    fecha_emision = Column(DateTime, nullable=False)
    fecha_autorizacion = Column(DateTime)
    
    # Estado
    estado = Column(SQLEnum(EstadoComprobanteEnum), default=EstadoComprobanteEnum.BORRADOR)
    mensaje_sri = Column(Text)  # Mensaje de respuesta del SRI
    numero_autorizacion = Column(String(50))  # Número de autorización SRI
    
    # Totales
    subtotal_sin_impuestos = Column(Float, default=0.0)
    subtotal_iva_0 = Column(Float, default=0.0)
    subtotal_iva_exento = Column(Float, default=0.0)
    subtotal_iva_no_objeto = Column(Float, default=0.0)
    subtotal_iva_diferenciado = Column(Float, default=0.0)
    subtotal_con_iva = Column(Float, default=0.0)
    total_iva = Column(Float, default=0.0)
    total_ice = Column(Float, default=0.0)
    total_descuentos = Column(Float, default=0.0)
    total_otros_cargos = Column(Float, default=0.0)
    importe_total = Column(Float, default=0.0)
    
    # Moneda
    moneda = Column(String(10), default="USD")
    
    # Referencia (para notas de crédito/débito)
    comprobante_referencia = Column(String(50))  # Clave acceso del comprobante original
    tipo_emision_referencia = Column(String(1))
    motivo_modificacion = Column(String(300))
    
    # XML firmado
    xml_generado = Column(Text)  # XML sin firmar
    xml_firmado = Column(Text)  # XML firmado
    xml_respuesta_sri = Column(Text)  # Respuesta del SRI
    
    # PDF generado
    pdf_generado = Column(Text)  # Base64 del PDF o ruta
    
    # Auditoría
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="comprobantes")
    cliente = relationship("Cliente", back_populates="facturas")
    creador = relationship("Usuario")
    detalles = relationship("ComprobanteDetalle", back_populates="comprobante", cascade="all, delete-orphan")
    impuestos = relationship("ComprobanteImpuesto", back_populates="comprobante", cascade="all, delete-orphan")
    retenciones = relationship("ComprobanteRetencion", back_populates="comprobante", cascade="all, delete-orphan")


class ComprobanteDetalle(Base):
    """Detalles de items en el comprobante"""
    __tablename__ = "comprobantes_detalles"
    
    id = Column(Integer, primary_key=True, index=True)
    comprobante_id = Column(Integer, ForeignKey("comprobantes_electronicos.id"), nullable=True)  # Nullable para proformas
    proforma_id = Column(Integer, ForeignKey("proformas.id"), nullable=True)  # Nuevo campo para proformas
    producto_id = Column(Integer, ForeignKey("productos_servicios.id"))
    
    # Datos del item
    codigo_principal = Column(String(10))
    codigo_secundario = Column(String(10))
    descripcion = Column(String(500), nullable=False)
    cantidad = Column(Float, nullable=False, default=1.0)
    unidad_medida = Column(String(20), default="UNID")
    precio_unitario = Column(Float, nullable=False, default=0.0)
    descuento = Column(Float, default=0.0)
    
    # Impuestos
    tipo_iva = Column(SQLEnum(TipoIVAEnum), default=TipoIVAEnum.QUINCE)
    porcentaje_iva = Column(Float, default=15.0)
    valor_iva = Column(Float, default=0.0)
    tiene_ice = Column(Boolean, default=False)
    tipo_ice = Column(String(10))  # Specifico o Porcentual
    porcentaje_ice = Column(Float, default=0.0)
    valor_ice = Column(Float, default=0.0)
    
    # Totales linea
    precio_total_sin_impuestos = Column(Float, default=0.0)
    precio_total_con_impuestos = Column(Float, default=0.0)
    
    # Relaciones
    comprobante = relationship("ComprobanteElectronico", back_populates="detalles")
    proforma = relationship("Proforma", back_populates="detalles")
    producto = relationship("ProductoServicio")


class ComprobanteImpuesto(Base):
    """Impuestos desglosados en el comprobante"""
    __tablename__ = "comprobantes_impuestos"
    
    id = Column(Integer, primary_key=True, index=True)
    comprobante_id = Column(Integer, ForeignKey("comprobantes_electronicos.id"), nullable=False)
    
    # Tipo de impuesto
    codigo = Column(String(10), nullable=False)  # 2: IVA, 3: ICE
    codigo_porcentaje = Column(String(10), nullable=False)  # 0, 5, 8, 12, 13, 14, 15, no_objeto, exento
    
    # Bases y valores
    base_imponible = Column(Float, default=0.0)
    tarifa = Column(Float, default=0.0)
    valor = Column(Float, default=0.0)
    
    # Relación
    comprobante = relationship("ComprobanteElectronico", back_populates="impuestos")


class ComprobanteRetencion(Base):
    """Retenciones aplicadas en el comprobante"""
    __tablename__ = "comprobantes_retenciones"
    
    id = Column(Integer, primary_key=True, index=True)
    comprobante_id = Column(Integer, ForeignKey("comprobantes_electronicos.id"), nullable=False)
    
    # Tipo de retención
    codigo = Column(String(10), nullable=False)  # 1: Renta, 2: IVA
    codigo_retencion = Column(String(10), nullable=False)  # Código específico SRI
    
    # Base y porcentaje
    base_imponible = Column(Float, default=0.0)
    porcentaje_retener = Column(Float, default=0.0)  # 10, 20, 30, 50, 70, 100
    valor_retenido = Column(Float, default=0.0)
    
    # Relación
    comprobante = relationship("ComprobanteElectronico", back_populates="retenciones")


class GuiaRemision(Base):
    """Guías de remisión"""
    __tablename__ = "guias_remision"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    
    # Numeración
    establecimiento = Column(String(3), nullable=False)
    punto_emision = Column(String(3), nullable=False)
    secuencial = Column(String(9), nullable=False)
    
    # Clave de acceso
    clave_acceso = Column(String(49), unique=True)
    
    # Fechas
    fecha_inicio_transporte = Column(DateTime, nullable=False)
    fecha_fin_transporte = Column(DateTime)
    
    # Destinatario
    destinatario_ruc = Column(String(13))
    destinatario_razon_social = Column(String(200))
    destinatario_direccion = Column(String(500))
    
    # Transporte
    motivo_traslado = Column(String(100))
    placa_vehiculo = Column(String(20))
    
    # Estado
    estado = Column(SQLEnum(EstadoComprobanteEnum), default=EstadoComprobanteEnum.BORRADOR)
    
    # XML
    xml_firmado = Column(Text)
    
    # Auditoría
    creado_en = Column(DateTime, default=datetime.utcnow)
    
    # Relación
    empresa = relationship("Empresa")


class Proforma(Base):
    """Proformas (no tributario, solo referencial)"""
    __tablename__ = "proformas"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    
    # Numeración interna
    secuencial = Column(String(9), nullable=False)
    
    # Fechas
    fecha_emision = Column(DateTime, default=datetime.utcnow)
    fecha_validez = Column(DateTime)  # Fecha límite de validez de la proforma
    
    # Totales
    subtotal = Column(Float, default=0.0)
    descuento = Column(Float, default=0.0)
    total_iva = Column(Float, default=0.0)
    total_ice = Column(Float, default=0.0)
    total_con_impuestos = Column(Float, default=0.0)
    
    # Estado
    estado = Column(String(20), default="vigente")  # vigente, aceptada, rechazada, expirada, convertida_factura
    
    # Observaciones
    observaciones = Column(Text)
    condiciones_comerciales = Column(Text)  # Términos de pago, entrega, etc.
    
    # Referencia a factura si se convierte
    comprobante_id = Column(Integer, ForeignKey("comprobantes_electronicos.id"), nullable=True)
    
    # Auditoría
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa")
    cliente = relationship("Cliente", back_populates="proformas")
    detalles = relationship("ComprobanteDetalle", back_populates="proforma", cascade="all, delete-orphan")
    comprobante = relationship("ComprobanteElectronico")


class LogSRI(Base):
    """Logs de interacciones con el SRI"""
    __tablename__ = "logs_sri"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    comprobante_id = Column(Integer, ForeignKey("comprobantes_electronicos.id"))
    
    # Acción
    accion = Column(String(50), nullable=False)  # enviar, consultar, autorizar
    endpoint_sri = Column(String(500))
    
    # Request/Response
    request_xml = Column(Text)
    response_xml = Column(Text)
    
    # Resultado
    exito = Column(Boolean, default=False)
    mensaje_error = Column(Text)
    codigo_error = Column(String(20))
    
    # Timestamp
    creado_en = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa")
    comprobante = relationship("ComprobanteElectronico")
