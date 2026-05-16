"""
Servicio de consulta al SRI Ecuador.
Reemplaza el stub de consulta RUC por una implementación HTTP real.
"""

import httpx
from typing import Dict, Any, Optional
from fastapi import HTTPException
from app.core.config import get_settings


class ConsultaSRI:
    """
    Consulta de contribuyentes al web service del SRI Ecuador.
    Usa el endpoint REST público de Catastro de Sujetos.
    """

    HEADERS = {
        "Accept": "application/json",
        "User-Agent": "ContaEC/1.0 (T&M Technology Ec)",
    }

    @staticmethod
    async def consultar_ruc(ruc: str) -> Dict[str, Any]:
        """
        Consulta un RUC en el SRI Ecuador.
        Retorna datos reales del contribuyente si existe.
        """
        settings = get_settings()
        ruc_limpio = str(ruc).strip()

        # Validación básica de RUC ecuatoriano
        if not ruc_limpio or len(ruc_limpio) not in (10, 13):
            raise HTTPException(
                status_code=400,
                detail="RUC inválido. Debe tener 10 (cédula) o 13 dígitos (RUC)."
            )

        url = f"{settings.SRI_CONSULTA_RUC_URL}?numeroRuc={ruc_limpio}"

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=ConsultaSRI.HEADERS) as client:
                response = await client.get(url)

                # El SRI a veces retorna 200 incluso si no existe,
                # con un JSON que indica si existe o no.
                if response.status_code == 200:
                    data = response.json()

                    # El endpoint existePorNumeroRuc retorna un booleano o un objeto
                    if isinstance(data, bool):
                        if not data:
                            return {
                                "valido": False,
                                "ruc": ruc_limpio,
                                "mensaje": "RUC no encontrado en el SRI."
                            }
                        # Si retorna True, necesitamos consultar más detalles
                        return await ConsultaSRI._consultar_detalle_ruc(ruc_limpio)

                    if isinstance(data, dict):
                        if data.get("existe", False) or "razonSocial" in data or "nombreCompleto" in data:
                            return ConsultaSRI._normalizar_respuesta(data, ruc_limpio)
                        return {
                            "valido": False,
                            "ruc": ruc_limpio,
                            "mensaje": "RUC no encontrado en el SRI.",
                            "respuesta_raw": data,
                        }

                # Si el SRI está caído o cambió el endpoint
                if response.status_code in (404, 500, 503):
                    return {
                        "valido": False,
                        "ruc": ruc_limpio,
                        "mensaje": f"Servicio del SRI no disponible (HTTP {response.status_code}). Intente más tarde.",
                    }

                response.raise_for_status()
                data = response.json()
                return ConsultaSRI._normalizar_respuesta(data, ruc_limpio)

        except httpx.TimeoutException:
            return {
                "valido": False,
                "ruc": ruc_limpio,
                "mensaje": "Tiempo de espera agotado al consultar el SRI. El servicio puede estar lento."
            }
        except httpx.ConnectError:
            return {
                "valido": False,
                "ruc": ruc_limpio,
                "mensaje": "No se pudo conectar al SRI. Verifique la conexión a Internet."
            }
        except httpx.HTTPStatusError as exc:
            return {
                "valido": False,
                "ruc": ruc_limpio,
                "mensaje": f"Error HTTP al consultar SRI: {exc.response.status_code}.",
            }
        except Exception as exc:
            return {
                "valido": False,
                "ruc": ruc_limpio,
                "mensaje": f"Error inesperado al consultar SRI: {str(exc)}",
            }

    @staticmethod
    async def _consultar_detalle_ruc(ruc: str) -> Dict[str, Any]:
        """
        Fallback: consulta el endpoint alternativo de detalle por RUC.
        """
        settings = get_settings()
        url = f"https://srienlinea.sri.gob.ec/sri-catastro-sujeto-servicio-internet/rest/ConsolidadoContribuyente/obtenerPorNumerosRuc?numeroRuc={ruc}"

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=ConsultaSRI.HEADERS) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return ConsultaSRI._normalizar_respuesta(data, ruc)
        except Exception:
            # Si también falla, retornar un objeto básico marcado como válido
            # pero con campos vacíos para que el usuario los llene manualmente
            return {
                "valido": True,
                "ruc": ruc,
                "razon_social": "",
                "nombre_comercial": "",
                "direccion": "",
                "telefono": "",
                "email": "",
                "obligado_contabilidad": False,
                "contribuyente_especial": "NO",
                "tipo_contribuyente": "PERSONA_NATURAL",
                "estado": "ACTIVO",
                "mensaje": "RUC válido pero no se pudo obtener detalles del SRI.",
            }

    @staticmethod
    def _normalizar_respuesta(data: Dict[str, Any], ruc: str) -> Dict[str, Any]:
        """
        Normaliza la respuesta del SRI a un formato uniforme para ContaEC.
        El SRI puede retornar diferentes estructuras según el endpoint.
        """
        # Estructura típica de obtenerPorNumerosRuc
        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        razon_social = (
            data.get("razonSocial")
            or data.get("nombreCompleto")
            or data.get("nombreCompletoPrimero")
            or data.get("razonSocialPrimero")
            or ""
        )
        nombre_comercial = (
            data.get("nombreComercial")
            or data.get("nombreFantasiaComercial")
            or razon_social
            or ""
        )
        direccion = (
            data.get("direccionCompleta")
            or data.get("calle")
            or ""
        )
        if not direccion and data.get("interseccion"):
            direccion = f"{data.get('calle', '')} y {data.get('interseccion', '')}"

        estado = data.get("estadoContribuyente", "ACTIVO")
        obligado = data.get("obligadoContabilidad", "NO")
        contribuyente_especial = data.get("contribuyenteEspecial", "NO")

        # Determinar tipo de contribuyente
        tipo = "PERSONA_NATURAL" if len(ruc) == 10 else "PERSONA_JURIDICA"
        if data.get("esRIMPE", False) or data.get("regimenRIMPE"):
            tipo = "RIMPE_EMPRENDEDOR"

        return {
            "valido": True,
            "ruc": ruc,
            "razon_social": razon_social.strip(),
            "nombre_comercial": nombre_comercial.strip(),
            "direccion": direccion.strip(),
            "telefono": (data.get("telefonoDomicilio") or data.get("telefonoTrabajo") or "").strip(),
            "email": (data.get("correo") or data.get("email") or "").strip().lower(),
            "obligado_contabilidad": str(obligado).upper() in ("SI", "SÍ", "YES", "TRUE"),
            "contribuyente_especial": str(contribuyente_especial).upper(),
            "tipo_contribuyente": tipo,
            "estado": str(estado).upper(),
            "canton": (data.get("canton") or "").strip(),
            "provincia": (data.get("provincia") or "").strip(),
            "actividad_economica": (data.get("actividadEconomica") or data.get("actividadEconomicaPrincipal") or "").strip(),
            "mensaje": "RUC consultado exitosamente en el SRI.",
            "fuente": "SRI",
        }
