"""
Servicios SRI para facturación electrónica ecuatoriana.

Incluye:
- clave de acceso oficial de 49 dígitos;
- XML de factura, notas de crédito/débito, retenciones y guías de remisión;
- firma XML con certificado PKCS#12/P12;
- cliente SOAP para recepción y autorización SRI.
"""
from __future__ import annotations

import base64
import hashlib
import random
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.dom import minidom

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app.core.security import decrypt_sensitive_data
from app.core.sri_constants import IVA_CODES
from app.models.facturacion import (
    EstadoComprobanteEnum,
    TipoComprobanteEnum,
    TipoContribuyenteEnum,
    TipoIVAEnum,
)


def _money(value: Any) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amount:.2f}"


def _percent(value: Any) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
    return f"{amount:.2f}"


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def _digits(value: str, length: int) -> str:
    cleaned = re.sub(r"\D", "", value or "")
    if len(cleaned) != length:
        raise ValueError(f"El valor debe tener {length} dígitos")
    return cleaned


def _add(parent: ET.Element, tag: str, value: Any, fallback: str = "") -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.text = _text(value, fallback)
    return child


def _tipo_identificacion_sri(cliente: Any) -> str:
    if not cliente:
        return "07"
    if getattr(cliente, "es_consumidor_final", False):
        return "07"
    identificacion = _text(getattr(cliente, "identificacion", ""))
    tipo = _text(getattr(cliente, "tipo_identificacion", "")).lower()
    if tipo == "ruc" or len(identificacion) == 13:
        return "04"
    if tipo in {"cedula", "cédula"} or len(identificacion) == 10:
        return "05"
    if tipo == "pasaporte":
        return "06"
    return "08"


def _obligado_contabilidad(tipo_contribuyente: Any) -> str:
    value = getattr(tipo_contribuyente, "value", tipo_contribuyente)
    return "SI" if value in {"02", "obligado_contabilidad"} else "NO"


def _iva_catalog_key(tipo_iva: Any, porcentaje_iva: Any = None) -> str:
    value = getattr(tipo_iva, "value", tipo_iva)
    if value in {"no_objeto", "NO_OBJETO"}:
        return "NO_OBJETO"
    if value in {"exento", "EXENTO"}:
        return "EXENTO"
    if value in {"diferenciado", "DIFERENCIADO"}:
        return "DIFERENCIADO"
    if value:
        return str(value)
    return str(int(porcentaje_iva or 15))


def sri_codigo_iva(tipo_iva: Any, porcentaje_iva: Any = None) -> str:
    key = _iva_catalog_key(tipo_iva, porcentaje_iva)
    return IVA_CODES.get(key, IVA_CODES["15"])["code"]


@dataclass
class RespuestaSRI:
    exito: bool
    estado: str
    mensaje: str
    numero_autorizacion: Optional[str] = None
    fecha_autorizacion: Optional[str] = None
    raw_xml: Optional[str] = None


class GeneradorClaveAcceso:
    """Genera la clave de acceso SRI: 49 dígitos con módulo 11."""

    @staticmethod
    def generar(
        fecha_emision: datetime,
        tipo_comprobante: str,
        ruc: str,
        ambiente: str,
        secuencial: str,
        establecimiento: str = "001",
        punto_emision: str = "001",
        codigo_numerico: Optional[str] = None,
        tipo_emision: str = "1",
        numero_autorizacion: Optional[str] = None,
    ) -> str:
        del numero_autorizacion
        cod_doc = _digits(str(tipo_comprobante), 2)
        ruc = _digits(ruc, 13)
        ambiente = _digits(str(ambiente), 1)
        establecimiento = _digits(establecimiento, 3)
        punto_emision = _digits(punto_emision, 3)
        secuencial = _digits(secuencial.zfill(9), 9)
        tipo_emision = _digits(str(tipo_emision), 1)
        codigo_numerico = codigo_numerico or "".join(str(random.randint(0, 9)) for _ in range(8))
        codigo_numerico = _digits(codigo_numerico, 8)

        clave_sin_dv = (
            fecha_emision.strftime("%d%m%Y")
            + cod_doc
            + ruc
            + ambiente
            + establecimiento
            + punto_emision
            + secuencial
            + codigo_numerico
            + tipo_emision
        )
        return clave_sin_dv + GeneradorClaveAcceso.calcular_digito_verificador(clave_sin_dv)

    @staticmethod
    def calcular_digito_verificador(clave: str) -> str:
        coeficientes = [2, 3, 4, 5, 6, 7]
        suma = sum(int(digito) * coeficientes[i % 6] for i, digito in enumerate(reversed(clave)))
        resultado = 11 - (suma % 11)
        if resultado == 11:
            return "0"
        if resultado == 10:
            return "1"
        return str(resultado)


class GeneradorXML:
    VERSION = "1.1.0"

    @staticmethod
    def generar(comprobante: Any, empresa_config: Any) -> str:
        tipo = getattr(comprobante.tipo_comprobante, "value", comprobante.tipo_comprobante)
        if tipo == TipoComprobanteEnum.FACTURA.value:
            return GeneradorXML.generar_factura(comprobante, empresa_config, comprobante.detalles, comprobante.impuestos)
        if tipo == TipoComprobanteEnum.NOTA_CREDITO.value:
            return GeneradorXML.generar_nota_credito(comprobante, empresa_config, comprobante.detalles, comprobante.impuestos)
        if tipo == TipoComprobanteEnum.NOTA_DEBITO.value:
            return GeneradorXML.generar_nota_debito(comprobante, empresa_config, comprobante.impuestos)
        if tipo == TipoComprobanteEnum.RETENCION.value:
            return GeneradorXML.generar_retencion(comprobante, empresa_config, comprobante.retenciones)
        raise ValueError(f"Tipo de comprobante no soportado: {tipo}")

    @staticmethod
    def generar_factura(comprobante: Any, empresa_config: Any, detalles: List[Any], impuestos: List[Any]) -> str:
        root = ET.Element("factura", {"id": "comprobante", "version": GeneradorXML.VERSION})
        GeneradorXML._info_tributaria(root, comprobante, empresa_config)

        info = ET.SubElement(root, "infoFactura")
        GeneradorXML._datos_comprador(info, comprobante, empresa_config)
        _add(info, "totalSinImpuestos", _money(comprobante.subtotal_sin_impuestos))
        _add(info, "totalDescuento", _money(comprobante.total_descuentos))
        GeneradorXML._total_con_impuestos(info, impuestos)
        _add(info, "propina", "0.00")
        _add(info, "importeTotal", _money(comprobante.importe_total))
        _add(info, "moneda", comprobante.moneda or "DOLAR")
        pagos = ET.SubElement(info, "pagos")
        pago = ET.SubElement(pagos, "pago")
        _add(pago, "formaPago", "20")
        _add(pago, "total", _money(comprobante.importe_total))

        detalles_node = ET.SubElement(root, "detalles")
        for detalle in detalles:
            det = ET.SubElement(detalles_node, "detalle")
            _add(det, "codigoPrincipal", detalle.codigo_principal or "001")
            if detalle.codigo_secundario:
                _add(det, "codigoAuxiliar", detalle.codigo_secundario)
            _add(det, "descripcion", detalle.descripcion)
            _add(det, "cantidad", _percent(detalle.cantidad))
            _add(det, "precioUnitario", _money(detalle.precio_unitario))
            _add(det, "descuento", _money(detalle.descuento))
            _add(det, "precioTotalSinImpuesto", _money(detalle.precio_total_sin_impuestos))
            GeneradorXML._impuestos_detalle(det, detalle)

        return GeneradorXML._pretty_xml(root)

    @staticmethod
    def generar_nota_credito(comprobante: Any, empresa_config: Any, detalles: List[Any], impuestos: List[Any]) -> str:
        root = ET.Element("notaCredito", {"id": "comprobante", "version": GeneradorXML.VERSION})
        GeneradorXML._info_tributaria(root, comprobante, empresa_config)

        info = ET.SubElement(root, "infoNotaCredito")
        GeneradorXML._datos_comprador(info, comprobante, empresa_config, tag_dir="dirEstablecimiento")
        _add(info, "codDocModificado", comprobante.tipo_emision_referencia or "01")
        _add(info, "numDocModificado", comprobante.comprobante_referencia or "000-000-000000000")
        _add(info, "fechaEmisionDocSustento", comprobante.fecha_emision.strftime("%d/%m/%Y"))
        _add(info, "totalSinImpuestos", _money(comprobante.subtotal_sin_impuestos))
        _add(info, "valorModificacion", _money(comprobante.importe_total))
        _add(info, "moneda", comprobante.moneda or "DOLAR")
        GeneradorXML._total_con_impuestos(info, impuestos)
        _add(info, "motivo", comprobante.motivo_modificacion or "Nota de crédito")

        detalles_node = ET.SubElement(root, "detalles")
        for detalle in detalles:
            det = ET.SubElement(detalles_node, "detalle")
            _add(det, "codigoInterno", detalle.codigo_principal or "001")
            if detalle.codigo_secundario:
                _add(det, "codigoAdicional", detalle.codigo_secundario)
            _add(det, "descripcion", detalle.descripcion)
            _add(det, "cantidad", _percent(detalle.cantidad))
            _add(det, "precioUnitario", _money(detalle.precio_unitario))
            _add(det, "descuento", _money(detalle.descuento))
            _add(det, "precioTotalSinImpuesto", _money(detalle.precio_total_sin_impuestos))
            GeneradorXML._impuestos_detalle(det, detalle)

        return GeneradorXML._pretty_xml(root)

    @staticmethod
    def generar_nota_debito(comprobante: Any, empresa_config: Any, impuestos: List[Any]) -> str:
        root = ET.Element("notaDebito", {"id": "comprobante", "version": GeneradorXML.VERSION})
        GeneradorXML._info_tributaria(root, comprobante, empresa_config)

        info = ET.SubElement(root, "infoNotaDebito")
        GeneradorXML._datos_comprador(info, comprobante, empresa_config, tag_dir="dirEstablecimiento")
        _add(info, "codDocModificado", comprobante.tipo_emision_referencia or "01")
        _add(info, "numDocModificado", comprobante.comprobante_referencia or "000-000-000000000")
        _add(info, "fechaEmisionDocSustento", comprobante.fecha_emision.strftime("%d/%m/%Y"))
        _add(info, "totalSinImpuestos", _money(comprobante.subtotal_sin_impuestos))
        GeneradorXML._total_con_impuestos(info, impuestos)
        _add(info, "valorTotal", _money(comprobante.importe_total))

        motivos = ET.SubElement(root, "motivos")
        motivo = ET.SubElement(motivos, "motivo")
        _add(motivo, "razon", comprobante.motivo_modificacion or "Intereses o cargos")
        _add(motivo, "valor", _money(comprobante.subtotal_sin_impuestos))
        return GeneradorXML._pretty_xml(root)

    @staticmethod
    def generar_retencion(comprobante: Any, empresa_config: Any, retenciones: List[Any]) -> str:
        root = ET.Element("comprobanteRetencion", {"id": "comprobante", "version": "1.0.0"})
        GeneradorXML._info_tributaria(root, comprobante, empresa_config)

        info = ET.SubElement(root, "infoCompRetencion")
        _add(info, "fechaEmision", comprobante.fecha_emision.strftime("%d/%m/%Y"))
        _add(info, "dirEstablecimiento", getattr(empresa_config, "direccion_establecimiento", None) or "SIN DIRECCION")
        _add(info, "obligadoContabilidad", _obligado_contabilidad(empresa_config.tipo_contribuyente))
        _add(info, "tipoIdentificacionSujetoRetenido", _tipo_identificacion_sri(comprobante.cliente))
        _add(info, "razonSocialSujetoRetenido", getattr(comprobante.cliente, "razon_social", None) or "SUJETO RETENIDO")
        _add(info, "identificacionSujetoRetenido", getattr(comprobante.cliente, "identificacion", None) or "9999999999999")
        _add(info, "periodoFiscal", comprobante.fecha_emision.strftime("%m/%Y"))

        impuestos = ET.SubElement(root, "impuestos")
        for retencion in retenciones:
            impuesto = ET.SubElement(impuestos, "impuesto")
            _add(impuesto, "codigo", retencion.codigo)
            _add(impuesto, "codigoRetencion", retencion.codigo_retencion)
            _add(impuesto, "baseImponible", _money(retencion.base_imponible))
            _add(impuesto, "porcentajeRetener", _percent(retencion.porcentaje_retener))
            _add(impuesto, "valorRetenido", _money(retencion.valor_retenido))
            _add(impuesto, "codDocSustento", comprobante.tipo_emision_referencia or "01")
            _add(impuesto, "numDocSustento", comprobante.comprobante_referencia or "000000000000000")
            _add(impuesto, "fechaEmisionDocSustento", comprobante.fecha_emision.strftime("%d/%m/%Y"))

        return GeneradorXML._pretty_xml(root)

    @staticmethod
    def generar_guia_remision(guia: Any, empresa_config: Any, detalles: Optional[List[Any]] = None) -> str:
        root = ET.Element("guiaRemision", {"id": "comprobante", "version": "1.1.0"})
        GeneradorXML._info_tributaria(root, guia, empresa_config, cod_doc=TipoComprobanteEnum.GUIA_REMISION.value)
        info = ET.SubElement(root, "infoGuiaRemision")
        _add(info, "dirEstablecimiento", getattr(empresa_config, "direccion_establecimiento", None) or "SIN DIRECCION")
        _add(info, "dirPartida", getattr(empresa_config, "direccion_matriz", None) or "SIN DIRECCION")
        _add(info, "razonSocialTransportista", getattr(guia, "transportista_razon_social", None) or "TRANSPORTISTA")
        _add(info, "tipoIdentificacionTransportista", "04")
        _add(info, "rucTransportista", getattr(guia, "transportista_ruc", None) or empresa_config.ruc)
        _add(info, "obligadoContabilidad", _obligado_contabilidad(empresa_config.tipo_contribuyente))
        _add(info, "fechaIniTransporte", guia.fecha_inicio_transporte.strftime("%d/%m/%Y"))
        _add(info, "fechaFinTransporte", (guia.fecha_fin_transporte or guia.fecha_inicio_transporte).strftime("%d/%m/%Y"))
        _add(info, "placa", guia.placa_vehiculo or "AAA0000")

        destinatarios = ET.SubElement(root, "destinatarios")
        destinatario = ET.SubElement(destinatarios, "destinatario")
        _add(destinatario, "identificacionDestinatario", guia.destinatario_ruc or "9999999999999")
        _add(destinatario, "razonSocialDestinatario", guia.destinatario_razon_social or "CONSUMIDOR FINAL")
        _add(destinatario, "dirDestinatario", guia.destinatario_direccion or "SIN DIRECCION")
        _add(destinatario, "motivoTraslado", guia.motivo_traslado or "Venta")
        _add(destinatario, "codEstabDestino", "001")
        _add(destinatario, "ruta", "")
        if detalles:
            dets = ET.SubElement(destinatario, "detalles")
            for item in detalles:
                det = ET.SubElement(dets, "detalle")
                _add(det, "codigoInterno", getattr(item, "codigo_principal", None) or "001")
                _add(det, "descripcion", getattr(item, "descripcion", None) or "Producto")
                _add(det, "cantidad", _percent(getattr(item, "cantidad", 1)))
        return GeneradorXML._pretty_xml(root)

    @staticmethod
    def _info_tributaria(root: ET.Element, comprobante: Any, empresa_config: Any, cod_doc: Optional[str] = None) -> None:
        info = ET.SubElement(root, "infoTributaria")
        ambiente = "2" if empresa_config.ambiente == "produccion" else "1"
        _add(info, "ambiente", ambiente)
        _add(info, "tipoEmision", empresa_config.tipo_emision or "1")
        _add(info, "razonSocial", empresa_config.razon_social)
        _add(info, "nombreComercial", empresa_config.nombre_comercial or empresa_config.razon_social)
        _add(info, "ruc", empresa_config.ruc)
        _add(info, "claveAcceso", comprobante.clave_acceso)
        _add(info, "codDoc", cod_doc or getattr(comprobante.tipo_comprobante, "value", comprobante.tipo_comprobante))
        _add(info, "estab", comprobante.establecimiento)
        _add(info, "ptoEmi", comprobante.punto_emision)
        _add(info, "secuencial", comprobante.secuencial)
        _add(info, "dirMatriz", getattr(empresa_config, "direccion_matriz", None) or "SIN DIRECCION")

    @staticmethod
    def _datos_comprador(info: ET.Element, comprobante: Any, empresa_config: Any, tag_dir: str = "dirEstablecimiento") -> None:
        _add(info, "fechaEmision", comprobante.fecha_emision.strftime("%d/%m/%Y"))
        _add(info, tag_dir, getattr(empresa_config, "direccion_establecimiento", None) or "SIN DIRECCION")
        if getattr(empresa_config, "contribuyente_especial", None):
            _add(info, "contribuyenteEspecial", empresa_config.contribuyente_especial)
        _add(info, "obligadoContabilidad", _obligado_contabilidad(empresa_config.tipo_contribuyente))
        _add(info, "tipoIdentificacionComprador", _tipo_identificacion_sri(comprobante.cliente))
        _add(info, "razonSocialComprador", getattr(comprobante.cliente, "razon_social", None) or "CONSUMIDOR FINAL")
        _add(info, "identificacionComprador", getattr(comprobante.cliente, "identificacion", None) or "9999999999999")
        if getattr(comprobante.cliente, "direccion", None):
            _add(info, "direccionComprador", comprobante.cliente.direccion)

    @staticmethod
    def _total_con_impuestos(parent: ET.Element, impuestos: Iterable[Any]) -> None:
        total = ET.SubElement(parent, "totalConImpuestos")
        for imp in impuestos:
            item = ET.SubElement(total, "totalImpuesto")
            _add(item, "codigo", imp.codigo)
            _add(item, "codigoPorcentaje", imp.codigo_porcentaje)
            _add(item, "baseImponible", _money(imp.base_imponible))
            _add(item, "valor", _money(imp.valor))
            if imp.codigo == "2":
                _add(item, "tarifa", _percent(imp.tarifa))

    @staticmethod
    def _impuestos_detalle(detalle_node: ET.Element, detalle: Any) -> None:
        impuestos = ET.SubElement(detalle_node, "impuestos")
        iva = ET.SubElement(impuestos, "impuesto")
        _add(iva, "codigo", "2")
        _add(iva, "codigoPorcentaje", sri_codigo_iva(detalle.tipo_iva, detalle.porcentaje_iva))
        _add(iva, "tarifa", _percent(detalle.porcentaje_iva))
        _add(iva, "baseImponible", _money(detalle.precio_total_sin_impuestos))
        _add(iva, "valor", _money(detalle.valor_iva))
        if getattr(detalle, "valor_ice", 0):
            ice = ET.SubElement(impuestos, "impuesto")
            _add(ice, "codigo", "3")
            _add(ice, "codigoPorcentaje", detalle.tipo_ice or "0")
            _add(ice, "tarifa", _percent(detalle.porcentaje_ice))
            _add(ice, "baseImponible", _money(detalle.precio_total_sin_impuestos))
            _add(ice, "valor", _money(detalle.valor_ice))

    @staticmethod
    def _pretty_xml(elem: ET.Element) -> str:
        xml_bytes = ET.tostring(elem, encoding="utf-8", method="xml")
        parsed = minidom.parseString(xml_bytes)
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


class FirmadorXML:
    """Firma XML con certificado digital PKCS#12/P12.

    La firma insertada es XMLDSig enveloped RSA-SHA256. Para producción SRI, el
    certificado cargado debe ser válido y emitido por una entidad acreditada.
    """

    @staticmethod
    def extraer_info_certificado(certificado_encriptado: str, clave_encriptada: str) -> Dict[str, Any]:
        cert_bytes, password = FirmadorXML._decrypt_pkcs12(certificado_encriptado, clave_encriptada)
        private_key, cert, _ = pkcs12.load_key_and_certificates(cert_bytes, password)
        if not cert or not private_key:
            raise ValueError("El certificado no contiene clave privada o certificado público")
        common_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        issuer_name = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        return {
            "sujeto": common_name[0].value if common_name else cert.subject.rfc4514_string(),
            "emisor": issuer_name[0].value if issuer_name else cert.issuer.rfc4514_string(),
            "numero_serial": str(cert.serial_number),
            "fecha_inicio": cert.not_valid_before,
            "fecha_fin": cert.not_valid_after,
            "dias_restantes": (cert.not_valid_after - datetime.utcnow()).days,
        }

    @staticmethod
    def firmar(xml_content: str, certificado_encriptado: str, clave_encriptada: str, clave_desencriptacion: Optional[str] = None) -> str:
        del clave_desencriptacion
        cert_bytes, password = FirmadorXML._decrypt_pkcs12(certificado_encriptado, clave_encriptada)
        private_key, cert, _ = pkcs12.load_key_and_certificates(cert_bytes, password)
        if not private_key or not cert:
            raise ValueError("Certificado PKCS#12 inválido")

        root = ET.fromstring(xml_content.encode("utf-8"))
        canonical_payload = ET.tostring(root, encoding="utf-8", method="xml")
        digest = hashlib.sha256(canonical_payload).digest()
        signature = private_key.sign(digest, padding.PKCS1v15(), hashes.SHA256())
        cert_der = cert.public_bytes(serialization.Encoding.DER)

        signature_node = ET.SubElement(root, "{http://www.w3.org/2000/09/xmldsig#}Signature")
        signed_info = ET.SubElement(signature_node, "{http://www.w3.org/2000/09/xmldsig#}SignedInfo")
        _add(signed_info, "{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod", "")
        signed_info[-1].set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        _add(signed_info, "{http://www.w3.org/2000/09/xmldsig#}SignatureMethod", "")
        signed_info[-1].set("Algorithm", "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256")
        reference = ET.SubElement(signed_info, "{http://www.w3.org/2000/09/xmldsig#}Reference", {"URI": "#comprobante"})
        transforms = ET.SubElement(reference, "{http://www.w3.org/2000/09/xmldsig#}Transforms")
        ET.SubElement(transforms, "{http://www.w3.org/2000/09/xmldsig#}Transform", {"Algorithm": "http://www.w3.org/2000/09/xmldsig#enveloped-signature"})
        ET.SubElement(reference, "{http://www.w3.org/2000/09/xmldsig#}DigestMethod", {"Algorithm": "http://www.w3.org/2001/04/xmlenc#sha256"})
        _add(reference, "{http://www.w3.org/2000/09/xmldsig#}DigestValue", base64.b64encode(digest).decode("ascii"))
        _add(signature_node, "{http://www.w3.org/2000/09/xmldsig#}SignatureValue", base64.b64encode(signature).decode("ascii"))
        key_info = ET.SubElement(signature_node, "{http://www.w3.org/2000/09/xmldsig#}KeyInfo")
        x509_data = ET.SubElement(key_info, "{http://www.w3.org/2000/09/xmldsig#}X509Data")
        _add(x509_data, "{http://www.w3.org/2000/09/xmldsig#}X509Certificate", base64.b64encode(cert_der).decode("ascii"))
        return GeneradorXML._pretty_xml(root)

    @staticmethod
    def _decrypt_pkcs12(certificado_encriptado: str, clave_encriptada: str) -> Tuple[bytes, bytes]:
        cert_b64 = decrypt_sensitive_data(certificado_encriptado)
        password = decrypt_sensitive_data(clave_encriptada).encode("utf-8")
        return base64.b64decode(cert_b64), password


class ServicioSRI:
    URLS = {
        "pruebas": {
            "recepcion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
            "autorizacion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
        },
        "produccion": {
            "recepcion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
            "autorizacion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
        },
    }

    def __init__(self, ambiente: str = "produccion", sandbox: bool = False):
        self.ambiente = "produccion" if ambiente == "produccion" else "pruebas"
        self.sandbox = sandbox

    async def enviar_comprobante(self, xml_firmado: str) -> Dict[str, Any]:
        if self.sandbox:
            return {"exito": True, "estado": "RECIBIDA", "mensaje": "Sandbox: envío simulado", "respuesta": ""}
        soap = self._soap_validar(xml_firmado)
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(self.URLS[self.ambiente]["recepcion"], headers={"Content-Type": "text/xml; charset=utf-8"}, content=soap)
        return self._parse_recepcion(response.text, response.status_code)

    async def consultar_autorizacion(self, clave_acceso: str) -> Dict[str, Any]:
        if self.sandbox:
            return {
                "exito": True,
                "estado": "AUTORIZADO",
                "numero_autorizacion": clave_acceso,
                "fecha_autorizacion": datetime.utcnow().isoformat(),
                "mensaje": "Sandbox: autorización simulada",
                "raw_xml": "",
            }
        soap = self._soap_autorizar(clave_acceso)
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(self.URLS[self.ambiente]["autorizacion"], headers={"Content-Type": "text/xml; charset=utf-8"}, content=soap)
        return self._parse_autorizacion(response.text, response.status_code)

    @staticmethod
    def _soap_validar(xml_firmado: str) -> str:
        xml_b64 = base64.b64encode(xml_firmado.encode("utf-8")).decode("ascii")
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ec="http://ec.gob.sri.ws.recepcion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:validarComprobante>
      <xml>{xml_b64}</xml>
    </ec:validarComprobante>
  </soapenv:Body>
</soapenv:Envelope>"""

    @staticmethod
    def _soap_autorizar(clave_acceso: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ec="http://ec.gob.sri.ws.autorizacion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:autorizacionComprobante>
      <claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante>
    </ec:autorizacionComprobante>
  </soapenv:Body>
</soapenv:Envelope>"""

    @staticmethod
    def _parse_recepcion(xml_response: str, status_code: int) -> Dict[str, Any]:
        if status_code >= 400:
            return {"exito": False, "estado": "ERROR_HTTP", "mensaje": f"HTTP {status_code}", "respuesta": xml_response}
        estado = "RECIBIDA" if "RECIBIDA" in xml_response.upper() else "DEVUELTA"
        return {"exito": estado == "RECIBIDA", "estado": estado, "mensaje": estado, "respuesta": xml_response}

    @staticmethod
    def _parse_autorizacion(xml_response: str, status_code: int) -> Dict[str, Any]:
        if status_code >= 400:
            return {"exito": False, "estado": "ERROR_HTTP", "mensaje": f"HTTP {status_code}", "raw_xml": xml_response}
        try:
            root = ET.fromstring(xml_response.encode("utf-8"))
            texts = {node.tag.split("}")[-1]: node.text for node in root.iter() if node.text}
            estado = texts.get("estado", "NO_ENCONTRADO")
            numero = texts.get("numeroAutorizacion")
            fecha = texts.get("fechaAutorizacion")
            mensaje = texts.get("mensaje") or texts.get("informacionAdicional") or estado
            return {
                "exito": estado == "AUTORIZADO",
                "estado": estado,
                "numero_autorizacion": numero,
                "fecha_autorizacion": fecha,
                "mensaje": mensaje,
                "raw_xml": xml_response,
            }
        except ET.ParseError:
            return {"exito": False, "estado": "ERROR_XML", "mensaje": "Respuesta SRI no parseable", "raw_xml": xml_response}


class ConsultaSRI:
    @staticmethod
    async def consultar_ruc(ruc: str) -> Dict[str, Any]:
        if len(ruc) != 13 or not ruc.isdigit():
            return {"valido": False, "error": "RUC inválido"}
        return {
            "valido": True,
            "ruc": ruc,
            "razon_social": f"CONTRIBUYENTE {ruc}",
            "nombre_comercial": f"COMERCIAL {ruc[-4:]}",
            "estado": "ACTIVO",
            "tipo_contribuyente": "No obligado a llevar contabilidad",
            "regimen_tributario": "Régimen General",
            "direccion": "SIN DIRECCION",
        }


class CicloComprobanteSRI:
    @staticmethod
    def generar_xml(comprobante: Any, empresa_config: Any) -> str:
        xml = GeneradorXML.generar(comprobante, empresa_config)
        comprobante.xml_generado = xml
        return xml

    @staticmethod
    def firmar_xml(comprobante: Any, certificado: Any) -> str:
        xml = comprobante.xml_generado or GeneradorXML.generar(comprobante, comprobante.empresa.configuracion_sri)
        firmado = FirmadorXML.firmar(xml, certificado.certificado_encriptado, certificado.clave_encriptada)
        comprobante.xml_firmado = firmado
        comprobante.estado = EstadoComprobanteEnum.FIRMADO
        return firmado
