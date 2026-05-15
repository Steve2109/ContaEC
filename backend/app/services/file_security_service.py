"""
Servicio de escaneo de archivos con ClamAV y VirusTotal
"""
import os
import hashlib
import httpx
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import MalwareScanLog


class ClamAVScanner:
    """
    Escáner de archivos usando ClamAV
    """
    
    def __init__(self):
        self.enabled = settings.CLAMAV_ENABLED
        self.socket_path = settings.CLAMAV_SOCKET
    
    def scan_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Escanea un archivo con ClamAV
        Retorna (es_limpio, nombre_de_amenaza)
        """
        if not self.enabled:
            return True, None
        
        if not os.path.exists(file_path):
            return False, "Archivo no encontrado"
        
        try:
            # Intentar usar clamd (daemon) para mejor rendimiento
            result = self._scan_with_clamd(file_path)
            if result is not None:
                return result
            
            # Fallback a clamscan
            return self._scan_with_clamscan(file_path)
            
        except Exception as e:
            # Si falla el escaneo, considerar como sospechoso
            return False, f"Error en escaneo: {str(e)}"
    
    def _scan_with_clamd(self, file_path: str) -> Optional[Tuple[bool, Optional[str]]]:
        """
        Escanea usando clamd (daemon)
        """
        try:
            import socket
            
            # Conectar al socket de clamd
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(self.socket_path)
            
            # Enviar comando de escaneo
            command = f"zSCAN {file_path}\n".encode()
            client.sendall(command)
            
            # Recibir respuesta
            response = b""
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"\n" in response:
                    break
            
            client.close()
            
            response_str = response.decode().strip()
            
            # Parsear respuesta
            if "OK" in response_str:
                return True, None
            elif ":" in response_str:
                # Formato: file_path: threat_name FOUND
                parts = response_str.split(":")
                if len(parts) >= 2:
                    threat = parts[1].strip().replace(" FOUND", "")
                    return False, threat
            
            return True, None
            
        except Exception:
            return None  # Indica que debe usar fallback
    
    def _scan_with_clamscan(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Escanea usando clamscan (comando directo)
        """
        import subprocess
        
        try:
            result = subprocess.run(
                ["clamscan", "--no-summary", file_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            output = result.stdout + result.stderr
            
            if "OK" in output:
                return True, None
            elif "FOUND" in output:
                # Extraer nombre de amenaza
                for line in output.split("\n"):
                    if "FOUND" in line and ":" in line:
                        threat = line.split(":")[1].strip().replace(" FOUND", "")
                        return False, threat
            
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "Timeout en escaneo"
        except Exception as e:
            return False, f"Error: {str(e)}"


class VirusTotalScanner:
    """
    Escáner opcional usando VirusTotal API
    Solo se usa si el usuario lo activa explícitamente
    """
    
    def __init__(self):
        self.api_key = settings.VIRUSTOTAL_API_KEY
        self.base_url = "https://www.virustotal.com/api/v3"
    
    def is_available(self) -> bool:
        """Verifica si VirusTotal está configurado"""
        return bool(self.api_key)
    
    async def scan_file_hash(self, file_path: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Escanea el hash de un archivo en VirusTotal
        Retorna (es_limpio, amenaza, detectaciones)
        """
        if not self.is_available():
            return True, None, 0
        
        try:
            # Calcular hash SHA256 del archivo
            file_hash = self._calculate_sha256(file_path)
            
            async with httpx.AsyncClient() as client:
                headers = {
                    "x-apikey": self.api_key
                }
                
                # Consultar por el hash
                response = await client.get(
                    f"{self.base_url}/files/{file_hash}",
                    headers=headers
                )
                
                if response.status_code == 404:
                    # Archivo no analizado previamente
                    # Se podría subir para análisis, pero eso es más complejo
                    return True, None, 0
                
                data = response.json()
                stats = data["data"]["attributes"]["last_analysis_stats"]
                
                malicious = stats.get("malicious", 0)
                suspicious = stats.get("suspicious", 0)
                
                if malicious > 0 or suspicious > 0:
                    # Obtener nombre de amenaza
                    results = data["data"]["attributes"]["last_analysis_results"]
                    threat_name = None
                    for vendor, result in results.items():
                        if result["category"] in ["malicious", "suspicious"]:
                            threat_name = result["result"]
                            if threat_name:
                                break
                    
                    return False, threat_name, malicious + suspicious
                
                return True, None, 0
                
        except Exception as e:
            # Si falla VT, no bloquear el flujo principal
            return True, None, 0
    
    def _calculate_sha256(self, file_path: str) -> str:
        """Calcula hash SHA256 de un archivo"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


class FileSecurityService:
    """
    Servicio principal para seguridad de archivos
    Combina ClamAV (obligatorio) y VirusTotal (opcional)
    """
    
    def __init__(self):
        self.clamav = ClamAVScanner()
        self.virustotal = VirusTotalScanner()
    
    def scan_file(
        self,
        db: Session,
        file_path: str,
        file_name: str,
        user_id: Optional[int] = None,
        use_virustotal: bool = False
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Escanea un archivo completo
        Retorna (es_seguro, mensaje, nombre_amenaza)
        """
        # Calcular hash para logging
        file_hash = hashlib.sha256(open(file_path, "rb").read()).hexdigest()
        
        # 1. Escanear con ClamAV (siempre)
        is_clean, threat = self.clamav.scan_file(file_path)
        
        if not is_clean:
            # Log de malware detectado
            self._log_scan(
                db=db,
                user_id=user_id,
                file_name=file_name,
                file_path=file_path,
                file_hash=file_hash,
                result="INFECTED",
                scanner="CLAMAV",
                threat_name=threat
            )
            
            # Eliminar archivo infectado
            try:
                os.remove(file_path)
            except:
                pass
            
            return False, f"El archivo contiene malware: {threat}", threat
        
        # 2. Escanear con VirusTotal (opcional, solo si se solicita)
        if use_virustotal and self.virustotal.is_available():
            import asyncio
            is_clean, vt_threat, detections = asyncio.run(
                self.virustotal.scan_file_hash(file_path)
            )
            
            if not is_clean:
                self._log_scan(
                    db=db,
                    user_id=user_id,
                    file_name=file_name,
                    file_path=file_path,
                    file_hash=file_hash,
                    result="SUSPICIOUS",
                    scanner="VIRUSTOTAL",
                    threat_name=vt_threat
                )
                
                return False, f"VirusTotal detectó amenazas: {vt_threat}", vt_threat
        
        # 3. Archivo limpio
        self._log_scan(
            db=db,
            user_id=user_id,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            result="CLEAN",
            scanner="CLAMAV",
            threat_name=None
        )
        
        return True, "Archivo limpio", None
    
    def _log_scan(
        self,
        db: Session,
        user_id: Optional[int],
        file_name: str,
        file_path: str,
        file_hash: str,
        result: str,
        scanner: str,
        threat_name: Optional[str]
    ):
        """Registra el escaneo en la base de datos"""
        log = MalwareScanLog(
            user_id=user_id,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            scan_result=result,
            scanner=scanner,
            threat_name=threat_name
        )
        db.add(log)
        db.commit()
