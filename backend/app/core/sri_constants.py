"""
Constantes Oficiales SRI - Ecuador
Documento: FICHA_TECNICA.pdf
Implementación completa de códigos para facturación electrónica.
"""

# Tipos de IVA según SRI (Actualizado con todos los códigos oficiales)
IVA_CODES = {
    "0": {"code": "0", "name": "IVA 0%", "value": 0.00},
    "5": {"code": "5", "name": "IVA 5%", "value": 0.05},
    "8": {"code": "8", "name": "IVA 8%", "value": 0.08},
    "12": {"code": "2", "name": "IVA 12%", "value": 0.12},
    "13": {"code": "10", "name": "IVA 13%", "value": 0.13},
    "14": {"code": "3", "name": "IVA 14%", "value": 0.14},
    "15": {"code": "4", "name": "IVA 15% (Default)", "value": 0.15, "default": True},
    "NO_OBJETO": {"code": "6", "name": "No objeto de impuesto", "value": 0.00},
    "EXENTO": {"code": "7", "name": "Exento de IVA", "value": 0.00},
    "DIFERENCIADO": {"code": "8", "name": "IVA diferenciado", "value": 0.00},
}

DEFAULT_IVA = "15"

# Tarifas ICE (Impuesto a los Consumos Especiales) - Completar según FICHA_TECNICA.pdf
ICE_CODES = {
    "0": {"code": "0", "name": "Sin ICE", "value": 0.00},
    "ALCOHOLICOS": {"code": "1", "name": "Bebidas Alcohólicas", "value": 0.35},
    "CIGARRILLOS": {"code": "2", "name": "Tabacos", "value": 0.55},
    "VEHICULOS": {"code": "3", "name": "Vehículos (según cilindrada)", "value": 0.00},
    "TELEFONIA": {"code": "4", "name": "Servicios de telefonía", "value": 0.05},
    "BEBIDAS_AZUCARADAS": {"code": "5", "name": "Bebidas Azucaradas", "value": 0.18},
}

# Porcentajes de Retención en la Fuente (IR)
RETENTION_IR_CODES = {
    "0": {"code": "0", "name": "0%", "value": 0.00},
    "10": {"code": "1", "name": "10%", "value": 0.10},
    "20": {"code": "2", "name": "20%", "value": 0.20},
    "30": {"code": "3", "name": "30%", "value": 0.30},
    "50": {"code": "4", "name": "50%", "value": 0.50},
    "70": {"code": "5", "name": "70%", "value": 0.70},
    "100": {"code": "6", "name": "100%", "value": 1.00},
}

# Porcentajes de Retención de IVA
RETENTION_IVA_CODES = {
    "30": {"code": "1", "name": "30%", "value": 0.30},
    "50": {"code": "2", "name": "50%", "value": 0.50},
    "70": {"code": "3", "name": "70%", "value": 0.70},
    "100": {"code": "4", "name": "100%", "value": 1.00},
}

# Tipos de Contribuyente (Actualizado)
CONTRIBUTOR_TYPES = {
    "01": "Obligado a llevar contabilidad",
    "02": "No obligado a llevar contabilidad",
    "03": "Consumidor Final", # Default
    "04": "RIMPE Emprendedor",
    "05": "RIMPE Negocio Popular",
    "06": "Agente de Retención",
    "07": "Contribuyente Especial",
    "08": "Sociedad",
    "09": "Persona Natural",
}

# Regímenes Tributarios (Actualizado)
TAX_REGIMES = {
    "GENERAL": "Régimen General",
    "RIMPE_EMPRENDEDOR": "RIMPE - Emprendedor",
    "RIMPE_POPULAR": "RIMPE - Negocio Popular",
    "MICROEMPRESA": "Régimen Microempresa",
    "POPULAR": "Régimen Popular",
}

# Tipos de Comprobantes Electrónicos
DOCUMENT_TYPES = {
    "01": "Factura",
    "04": "Nota de Crédito",
    "05": "Nota de Débito",
    "06": "Guía de Remisión",
    "07": "Comprobante de Retención",
    "99": "Proforma (No tributario)",
}

# Estados del Comprobante Electrónico (Actualizado)
DOCUMENT_STATUS = {
    "BORRADOR": "Borrador",
    "FIRMADO": "Firmado Electrónicamente",
    "ENVIADO_SRI": "Enviado al SRI",
    "AUTORIZADO": "Autorizado por SRI",
    "RECHAZADO": "Rechazado por SRI",
    "ANULADO": "Anulado",
    "NO_ENCONTRADO": "No encontrado en SRI",
    "ERROR_XML": "Error en estructura XML",
}

# Cliente por defecto (Consumidor Final)
CONSUMIDOR_FINAL = {
    "ruc": "9999999999999",
    "nombre": "CONSUMIDOR FINAL",
    "tipo_contribuyente": "03",
    "regimen": "RIMPE_POPULAR",
    "direccion": "CIUDAD Y CANTÓN",
    "email": "",
}

# Códigos de Error SRI (Comunes)
SRI_ERROR_CODES = {
    "403": "Certificado revocado o caducado",
    "404": "RUC no encontrado",
    "500": "Error interno SRI",
    "600": "Errores en estructura XML",
}
