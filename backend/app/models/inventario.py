"""
Modelos para Inventario y Kardex - Fase 4
ContaEC
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.models.facturacion import TipoIVAEnum


class TipoMovimientoEnum(str, enum.Enum):
    """Tipos de movimiento de inventario"""
    ENTRADA_COMPRA = "entrada_compra"
    ENTRADA_DEVOLUCION = "entrada_devolucion"
    ENTRADA_AJUSTE_POSITIVO = "entrada_ajuste_positivo"
    SALIDA_VENTA = "salida_venta"
    SALIDA_DEVOLUCION = "salida_devolucion"
    SALIDA_AJUSTE_NEGATIVO = "salida_ajuste_negativo"
    SALIDA_MERMAS = "salida_mermas"
    TRANSFERENCIA_ENTRADA = "transferencia_entrada"
    TRANSFERENCIA_SALIDA = "transferencia_salida"


class UnidadMedidaEnum(str, enum.Enum):
    """Unidades de medida"""
    UNIDAD = "UNID"
    KILOGRAMO = "KG"
    LIBRA = "LB"
    LITRO = "LT"
    GALON = "GL"
    METRO = "M"
    CENTIMETRO = "CM"
    CAJA = "CAJ"
    FUNDO = "FUN"
    SACO = "SAC"
    OTRO = "OTRO"


class CategoriaProducto(Base):
    """Categorías de productos"""
    __tablename__ = "categorias_productos"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    codigo_categoria = Column(String(20))
    
    # Jerarquía
    padre_id = Column(Integer, ForeignKey("categorias_productos.id"))
    
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="categorias_inventario")
    productos = relationship("Producto", back_populates="categoria")
    padre = relationship("CategoriaProducto", remote_side=[id], backref="hijos")


class Producto(Base):
    """Productos del inventario - Ampliado desde ProductosServicio"""
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias_productos.id"))
    
    # Identificación
    codigo_interno = Column(String(50), unique=True, index=True)
    codigo_barras = Column(String(50), index=True)
    codigo_auxiliar = Column(String(50))
    sku = Column(String(50))
    
    # Información básica
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    descripcion_corta = Column(String(300))
    
    # Clasificación SRI (heredado de facturación)
    codigo_principal_sri = Column(String(10))
    codigo_secundario_sri = Column(String(10))
    
    # Precios
    costo_promedio = Column(Numeric(12, 4), default=0.0)
    costo_ultimo = Column(Numeric(12, 4), default=0.0)
    precio_venta_base = Column(Numeric(12, 2), default=0.0)
    precio_venta_minimo = Column(Numeric(12, 2), default=0.0)
    precio_venta_maximo = Column(Numeric(12, 2), default=0.0)
    
    # Impuestos
    tipo_iva = Column(SQLEnum(TipoIVAEnum), default=TipoIVAEnum.QUINCE)
    porcentaje_iva = Column(Float, default=15.0)
    tiene_ice = Column(Boolean, default=False)
    porcentaje_ice = Column(Float, default=0.0)
    
    # Unidad y medidas
    unidad_medida = Column(SQLEnum(UnidadMedidaEnum), default=UnidadMedidaEnum.UNIDAD)
    factor_conversion = Column(Float, default=1.0)
    peso_neto = Column(Float, default=0.0)
    peso_bruto = Column(Float, default=0.0)
    
    # Control de stock
    stock_minimo = Column(Float, default=0.0)
    stock_maximo = Column(Float, default=999999.0)
    punto_reorden = Column(Float, default=0.0)
    controla_lote = Column(Boolean, default=False)
    controla_serial = Column(Boolean, default=False)
    controla_fecha_vencimiento = Column(Boolean, default=False)
    
    # Estado
    activo = Column(Boolean, default=True)
    es_servicio = Column(Boolean, default=False)
    permite_venta_negativa = Column(Boolean, default=False)
    
    # Imágenes y archivos
    ruta_imagen = Column(String(500))
    archivo_ficha_tecnica = Column(String(500))
    
    # Auditoría
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="productos_inventario")
    categoria = relationship("CategoriaProducto", back_populates="productos")
    stocks = relationship("StockProducto", back_populates="producto", cascade="all, delete-orphan")
    movimientos = relationship("MovimientoInventario", back_populates="producto", cascade="all, delete-orphan")
    lotes = relationship("LoteProducto", back_populates="producto", cascade="all, delete-orphan")


class Almacen(Base):
    """Almacenes o bodegas"""
    __tablename__ = "almacenes"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(20), unique=True)
    direccion = Column(String(500))
    telefono = Column(String(20))
    responsable = Column(String(100))
    email = Column(String(100))
    
    # Configuración
    es_principal = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    
    # Auditoría
    creado_en = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="almacenes")
    stocks = relationship("StockProducto", back_populates="almacen")
    ubicaciones = relationship("UbicacionAlmacen", back_populates="almacen", cascade="all, delete-orphan")


class UbicacionAlmacen(Base):
    """Ubicaciones físicas dentro de un almacén (rack, estante, nivel)"""
    __tablename__ = "ubicaciones_almacen"
    
    id = Column(Integer, primary_key=True, index=True)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    
    codigo = Column(String(20), nullable=False)  # Ej: A-01-B-02-C-03
    descripcion = Column(String(200))
    zona = Column(String(50))  # Zona del almacén
    pasillo = Column(String(50))
    rack = Column(String(50))
    estante = Column(String(50))
    nivel = Column(String(50))
    
    capacidad_maxima = Column(Float)
    volumen_maximo = Column(Float)
    
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    almacen = relationship("Almacen", back_populates="ubicaciones")
    stocks = relationship("StockProducto", back_populates="ubicacion")


class StockProducto(Base):
    """Stock actual de productos por almacén y ubicación"""
    __tablename__ = "stock_productos"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    ubicacion_id = Column(Integer, ForeignKey("ubicaciones_almacen.id"))
    
    # Cantidades
    cantidad_disponible = Column(Numeric(14, 4), default=0.0)
    cantidad_reservada = Column(Numeric(14, 4), default=0.0)
    cantidad_transito = Column(Numeric(14, 4), default=0.0)
    cantidad_total = Column(Numeric(14, 4), default=0.0)
    
    # Valorización
    costo_promedio = Column(Numeric(12, 4), default=0.0)
    valor_total = Column(Numeric(14, 2), default=0.0)
    
    # Última actualización
    ultima_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índices únicos
    __table_args__ = (
        # Un producto solo puede tener un stock por almacén/ubicación
        {'sqlite_autoincrement': True}
    )
    
    # Relaciones
    producto = relationship("Producto", back_populates="stocks")
    almacen = relationship("Almacen", back_populates="stocks")
    ubicacion = relationship("UbicacionAlmacen", back_populates="stocks")


class MovimientoInventario(Base):
    """Kardex - Movimientos de inventario"""
    __tablename__ = "movimientos_inventario"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    ubicacion_id = Column(Integer, ForeignKey("ubicaciones_almacen.id"))
    
    # Tipo de movimiento
    tipo_movimiento = Column(SQLEnum(TipoMovimientoEnum), nullable=False)
    
    # Cantidades
    cantidad_entrada = Column(Numeric(14, 4), default=0.0)
    cantidad_salida = Column(Numeric(14, 4), default=0.0)
    cantidad_anterior = Column(Numeric(14, 4), default=0.0)
    cantidad_nueva = Column(Numeric(14, 4), default=0.0)
    
    # Valores
    costo_unitario = Column(Numeric(12, 4), default=0.0)
    costo_total = Column(Numeric(14, 2), default=0.0)
    
    # Referencias externas
    documento_referencia_tipo = Column(String(50))  # factura, orden_compra, transferencia
    documento_referencia_id = Column(Integer)
    documento_referencia_numero = Column(String(50))
    
    # Tercero relacionado
    tercero_tipo = Column(String(20))  # proveedor, cliente, empleado
    tercero_id = Column(Integer)
    tercero_nombre = Column(String(200))
    
    # Lote y serial
    lote_id = Column(Integer, ForeignKey("lotes_productos.id"))
    numero_serial = Column(String(100))
    fecha_vencimiento = Column(DateTime)
    
    # Observaciones
    observaciones = Column(Text)
    
    # Auditoría
    fecha_movimiento = Column(DateTime, default=datetime.utcnow, nullable=False)
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa")
    producto = relationship("Producto", back_populates="movimientos")
    almacen = relationship("Almacen")
    ubicacion = relationship("UbicacionAlmacen")
    creador = relationship("Usuario")
    lote = relationship("LoteProducto")


class LoteProducto(Base):
    """Lotes de productos con trazabilidad"""
    __tablename__ = "lotes_productos"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    
    codigo_lote = Column(String(50), nullable=False)
    fecha_produccion = Column(DateTime)
    fecha_vencimiento = Column(DateTime)
    fecha_recepcion = Column(DateTime, default=datetime.utcnow)
    
    cantidad_inicial = Column(Numeric(14, 4), default=0.0)
    cantidad_actual = Column(Numeric(14, 4), default=0.0)
    
    costo_unitario = Column(Numeric(12, 4), default=0.0)
    
    estado = Column(String(20), default="activo")  # activo, vencido, agotado
    
    creado_en = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    empresa = relationship("Empresa")
    producto = relationship("Producto", back_populates="lotes")
    movimientos = relationship("MovimientoInventario", back_populates="lote")


class AjusteInventario(Base):
    """Ajustes de inventario"""
    __tablename__ = "ajustes_inventario"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    
    numero_ajuste = Column(String(20), unique=True)
    fecha_ajuste = Column(DateTime, default=datetime.utcnow)
    
    motivo = Column(String(300), nullable=False)
    observaciones = Column(Text)
    
    estado = Column(String(20), default="borrador")  # borrador, aprobado, aplicado
    
    valor_total_ajuste = Column(Numeric(14, 2), default=0.0)
    
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    aprobado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en = Column(DateTime, default=datetime.utcnow)
    aprobado_en = Column(DateTime)
    
    # Relación con items del ajuste
    items = relationship("AjusteInventarioItem", back_populates="ajuste", cascade="all, delete-orphan")
    
    # Relaciones
    empresa = relationship("Empresa")
    almacen = relationship("Almacen")
    creador = relationship("Usuario", foreign_keys=[creado_por])
    aprobador = relationship("Usuario", foreign_keys=[aprobado_por])


class AjusteInventarioItem(Base):
    """Items de un ajuste de inventario"""
    __tablename__ = "ajustes_inventario_items"
    
    id = Column(Integer, primary_key=True, index=True)
    ajuste_id = Column(Integer, ForeignKey("ajustes_inventario.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    ubicacion_id = Column(Integer, ForeignKey("ubicaciones_almacen.id"))
    
    cantidad_anterior = Column(Numeric(14, 4), default=0.0)
    cantidad_nueva = Column(Numeric(14, 4), default=0.0)
    diferencia = Column(Numeric(14, 4), default=0.0)  # Positiva o negativa
    
    costo_unitario = Column(Numeric(12, 4), default=0.0)
    valor_diferencia = Column(Numeric(14, 2), default=0.0)
    
    motivo = Column(String(300))
    
    # Relaciones
    ajuste = relationship("AjusteInventario", back_populates="items")
    producto = relationship("Producto")
    almacen = relationship("Almacen")
    ubicacion = relationship("UbicacionAlmacen")


# Tabla para importación/exportación temporal
class ArchivoImportacionExportacion(Base):
    """Archivos temporales para importación/exportación"""
    __tablename__ = "archivos_import_export"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    nombre_archivo_original = Column(String(255), nullable=False)
    nombre_archivo_servidor = Column(String(255), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    
    tipo_archivo = Column(String(10))  # xlsx, csv, zip, pdf
    tipo_operacion = Column(String(20))  # importacion, exportacion
    entidad = Column(String(50))  # productos, clientes, facturas, etc.
    
    tamaño_bytes = Column(Integer, default=0)
    estado = Column(String(20), default="pendiente")  # pendiente, procesando, completado, error, eliminado
    mensaje_error = Column(Text)
    
    registros_procesados = Column(Integer, default=0)
    registros_exitosos = Column(Integer, default=0)
    registros_fallidos = Column(Integer, default=0)
    
    escaneo_clamav = Column(Boolean, default=False)
    resultado_clamav = Column(String(50))  # limpio, malware, no_escaneado
    escaneo_virustotal = Column(Boolean, default=False)
    resultado_virustotal = Column(String(50))
    
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_expiracion = Column(DateTime)  # Para eliminación automática
    fecha_eliminacion = Column(DateTime)  # Cuando se eliminó
    
    # Relaciones
    empresa = relationship("Empresa")
    usuario = relationship("Usuario")
