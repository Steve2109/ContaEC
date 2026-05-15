"""
Rutas API para Inventario - Fase 4
ContaEC
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import tempfile

from app.core.database import get_db
from app.models import User, Company as Empresa
from app.models.inventario import (
    Producto, CategoriaProducto, Almacen, StockProducto,
    MovimientoInventario, AjusteInventario, TipoMovimientoEnum
)
from app.services.inventario_service import InventarioService, ImportacionExportacionService
from app.services.file_security_service import FileSecurityService
from app.core.security import get_current_user
from app.core.dependencies import get_current_empresa

router = APIRouter(prefix="/inventario", tags=["Inventario"])


# ==================== PRODUCTOS ====================

@router.post("/productos/", status_code=status.HTTP_201_CREATED)
async def crear_producto(
    producto_data: dict,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear un nuevo producto"""
    from app.models.inventario import UnidadMedidaEnum, TipoIVAEnum
    
    producto = Producto(
        empresa_id=empresa.id,
        creado_por=usuario.id,
        **producto_data
    )
    
    db.add(producto)
    db.commit()
    db.refresh(producto)
    
    return producto


@router.get("/productos/")
async def listar_productos(
    skip: int = 0,
    limit: int = 100,
    buscar: Optional[str] = None,
    categoria_id: Optional[int] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Listar productos del inventario"""
    query = db.query(Producto).filter(Producto.empresa_id == empresa.id)
    
    if buscar:
        query = query.filter(
            (Producto.nombre.contains(buscar)) |
            (Producto.codigo_interno.contains(buscar)) |
            (Producto.codigo_barras.contains(buscar))
        )
    
    if categoria_id:
        query = query.filter(Producto.categoria_id == categoria_id)
    
    return query.offset(skip).limit(limit).all()


@router.get("/productos/{producto_id}")
async def obtener_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Obtener detalle de un producto"""
    producto = db.query(Producto).filter(
        and_(Producto.id == producto_id, Producto.empresa_id == empresa.id)
    ).first()
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    stock_info = InventarioService.obtener_stock_producto(db, producto_id, empresa_id=empresa.id)
    
    return {
        "producto": producto,
        "stock": stock_info
    }


@router.put("/productos/{producto_id}")
async def actualizar_producto(
    producto_id: int,
    producto_data: dict,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Actualizar producto"""
    producto = db.query(Producto).filter(
        and_(Producto.id == producto_id, Producto.empresa_id == empresa.id)
    ).first()
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    for field, value in producto_data.items():
        if hasattr(producto, field):
            setattr(producto, field, value)
    
    db.commit()
    db.refresh(producto)
    
    return producto


@router.delete("/productos/{producto_id}")
async def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Eliminar producto (soft delete)"""
    producto = db.query(Producto).filter(
        and_(Producto.id == producto_id, Producto.empresa_id == empresa.id)
    ).first()
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    producto.activo = False
    db.commit()
    
    return {"mensaje": "Producto eliminado exitosamente"}


# ==================== STOCK ====================

@router.get("/stock/{producto_id}")
async def obtener_stock_producto(
    producto_id: int,
    almacen_id: Optional[int] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Obtener stock de un producto"""
    producto = db.query(Producto).filter(
        and_(Producto.id == producto_id, Producto.empresa_id == empresa.id)
    ).first()
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    stock_info = InventarioService.obtener_stock_producto(
        db, producto_id, almacen_id, empresa_id=empresa.id
    )
    
    return stock_info


@router.get("/stock/alertas/")
async def obtener_alertas_stock(
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Obtener productos con stock por debajo del mínimo"""
    alertas = InventarioService.verificar_stock_minimo(db, empresa.id)
    return {"alertas": alertas}


# ==================== MOVIMIENTOS (KARDEX) ====================

@router.post("/movimientos/", status_code=status.HTTP_201_CREATED)
async def registrar_movimiento(
    movimiento_data: dict,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Registrar movimiento de inventario (entrada/salida)"""
    
    tipo_movimiento = TipoMovimientoEnum(movimiento_data.get("tipo_movimiento"))
    
    movimiento = InventarioService.registrar_movimiento(
        db=db,
        empresa_id=empresa.id,
        producto_id=movimiento_data["producto_id"],
        almacen_id=movimiento_data["almacen_id"],
        tipo_movimiento=tipo_movimiento,
        cantidad=movimiento_data["cantidad"],
        costo_unitario=movimiento_data.get("costo_unitario", 0),
        documento_referencia_tipo=movimiento_data.get("documento_referencia_tipo"),
        documento_referencia_id=movimiento_data.get("documento_referencia_id"),
        documento_referencia_numero=movimiento_data.get("documento_referencia_numero"),
        observaciones=movimiento_data.get("observaciones"),
        creado_por=usuario.id
    )
    
    return movimiento


@router.get("/kardex/{producto_id}")
async def obtener_kardex(
    producto_id: int,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    almacen_id: Optional[int] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Obtener kardex (historial de movimientos) de un producto"""
    producto = db.query(Producto).filter(
        and_(Producto.id == producto_id, Producto.empresa_id == empresa.id)
    ).first()
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    kardex = InventarioService.obtener_kardex(
        db, producto_id, fecha_desde, fecha_hasta, almacen_id
    )
    
    return {"kardex": kardex}


# ==================== AJUSTES ====================

@router.post("/ajustes/", status_code=status.HTTP_201_CREATED)
async def crear_ajuste_inventario(
    ajuste_data: dict,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear ajuste de inventario"""
    
    ajuste = InventarioService.realizar_ajuste_inventario(
        db=db,
        empresa_id=empresa.id,
        almacen_id=ajuste_data["almacen_id"],
        motivo=ajuste_data["motivo"],
        items_ajuste=ajuste_data["items"],
        observaciones=ajuste_data.get("observaciones"),
        creado_por=usuario.id
    )
    
    return ajuste


@router.get("/ajustes/")
async def listar_ajustes(
    skip: int = 0,
    limit: int = 100,
    almacen_id: Optional[int] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Listar ajustes de inventario"""
    query = db.query(AjusteInventario).filter(AjusteInventario.empresa_id == empresa.id)
    
    if almacen_id:
        query = query.filter(AjusteInventario.almacen_id == almacen_id)
    
    return query.order_by(AjusteInventario.fecha_ajuste.desc()).offset(skip).limit(limit).all()


# ==================== ALMACENES ====================

@router.post("/almacenes/", status_code=status.HTTP_201_CREATED)
async def crear_almacen(
    almacen_data: dict,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear un nuevo almacén"""
    almacen = Almacen(empresa_id=empresa.id, **almacen_data)
    db.add(almacen)
    db.commit()
    db.refresh(almacen)
    return almacen


@router.get("/almacenes/")
async def listar_almacenes(
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Listar almacenes de la empresa"""
    return db.query(Almacen).filter(Almacen.empresa_id == empresa.id).all()


# ==================== IMPORTACIÓN/EXPORTACIÓN ====================

@router.post("/exportar/productos/excel/")
async def exportar_productos_excel(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Exportar productos a Excel"""
    
    file_content, filename = await ImportacionExportacionService.exportar_productos_excel(
        db, empresa.id, usuario.id
    )
    
    # Crear archivo temporal
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"export_{filename}")
    
    with open(temp_path, "wb") as f:
        f.write(file_content)
    
    # Programar eliminación automática
    background_tasks.add_task(ImportacionExportacionService.eliminar_archivo_temporal, temp_path)
    
    return {
        "mensaje": "Archivo generado exitosamente",
        "nombre_archivo": filename,
        "ruta_temporal": temp_path,
        "nota": "El archivo se eliminará automáticamente después de la descarga"
    }


@router.post("/importar/productos/excel/")
async def importar_productos_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Importar productos desde Excel con escaneo de seguridad"""
    
    # Validar tipo de archivo
    allowed_extensions = [".xlsx", ".xls"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Extensions permitidas: {', '.join(allowed_extensions)}"
        )
    
    # Escanear con ClamAV
    file_content = await file.read()
    
    escaneo_result = await FileSecurityService.scan_file_with_clamav(file_content)
    
    if not escaneo_result["limpio"]:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo contiene malware o no pasó el escaneo de seguridad: {escaneo_result['mensaje']}"
        )
    
    # Procesar importación
    resultado = await ImportacionExportacionService.importar_productos_excel(
        db=db,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        file_content=file_content,
        nombre_archivo=file.filename
    )
    
    return {
        "mensaje": "Importación completada",
        "resultado": resultado
    }


@router.get("/exportar/kardex/excel/")
async def exportar_kardex_excel(
    producto_id: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Exportar kardex a Excel"""
    
    file_content, filename = await ImportacionExportacionService.exportar_kardex_excel(
        db, empresa.id, producto_id, fecha_desde, fecha_hasta
    )
    
    return {
        "mensaje": "Archivo generado exitosamente",
        "nombre_archivo": filename,
        "tamaño_bytes": len(file_content),
        "nota": "Use endpoint de descarga para obtener el archivo"
    }


# ==================== CATEGORÍAS ====================

@router.post("/categorias/", status_code=status.HTTP_201_CREATED)
async def crear_categoria(
    categoria_data: dict,
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Crear categoría de productos"""
    categoria = CategoriaProducto(empresa_id=empresa.id, **categoria_data)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.get("/categorias/")
async def listar_categorias(
    db: Session = Depends(get_db),
    empresa: Empresa = Depends(get_current_empresa)
):
    """Listar categorías de productos"""
    return db.query(CategoriaProducto).filter(
        CategoriaProducto.empresa_id == empresa.id,
        CategoriaProducto.activo == True
    ).all()
