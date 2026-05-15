"""
Servicios para Inventario y Kardex - Fase 4
ContaEC
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import os
import uuid
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import csv
import zipfile
from io import BytesIO

from app.models.inventario import (
    Producto, CategoriaProducto, Almacen, UbicacionAlmacen,
    StockProducto, MovimientoInventario, LoteProducto,
    AjusteInventario, AjusteInventarioItem, ArchivoImportacionExportacion,
    TipoMovimientoEnum, UnidadMedidaEnum
)
from app.models.facturacion import TipoIVAEnum


class InventarioService:
    """Servicios para gestión de inventario"""
    
    @staticmethod
    def obtener_stock_producto(
        db: Session,
        producto_id: int,
        almacen_id: Optional[int] = None,
        empresa_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Obtener stock actual de un producto"""
        query = db.query(StockProducto).filter(StockProducto.producto_id == producto_id)
        
        if almacen_id:
            query = query.filter(StockProducto.almacen_id == almacen_id)
        
        stocks = query.all()
        
        total_disponible = sum(s.cantidad_disponible for s in stocks)
        total_reservada = sum(s.cantidad_reservada for s in stocks)
        total_transito = sum(s.cantidad_transito for s in stocks)
        
        return {
            "producto_id": producto_id,
            "almacen_id": almacen_id,
            "cantidad_disponible": float(total_disponible),
            "cantidad_reservada": float(total_reservada),
            "cantidad_transito": float(total_transito),
            "cantidad_total": float(total_disponible + total_reservada + total_transito),
            "detalle_por_almacen": [
                {
                    "almacen_id": s.almacen_id,
                    "ubicacion_id": s.ubicacion_id,
                    "disponible": float(s.cantidad_disponible),
                    "reservada": float(s.cantidad_reservada)
                }
                for s in stocks
            ]
        }
    
    @staticmethod
    def registrar_movimiento(
        db: Session,
        empresa_id: int,
        producto_id: int,
        almacen_id: int,
        tipo_movimiento: TipoMovimientoEnum,
        cantidad: float,
        costo_unitario: float,
        documento_referencia_tipo: Optional[str] = None,
        documento_referencia_id: Optional[int] = None,
        documento_referencia_numero: Optional[str] = None,
        observaciones: Optional[str] = None,
        creado_por: Optional[int] = None,
        lote_id: Optional[int] = None,
        numero_serial: Optional[str] = None,
        fecha_vencimiento: Optional[datetime] = None,
        ubicacion_id: Optional[int] = None
    ) -> MovimientoInventario:
        """Registrar un movimiento de inventario (entrada/salida)"""
        
        # Obtener stock actual o crear si no existe
        stock = db.query(StockProducto).filter(
            and_(
                StockProducto.producto_id == producto_id,
                StockProducto.almacen_id == almacen_id,
                StockProducto.ubicacion_id == ubicacion_id
            )
        ).first()
        
        if not stock:
            stock = StockProducto(
                producto_id=producto_id,
                almacen_id=almacen_id,
                ubicacion_id=ubicacion_id,
                cantidad_disponible=0,
                cantidad_reservada=0,
                cantidad_transito=0,
                costo_promedio=costo_unitario
            )
            db.add(stock)
            db.flush()
        
        cantidad_anterior = stock.cantidad_disponible
        
        # Actualizar stock según tipo de movimiento
        es_entrada = tipo_movimiento in [
            TipoMovimientoEnum.ENTRADA_COMPRA,
            TipoMovimientoEnum.ENTRADA_DEVOLUCION,
            TipoMovimientoEnum.ENTRADA_AJUSTE_POSITIVO,
            TipoMovimientoEnum.TRANSFERENCIA_ENTRADA
        ]
        
        if es_entrada:
            nueva_cantidad = cantidad_anterior + cantidad
            
            # Recalcular costo promedio ponderado
            valor_actual = stock.cantidad_disponible * stock.costo_promedio
            valor_nuevo = cantidad * costo_unitario
            nuevo_costo_promedio = (valor_actual + valor_nuevo) / nueva_cantidad if nueva_cantidad > 0 else costo_unitario
            
            stock.costo_promedio = nuevo_costo_promedio
            stock.cantidad_disponible = nueva_cantidad
        else:
            nueva_cantidad = cantidad_anterior - cantidad
            stock.cantidad_disponible = nueva_cantidad
        
        # Actualizar cantidad total y valor total
        stock.cantidad_total = stock.cantidad_disponible + stock.cantidad_reservada + stock.cantidad_transito
        stock.valor_total = stock.cantidad_disponible * stock.costo_promedio
        stock.ultima_actualizacion = datetime.utcnow()
        
        # Crear registro de movimiento
        movimiento = MovimientoInventario(
            empresa_id=empresa_id,
            producto_id=producto_id,
            almacen_id=almacen_id,
            ubicacion_id=ubicacion_id,
            tipo_movimiento=tipo_movimiento,
            cantidad_entrada=cantidad if es_entrada else 0,
            cantidad_salida=cantidad if not es_entrada else 0,
            cantidad_anterior=cantidad_anterior,
            cantidad_nueva=nueva_cantidad,
            costo_unitario=costo_unitario,
            costo_total=cantidad * costo_unitario,
            documento_referencia_tipo=documento_referencia_tipo,
            documento_referencia_id=documento_referencia_id,
            documento_referencia_numero=documento_referencia_numero,
            observaciones=observaciones,
            creado_por=creado_por,
            lote_id=lote_id,
            numero_serial=numero_serial,
            fecha_vencimiento=fecha_vencimiento,
            fecha_movimiento=datetime.utcnow()
        )
        
        db.add(movimiento)
        db.commit()
        db.refresh(movimiento)
        
        return movimiento
    
    @staticmethod
    def realizar_ajuste_inventario(
        db: Session,
        empresa_id: int,
        almacen_id: int,
        motivo: str,
        items_ajuste: List[Dict[str, Any]],
        observaciones: Optional[str] = None,
        creado_por: Optional[int] = None
    ) -> AjusteInventario:
        """Realizar ajuste de inventario con múltiples items"""
        
        # Crear número de ajuste único
        numero_ajuste = f"AJT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        ajuste = AjusteInventario(
            empresa_id=empresa_id,
            almacen_id=almacen_id,
            numero_ajuste=numero_ajuste,
            motivo=motivo,
            observaciones=observaciones,
            creado_por=creado_por,
            estado="borrador"
        )
        
        db.add(ajuste)
        db.flush()
        
        valor_total_ajuste = 0
        
        for item_data in items_ajuste:
            producto_id = item_data["producto_id"]
            cantidad_nueva = item_data["cantidad_nueva"]
            ubicacion_id = item_data.get("ubicacion_id")
            
            # Obtener stock actual
            stock = db.query(StockProducto).filter(
                and_(
                    StockProducto.producto_id == producto_id,
                    StockProducto.almacen_id == almacen_id,
                    StockProducto.ubicacion_id == ubicacion_id
                )
            ).first()
            
            if not stock:
                continue
            
            cantidad_anterior = stock.cantidad_disponible
            diferencia = cantidad_nueva - cantidad_anterior
            
            item = AjusteInventarioItem(
                ajuste_id=ajuste.id,
                producto_id=producto_id,
                almacen_id=almacen_id,
                ubicacion_id=ubicacion_id,
                cantidad_anterior=cantidad_anterior,
                cantidad_nueva=cantidad_nueva,
                diferencia=diferencia,
                costo_unitario=float(stock.costo_promedio),
                valor_diferencia=diferencia * float(stock.costo_promedio),
                motivo=motivo
            )
            
            db.add(item)
            valor_total_ajuste += item.valor_diferencia
            
            # Actualizar stock
            stock.cantidad_disponible = cantidad_nueva
            stock.cantidad_total = stock.cantidad_disponible + stock.cantidad_reservada + stock.cantidad_transito
            stock.valor_total = stock.cantidad_disponible * stock.costo_promedio
            stock.ultima_actualizacion = datetime.utcnow()
            
            # Registrar movimiento de ajuste
            tipo_movimiento = TipoMovimientoEnum.ENTRADA_AJUSTE_POSITIVO if diferencia > 0 else TipoMovimientoEnum.SALIDA_AJUSTE_NEGATIVO
            
            movimiento = MovimientoInventario(
                empresa_id=empresa_id,
                producto_id=producto_id,
                almacen_id=almacen_id,
                ubicacion_id=ubicacion_id,
                tipo_movimiento=tipo_movimiento,
                cantidad_entrada=diferencia if diferencia > 0 else 0,
                cantidad_salida=abs(diferencia) if diferencia < 0 else 0,
                cantidad_anterior=cantidad_anterior,
                cantidad_nueva=cantidad_nueva,
                costo_unitario=float(stock.costo_promedio),
                costo_total=abs(diferencia) * float(stock.costo_promedio),
                documento_referencia_tipo="ajuste",
                documento_referencia_id=ajuste.id,
                documento_referencia_numero=numero_ajuste,
                observaciones=f"Ajuste: {motivo}",
                creado_por=creado_por,
                fecha_movimiento=datetime.utcnow()
            )
            
            db.add(movimiento)
        
        ajuste.valor_total_ajuste = valor_total_ajuste
        ajuste.estado = "aprobado"
        ajuste.aprobado_por = creado_por
        ajuste.aprobado_en = datetime.utcnow()
        
        db.commit()
        db.refresh(ajuste)
        
        return ajuste
    
    @staticmethod
    def obtener_kardex(
        db: Session,
        producto_id: int,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        almacen_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Obtener kardex (historial de movimientos) de un producto"""
        
        query = db.query(MovimientoInventario).filter(MovimientoInventario.producto_id == producto_id)
        
        if fecha_desde:
            query = query.filter(MovimientoInventario.fecha_movimiento >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(MovimientoInventario.fecha_movimiento <= fecha_hasta)
        
        if almacen_id:
            query = query.filter(MovimientoInventario.almacen_id == almacen_id)
        
        query = query.order_by(MovimientoInventario.fecha_movimiento.desc())
        
        movimientos = query.all()
        
        return [
            {
                "id": m.id,
                "fecha": m.fecha_movimiento,
                "tipo_movimiento": m.tipo_movimiento.value,
                "entrada": float(m.cantidad_entrada),
                "salida": float(m.cantidad_salida),
                "cantidad_anterior": float(m.cantidad_anterior),
                "cantidad_nueva": float(m.cantidad_nueva),
                "costo_unitario": float(m.costo_unitario),
                "costo_total": float(m.costo_total),
                "documento_tipo": m.documento_referencia_tipo,
                "documento_numero": m.documento_referencia_numero,
                "observaciones": m.observaciones,
                "creado_por": m.creador.nombres if m.creador else None
            }
            for m in movimientos
        ]
    
    @staticmethod
    def verificar_stock_minimo(db: Session, empresa_id: int) -> List[Dict[str, Any]]:
        """Verificar productos con stock por debajo del mínimo"""
        
        productos = db.query(Producto).filter(
            and_(
                Producto.empresa_id == empresa_id,
                Producto.activo == True,
                Producto.es_servicio == False
            )
        ).all()
        
        alertas = []
        
        for producto in productos:
            stock_info = InventarioService.obtener_stock_producto(
                db, producto.id, empresa_id=empresa_id
            )
            
            if stock_info["cantidad_disponible"] <= producto.stock_minimo:
                alertas.append({
                    "producto_id": producto.id,
                    "nombre": producto.nombre,
                    "codigo_interno": producto.codigo_interno,
                    "stock_actual": stock_info["cantidad_disponible"],
                    "stock_minimo": producto.stock_minimo,
                    "punto_reorden": producto.punto_reorden,
                    "diferencia": producto.stock_minimo - stock_info["cantidad_disponible"]
                })
        
        return alertas


class ImportacionExportacionService:
    """Servicios para importación y exportación de datos"""
    
    @staticmethod
    async def exportar_productos_excel(
        db: Session,
        empresa_id: int,
        usuario_id: int
    ) -> Tuple[bytes, str]:
        """Exportar productos a Excel"""
        
        productos = db.query(Producto).filter(Producto.empresa_id == empresa_id).all()
        
        data = []
        for prod in productos:
            data.append({
                "Código Interno": prod.codigo_interno,
                "Código Barras": prod.codigo_barras,
                "Nombre": prod.nombre,
                "Descripción": prod.descripcion,
                "Categoría": prod.categoria.nombre if prod.categoria else "",
                "Costo Promedio": float(prod.costo_promedio),
                "Precio Venta": float(prod.precio_venta_base),
                "IVA %": prod.porcentaje_iva,
                "Unidad": prod.unidad_medida.value,
                "Stock Mínimo": prod.stock_minimo,
                "Activo": "Sí" if prod.activo else "No"
            })
        
        df = pd.DataFrame(data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Productos')
        
        output.seek(0)
        
        return output.getvalue(), f"productos_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    @staticmethod
    async def importar_productos_excel(
        db: Session,
        empresa_id: int,
        usuario_id: int,
        file_content: bytes,
        nombre_archivo: str
    ) -> Dict[str, Any]:
        """Importar productos desde Excel"""
        
        resultado = {
            "registros_procesados": 0,
            "registros_exitosos": 0,
            "registros_fallidos": 0,
            "errores": []
        }
        
        try:
            df = pd.read_excel(BytesIO(file_content))
            
            for index, row in df.iterrows():
                resultado["registros_procesados"] += 1
                
                try:
                    # Verificar si ya existe
                    producto_existente = db.query(Producto).filter(
                        and_(
                            Producto.empresa_id == empresa_id,
                            Producto.codigo_interno == str(row.get("Código Interno", ""))
                        )
                    ).first()
                    
                    if producto_existente:
                        # Actualizar existente
                        producto_existente.nombre = row.get("Nombre", producto_existente.nombre)
                        producto_existente.descripcion = row.get("Descripción", producto_existente.descripcion)
                        producto_existente.precio_venta_base = row.get("Precio Venta", producto_existente.precio_venta_base)
                        producto_existente.costo_promedio = row.get("Costo Promedio", producto_existente.costo_promedio)
                    else:
                        # Crear nuevo
                        producto = Producto(
                            empresa_id=empresa_id,
                            codigo_interno=str(row.get("Código Interno", f"PROD-{index}")),
                            codigo_barras=str(row.get("Código Barras", "")),
                            nombre=row.get("Nombre", f"Producto {index}"),
                            descripcion=row.get("Descripción", ""),
                            precio_venta_base=float(row.get("Precio Venta", 0)),
                            costo_promedio=float(row.get("Costo Promedio", 0)),
                            porcentaje_iva=float(row.get("IVA %", 15)),
                            unidad_medida=UnidadMedidaEnum(row.get("Unidad", "UNID")),
                            stock_minimo=float(row.get("Stock Mínimo", 0)),
                            activo=True
                        )
                        db.add(producto)
                    
                    resultado["registros_exitosos"] += 1
                    
                except Exception as e:
                    resultado["registros_fallidos"] += 1
                    resultado["errores"].append({
                        "fila": index + 2,
                        "error": str(e)
                    })
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
        
        return resultado
    
    @staticmethod
    async def exportar_kardex_excel(
        db: Session,
        empresa_id: int,
        producto_id: Optional[int] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None
    ) -> Tuple[bytes, str]:
        """Exportar kardex a Excel"""
        
        query = db.query(MovimientoInventario).filter(MovimientoInventario.empresa_id == empresa_id)
        
        if producto_id:
            query = query.filter(MovimientoInventario.producto_id == producto_id)
        
        if fecha_desde:
            query = query.filter(MovimientoInventario.fecha_movimiento >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(MovimientoInventario.fecha_movimiento <= fecha_hasta)
        
        movimientos = query.order_by(MovimientoInventario.fecha_movimiento).all()
        
        data = []
        for mov in movimientos:
            data.append({
                "Fecha": mov.fecha_movimiento.strftime("%Y-%m-%d %H:%M:%S"),
                "Producto": mov.producto.nombre if mov.producto else "",
                "Tipo Movimiento": mov.tipo_movimiento.value,
                "Entrada": float(mov.cantidad_entrada),
                "Salida": float(mov.cantidad_salida),
                "Cantidad Anterior": float(mov.cantidad_anterior),
                "Cantidad Nueva": float(mov.cantidad_nueva),
                "Costo Unitario": float(mov.costo_unitario),
                "Costo Total": float(mov.costo_total),
                "Documento": mov.documento_referencia_numero,
                "Observaciones": mov.observaciones
            })
        
        df = pd.DataFrame(data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Kardex')
        
        output.seek(0)
        
        return output.getvalue(), f"kardex_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    @staticmethod
    def eliminar_archivo_temporal(ruta_archivo: str):
        """Eliminar archivo temporal después de su uso"""
        try:
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
        except Exception as e:
            print(f"Error al eliminar archivo temporal: {e}")
