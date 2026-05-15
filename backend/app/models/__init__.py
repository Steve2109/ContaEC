"""
Modelos de base de datos para ContaEC
Fase 1-3: Usuarios, Empresas, Licencias, Configuración + Facturación Electrónica
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    """Roles de usuario"""
    ADMIN = "admin"
    USER = "user"
    ACCOUNTANT = "accountant"


class LicenseType(str, enum.Enum):
    """Tipos de licencia"""
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"


class User(Base):
    """
    Tabla de usuarios del sistema
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relaciones
    companies = relationship("Company", back_populates="owner", cascade="all, delete-orphan")
    user_companies = relationship("UserCompany", back_populates="user", cascade="all, delete-orphan")
    license = relationship("License", back_populates="user", uselist=False, cascade="all, delete-orphan")
    configurations = relationship("UserConfiguration", back_populates="user", uselist=False, cascade="all, delete-orphan")
    categorias_inventario = relationship("CategoriaProducto", back_populates="empresa", cascade="all, delete-orphan")
    productos_inventario = relationship("Producto", back_populates="empresa", cascade="all, delete-orphan")
    almacenes = relationship("Almacen", back_populates="empresa", cascade="all, delete-orphan")
    clientes = relationship("Cliente", back_populates="empresa", cascade="all, delete-orphan")
    productos_servicios = relationship("ProductoServicio", back_populates="empresa", cascade="all, delete-orphan")
    comprobantes = relationship("ComprobanteElectronico", back_populates="empresa", cascade="all, delete-orphan")


class Company(Base):
    """
    Tabla de empresas (multiempresa)
    """
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    ruc = Column(String(13), unique=True, index=True, nullable=False)
    business_name = Column(String(255), nullable=False)
    trade_name = Column(String(255))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    logo_path = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    owner = relationship("User", back_populates="companies")
    user_companies = relationship("UserCompany", back_populates="company", cascade="all, delete-orphan")
    configurations = relationship("CompanyConfiguration", back_populates="company", uselist=False, cascade="all, delete-orphan")


class UserCompany(Base):
    """
    Tabla intermedia para relación muchos-a-muchos entre usuarios y empresas
    Permite que un usuario maneje múltiples empresas
    """
    __tablename__ = "user_companies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    user = relationship("User", back_populates="user_companies")
    company = relationship("Company", back_populates="user_companies")


class License(Base):
    """
    Tabla de licenciamiento de usuarios
    """
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    license_type = Column(SQLEnum(LicenseType), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    payment_reference = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación
    user = relationship("User", back_populates="license")


class UserConfiguration(Base):
    """
    Tabla para guardar configuración encriptada de cada usuario
    Aquí se almacenan: firma electrónica, clave de firma, SMTP, clave de backup
    """
    __tablename__ = "user_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Datos encriptados
    encrypted_firma_electronica = Column(Text)  # Ruta o contenido de firma encriptada
    encrypted_firma_clave = Column(Text)  # Clave de firma encriptada
    firma_validity = Column(DateTime(timezone=True))  # Fecha de validez de la firma
    
    # Configuración SMTP encriptada
    encrypted_smtp_config = Column(JSON)  # {host, port, user, password, etc.}
    
    # Clave de backup encriptada
    encrypted_backup_key = Column(Text)
    
    # Preferencias
    language = Column(String(10), default="es_EC")
    theme = Column(String(20), default="light")
    
    # Modo sandbox/pruebas
    is_sandbox_mode = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación
    user = relationship("User", back_populates="configurations")


class CompanyConfiguration(Base):
    """
    Configuración específica de cada empresa
    """
    __tablename__ = "company_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), unique=True, nullable=False)
    
    # Datos del SRI
    contributor_type = Column(String(100))  # Tipo de contribuyente
    regime = Column(String(100))  # Régimen tributario
    
    # Configuración contable
    accounting_enabled = Column(Boolean, default=True)
    inventory_enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación
    company = relationship("Company", back_populates="configurations")


class SecurityLog(Base):
    """
    Logs de seguridad para auditoría
    """
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(255), nullable=False)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    details = Column(JSON)
    is_suspicious = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MalwareScanLog(Base):
    """
    Logs de escaneo de archivos con ClamAV/VirusTotal
    """
    __tablename__ = "malware_scan_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64))  # SHA256
    scan_result = Column(String(50), nullable=False)  # CLEAN, INFECTED, SUSPICIOUS
    scanner = Column(String(50), nullable=False)  # CLAMAV, VIRUSTOTAL
    threat_name = Column(String(255))
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())

# Importar modelos de nómina para registro en Base
from .nomina import (
    Employee, EmployeeContract, PayrollPeriod, PayrollRecord,
    PayrollEarning, PayrollDeduction, EmployeeLoan, EmployeeEvaluation,
    AttendanceRecord, RDEPRecord, IESSBatch
)

# Importar modelos de facturación electrónica SRI
from .facturacion import (
    EmpresaConfiguracion, CertificadoDigital, Cliente, ProductoServicio,
    ComprobanteElectronico, ComprobanteDetalle, ComprobanteImpuesto,
    ComprobanteRetencion, GuiaRemision, Proforma, LogSRI,
    TipoComprobanteEnum, EstadoComprobanteEnum, TipoIVAEnum,
    TipoContribuyenteEnum, RegimenTributarioEnum, TipoRetencionEnum
)

# Importar modelos de inventario
from .inventario import (
    CategoriaProducto, Producto, MovimientoInventario,
    TipoMovimientoEnum
)

# Importar modelos de almacén
from .warehouse import (
    Almacen, UbicacionAlmacen, StockUbicacion, TransferenciaAlmacen,
    TipoTransferenciaEnum
)

# Importar modelos de compras
from .purchase import (
    Proveedor, OrdenCompra, RecepcionOrden, CuentaPagar,
    EstadoOrdenEnum, EstadoCuentaEnum
)

# Importar modelos de CRM
from .crm import (
    Lead, Oportunidad, PipelineVenta, SeguimientoCRM,
    EstadoLeadEnum, EtapaPipelineEnum
)

# Importar modelos de proyectos
from .projects import (
    Proyecto, TareaProyecto, Timesheet, RecursoProyecto,
    EstadoProyectoEnum, PrioridadEnum
)

# Importar modelos de integraciones
from .integrations import (
    ConexionBancaria, ExtractoBancario, IntegracionEcommerce,
    TipoIntegracionEnum
)

# Importar modelos de presupuestos
from .budget import (
    PresupuestoAnual, LineaPresupuestaria, EjecucionPresupuesto,
    EstadoPresupuestoEnum
)

# Importar modelos de IA/ML
from .ai import (
    PrediccionVenta, DeteccionFraude, CategoriaAutomatica,
    TipoAnalisisEnum
)
