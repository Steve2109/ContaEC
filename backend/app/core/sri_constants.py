"""
Constantes Oficiales SRI - Ecuador
Documento: FICHA_TECNICA.pdf
Implementación completa de códigos para facturación electrónica.
"""

# Tipos de IVA según SRI
IVA_CODES = {
    "0": {"code": "0", "name": "IVA 0%", "value": 0.00},
    "5": {"code": "5", "name": "IVA 5%", "value": 0.05},
    "8": {"code": "8", "name": "IVA 8%", "value": 0.08},
    "12": {"code": "12", "name": "IVA 12%", "value": 0.12},
    "13": {"code": "13", "name": "IVA 13%", "value": 0.13},
    "14": {"code": "14", "name": "IVA 14%", "value": 0.14},
    "15": {"code": "15", "name": "IVA 15% (Default)", "value": 0.15},
    "NO_OBJETO": {"code": "6", "name": "No objeto de impuesto", "value": 0.00},
    "EXENTO": {"code": "7", "name": "Exento de IVA", "value": 0.00},
    "DIFERENCIADO": {"code": "8", "name": "IVA diferenciado", "value": 0.00}, # Para bienes de la canasta básica
}

DEFAULT_IVA = "15"

# Tarifas ICE (Impuesto a los Consumos Especiales) - Ejemplos comunes
ICE_CODES = {
    "0": {"code": "0", "name": "Sin ICE", "value": 0.00},
    "ALCOHOLICOS": {"code": "1", "name": "Bebidas Alcohólicas", "value": 0.35}, # Valor referencial %
    "CIGARRILLOS": {"code": "2", "name": "Tabacos", "value": 0.55},
    "VEHICULOS": {"code": "3", "name": "Vehículos (según cilindrada)", "value": 0.00}, # Variable
    "TELEFONIA": {"code": "4", "name": "Servicios de telefonía", "value": 0.05},
}

# Porcentajes de Retención en la Fuente
RETENTION_CODES = {
    "0": {"code": "0", "name": "0%", "value": 0.00},
    "10": {"code": "1", "name": "10%", "value": 0.10},
    "20": {"code": "2", "name": "20%", "value": 0.20},
    "30": {"code": "3", "name": "30%", "value": 0.30},
    "50": {"code": "4", "name": "50%", "value": 0.50},
    "70": {"code": "5", "name": "70%", "value": 0.70},
    "100": {"code": "6", "name": "100%", "value": 1.00},
}

# Tipos de Contribuyente
CONTRIBUTOR_TYPES = {
    "01": "Obligado a llevar contabilidad",
    "02": "No obligado a llevar contabilidad",
    "03": "Consumidor Final", # Default
    "04": "RIMPE Emprendedor",
    "05": "RIMPE Negocio Popular",
    "06": "Agente de Retención",
    "07": "Contribuyente Especial",
}

# Regímenes Tributarios
TAX_REGIMES = {
    "GENERAL": "Régimen General",
    "RIMPE_EMPRENDEDOR": "RIMPE - Emprendedor",
    "RIMPE_POPULAR": "RIMPE - Negocio Popular",
    "MICROEMPRESA": "Régimen Microempresa",
}

# Tipos de Comprobantes Electrónicos
DOCUMENT_TYPES = {
    "01": "Factura",
    "02": "Nota de Débito",
    "03": "Nota de Crédito",
    "04": "Retención",
    "05": "Guía de Remisión",
    "06": "Ticket de Venta (Autorizado)",
    "07": "Proforma (No tributario)",
}

# Estados del Comprobante Electrónico
DOCUMENT_STATUS = {
    "BORRADOR": "Borrador",
    "FIRMADO": "Firmado Electrónicamente",
    "ENVIADO_SRI": "Enviado al SRI",
    "AUTORIZADO": "Autorizado por SRI",
    "RECHAZADO": "Rechazado por SRI",
    "ANULADO": "Anulado",
}

# Códigos de Error SRI (Comunes)
SRI_ERROR_CODES = {
    "403": "Certificado revocado o caducado",
    "404": "RUC no encontrado",
    "500": "Error interno SRI",
    "600": "Errores en estructura XML",
}
