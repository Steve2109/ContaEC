"""
Constantes y catálogos del SRI Ecuador para Facturación Electrónica.
Completado: Grupos ICE (~30+), Retención IVA (todos los códigos SRI).
"""

from typing import Dict, Any

# ───────────────────────────────────────────────
# IVA
# ───────────────────────────────────────────────
IVA_CODES: Dict[str, Dict[str, Any]] = {
    "0": {"code": "0", "name": "0%", "value": 0.00},
    "5": {"code": "5", "name": "5%", "value": 0.05},
    "8": {"code": "8", "name": "8%", "value": 0.08},
    "12": {"code": "2", "name": "12%", "value": 0.12},
    "13": {"code": "3", "name": "13%", "value": 0.13},
    "14": {"code": "4", "name": "14%", "value": 0.14},
    "15": {"code": "5", "name": "15% (default)", "value": 0.15},
    "NO_OBJETO": {"code": "6", "name": "No Objeto de Impuesto", "value": 0.00},
    "EXENTO": {"code": "7", "name": "Exento de IVA", "value": 0.00},
    "DIFERENCIADO": {"code": "8", "name": "IVA Diferenciado", "value": None},
}

# ───────────────────────────────────────────────
# ICE — Impuesto a los Consumos Especiales
# Tabla completa según SRI (códigos de tarifa especial)
# ───────────────────────────────────────────────
ICE_CODES: Dict[str, Dict[str, Any]] = {
    "0": {"code": "0", "name": "Sin ICE", "value": 0.00, "group": "N/A"},
    # Bebidas alcohólicas y cerveza
    "3011": {"code": "3011", "name": "Bebidas alcohólicas (general)", "value": 0.35, "group": "ALCOHOLICAS"},
    "3021": {"code": "3021", "name": "Cerveza artesanal", "value": 0.10, "group": "ALCOHOLICAS"},
    "3023": {"code": "3023", "name": "Bebidas alcohólicas < grado determinado", "value": 0.25, "group": "ALCOHOLICAS"},
    # Tabacos
    "3041": {"code": "3041", "name": "Tabacos y cigarrillos", "value": 0.55, "group": "TABACOS"},
    # Vehículos
    "3051": {"code": "3051", "name": "Vehículos > $20.000 y <= $30.000", "value": 0.05, "group": "VEHICULOS"},
    "3052": {"code": "3052", "name": "Vehículos > $30.000 y <= $40.000", "value": 0.10, "group": "VEHICULOS"},
    "3053": {"code": "3053", "name": "Vehículos > $40.000 y <= $50.000", "value": 0.15, "group": "VEHICULOS"},
    "3054": {"code": "3054", "name": "Vehículos > $50.000 y <= $60.000", "value": 0.20, "group": "VEHICULOS"},
    "3055": {"code": "3055", "name": "Vehículos > $60.000 y <= $70.000", "value": 0.25, "group": "VEHICULOS"},
    "3056": {"code": "3056", "name": "Vehículos > $70.000", "value": 0.30, "group": "VEHICULOS"},
    # Perfumes, cosméticos, aguas de tocador
    "3071": {"code": "3071", "name": "Perfumes", "value": 0.20, "group": "COSMETICOS"},
    "3072": {"code": "3072", "name": "Agua de tocador", "value": 0.20, "group": "COSMETICOS"},
    "3073": {"code": "3073", "name": "Cosméticos", "value": 0.15, "group": "COSMETICOS"},
    "3074": {"code": "3074", "name": "Aceites/jabones para baño/lociones capilares", "value": 0.15, "group": "COSMETICOS"},
    # Videojuegos
    "3081": {"code": "3081", "name": "Videoconsolas y juegos", "value": 0.05, "group": "ENTRETENIMIENTO"},
    # Armas
    "3091": {"code": "3091", "name": "Armas de fuego (defensa/personal)", "value": 0.30, "group": "ARMAS"},
    "3092": {"code": "3092", "name": "Armas deportivas", "value": 0.15, "group": "ARMAS"},
    # Combustibles e hidrocarburos
    "3101": {"code": "3101", "name": "Jet fuel (combustible aviación)", "value": 0.10, "group": "COMBUSTIBLES"},
    "3102": {"code": "3102", "name": "Servicio transporte aéreo internacional", "value": 0.05, "group": "TRANSPORTE"},
    "3103": {"code": "3103", "name": "Servicio transporte aéreo nacional", "value": 0.05, "group": "TRANSPORTE"},
    "3104": {"code": "3104", "name": "Combustibles derivados petróleo (excepto gasolina)", "value": 0.10, "group": "COMBUSTIBLES"},
    "3111": {"code": "3111", "name": "Hidrocarburos (general)", "value": 0.10, "group": "HIDROCARBUROS"},
    "3112": {"code": "3112", "name": "Hidrocarburos no renovables (extra)", "value": 0.15, "group": "HIDROCARBUROS"},
    # Bolsas plásticas
    "3121": {"code": "3121", "name": "Bolsas plásticas (régimen general)", "value": 0.02, "group": "PLASTICOS"},
    "3122": {"code": "3122", "name": "Bolsas plásticas (régimen simplificado)", "value": 0.01, "group": "PLASTICOS"},
    # Bebidas azucaradas / Alimentos procesados
    "3151": {"code": "3151", "name": "Bebidas no alcohólicas con azúcar", "value": 0.18, "group": "BEBIDAS_AZUCARADAS"},
    "3152": {"code": "3152", "name": "Alimentos con alto contenido de azúcar", "value": 0.10, "group": "ALIMENTOS_PROCESADOS"},
    "3153": {"code": "3153", "name": "Alimentos con alto contenido de sal", "value": 0.05, "group": "ALIMENTOS_PROCESADOS"},
    "3154": {"code": "3154", "name": "Alimentos con alto contenido de grasas saturadas", "value": 0.05, "group": "ALIMENTOS_PROCESADOS"},
    # Telefonía (legacy, aún usado en ciertos casos)
    "3010": {"code": "3010", "name": "Servicios de telefonía", "value": 0.15, "group": "TELEFONIA"},
}

# ───────────────────────────────────────────────
# Retención en la Fuente — Impuesto a la Renta
# ───────────────────────────────────────────────
RETENTION_IR_CODES: Dict[str, Dict[str, Any]] = {
    "0": {"code": "0", "name": "0%", "value": 0.00},
    "10": {"code": "1", "name": "10%", "value": 0.10},
    "20": {"code": "2", "name": "20%", "value": 0.20},
    "30": {"code": "3", "name": "30%", "value": 0.30},
    "50": {"code": "4", "name": "50%", "value": 0.50},
    "70": {"code": "5", "name": "70%", "value": 0.70},
    "100": {"code": "6", "name": "100%", "value": 1.00},
}

# ───────────────────────────────────────────────
# Retención en la Fuente — IVA
# Todos los códigos SRI según normativa vigente
# ───────────────────────────────────────────────
RETENTION_IVA_CODES: Dict[str, Dict[str, Any]] = {
    "0": {"code": "0", "name": "0%", "value": 0.00},
    "10": {"code": "1", "name": "10%", "value": 0.10},
    "20": {"code": "2", "name": "20%", "value": 0.20},
    "30": {"code": "3", "name": "30%", "value": 0.30},
    "50": {"code": "4", "name": "50%", "value": 0.50},
    "70": {"code": "5", "name": "70%", "value": 0.70},
    "100": {"code": "6", "name": "100%", "value": 1.00},
    # Adicionales según normativa SRI
    "2": {"code": "7", "name": "2%", "value": 0.02},
    "15": {"code": "8", "name": "15%", "value": 0.15},
}

# ───────────────────────────────────────────────
# Tipos de Comprobante
# ───────────────────────────────────────────────
DOCUMENT_TYPES: Dict[str, str] = {
    "01": "Factura",
    "03": "Liquidación de Compras",
    "04": "Nota de Crédito",
    "05": "Nota de Débito",
    "06": "Guía de Remisión",
    "07": "Comprobante de Retención",
    "08": "Boleta de Depósito",
    "09": "Boletos de Espectáculos",
    "11": "Pasajes emitidos por líneas aéreas",
    "12": "Documentos emitidos por instituciones financieras",
    "15": "Comprobante de venta",
    "16": "Comprobante de líneas aéreas (ticket)",
    "20": "Documentos emitidos por AF/ILE",
    "21": "Carta Porte",
    "41": "Comprobante de reembolso",
    "47": "Nota de Crédito por reembolso",
    "48": "Nota de Débito por reembolso",
}

# ───────────────────────────────────────────────
# Estados del Comprobante
# ───────────────────────────────────────────────
COMPROBANTE_STATES: Dict[str, str] = {
    "BORRADOR": "Borrador",
    "FIRMADO": "Firmado",
    "ENVIADO": "Enviado",
    "AUTORIZADO": "Autorizado",
    "RECHAZADO": "Rechazado",
    "ANULADO": "Anulado",
    "ERROR_XML": "Error XML",
    "NO_ENVIADO": "No Enviado",
}

# ───────────────────────────────────────────────
# Tipos de Contribuyente / Regímenes
# ───────────────────────────────────────────────
CONTRIBUYENTE_TYPES: Dict[str, str] = {
    "RIMPE_EMPRENDEDOR": "RIMPE Emprendedor",
    "RIMPE_POPULAR": "RIMPE Popular",
    "RIMPE_ESPECIAL": "RIMPE Especial",
    "GENERAL": "Régimen General",
    "CONTRIBUYENTE_ESPECIAL": "Contribuyente Especial",
    "SECTOR_PUBLICO": "Sector Público",
    "ONG": "Organización No Gubernamental",
    "PERSONA_NATURAL": "Persona Natural",
    "PERSONA_JURIDICA": "Persona Jurídica",
}

TAX_REGIMES: Dict[str, str] = {
    "GENERAL": "Régimen General",
    "RIMPE": "Régimen RIMPE",
    "SECTOR_PUBLICO": "Sector Público",
    "EXTERIOR": "Exterior",
    "OTROS": "Otros",
}

# ───────────────────────────────────────────────
# Consumidor Final (RUC por defecto)
# ───────────────────────────────────────────────
CONSUMIDOR_FINAL_RUC: str = "9999999999999"
CONSUMIDOR_FINAL_NAME: str = "CONSUMIDOR FINAL"

# ───────────────────────────────────────────────
# Formas de Pago
# ───────────────────────────────────────────────
PAYMENT_METHODS: Dict[str, str] = {
    "01": "SIN UTILIZACION DEL SISTEMA FINANCIERO",
    "15": "COMPENSACIÓN DE DEUDAS",
    "16": "TARJETA DE DÉBITO",
    "17": "DINERO ELECTRÓNICO",
    "18": "TARJETA PREPAGO",
    "19": "TARJETA DE CRÉDITO",
    "20": "OTROS CON UTILIZACIÓN DEL SISTEMA FINANCIERO",
    "21": "ENDOSO DE TÍTULOS",
}

# ───────────────────────────────────────────────
# Tarifas IVA para exportación / otros
# ───────────────────────────────────────────────
IVA_EXPORTACION: Dict[str, Any] = {
    "code": "0",
    "name": "IVA 0% (Exportación)",
    "value": 0.00,
}

# ───────────────────────────────────────────────
# Ambiente SRI
# ───────────────────────────────────────────────
SRI_AMBIENTE_PRUEBAS: int = 1
SRI_AMBIENTE_PRODUCCION: int = 2

# ───────────────────────────────────────────────
# Emisión
# ───────────────────────────────────────────────
SRI_EMISION_NORMAL: str = "1"
SRI_EMISION_INDISPONIBILIDAD: str = "2"
