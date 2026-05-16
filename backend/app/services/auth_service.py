"""
Servicios de autenticación y gestión de usuarios
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import httpx

from ..models import User, Company, UserCompany, License, UserConfiguration, CompanyConfiguration, SecurityLog, UserRole, LicenseType
from ..schemas import UserCreate, UserUpdate, CompanyCreate, LicenseUpdate, UserConfigurationCreate
from ..core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, encrypt_sensitive_data, decrypt_sensitive_data
from ..core.config import settings


class AuthService:
    """Servicio para autenticación de usuarios"""
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Autentica un usuario por email y contraseña
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user
    
    @staticmethod
    def create_tokens(user: User) -> dict:
        """
        Crea tokens de acceso y refresco para un usuario
        """
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id}
        )
        refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": user.id}
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    @staticmethod
    def update_last_login(db: Session, user: User) -> None:
        """
        Actualiza la fecha del último login
        """
        user.last_login = datetime.utcnow()
        db.commit()
    
    @staticmethod
    def log_security_action(
        db: Session, 
        user_id: Optional[int], 
        action: str, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
        is_suspicious: bool = False
    ) -> None:
        """
        Registra una acción de seguridad en el log
        """
        log = SecurityLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            is_suspicious=is_suspicious
        )
        db.add(log)
        db.commit()


class UserService:
    """Servicio para gestión de usuarios"""
    
    @staticmethod
    def create_user(db: Session, user_data: UserCreate, is_admin: bool = False) -> User:
        """
        Crea un nuevo usuario
        """
        # Verificar si el email ya existe
        existing_user = db.query(User).filter(
            or_(User.email == user_data.email, User.full_name == user_data.full_name)
        ).first()
        if existing_user:
            raise ValueError("El correo o nombre de usuario ya está registrado")
        
        # Crear usuario
        db_user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            phone=user_data.phone,
            is_admin=is_admin,
            role=UserRole.ADMIN if is_admin else UserRole.USER
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Crear configuración vacía para el usuario
        config = UserConfiguration(user_id=db_user.id)
        db.add(config)
        db.commit()

        if not is_admin:
            trial_license = License(
                user_id=db_user.id,
                license_type=LicenseType.MENSUAL,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30),
                is_active=True,
                payment_reference="AUTO_TRIAL_30_DIAS"
            )
            db.add(trial_license)
            db.commit()
        
        return db_user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Obtiene un usuario por ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Obtiene un usuario por email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Actualiza datos de un usuario"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        
        if "password" in update_data and update_data["password"]:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        """Desactiva un usuario"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        db.commit()
        return True
    
    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Obtiene todos los usuarios con paginación"""
        return db.query(User).offset(skip).limit(limit).all()


class CompanyService:
    """Servicio para gestión de empresas (multiempresa)"""
    
    @staticmethod
    def create_company(
        db: Session, 
        company_data: CompanyCreate, 
        owner_id: int
    ) -> Company:
        """
        Crea una nueva empresa asociada a un propietario
        """
        # Verificar si el RUC ya existe
        existing_company = db.query(Company).filter(Company.ruc == company_data.ruc).first()
        if existing_company:
            raise ValueError(f"El RUC {company_data.ruc} ya está registrado")
        
        # Crear empresa
        db_company = Company(
            ruc=company_data.ruc,
            business_name=company_data.business_name,
            trade_name=company_data.trade_name,
            owner_id=owner_id
        )
        
        db.add(db_company)
        db.commit()
        db.refresh(db_company)
        
        # Asociar el propietario como usuario de la empresa
        user_company = UserCompany(
            user_id=owner_id,
            company_id=db_company.id,
            role=UserRole.ADMIN
        )
        db.add(user_company)
        
        # Crear configuración de empresa
        config = CompanyConfiguration(company_id=db_company.id)
        db.add(config)
        
        db.commit()
        return db_company
    
    @staticmethod
    def get_company_by_ruc(db: Session, ruc: str) -> Optional[Company]:
        """Obtiene una empresa por RUC"""
        return db.query(Company).filter(Company.ruc == ruc).first()
    
    @staticmethod
    def get_companies_by_user(db: Session, user_id: int) -> List[Company]:
        """Obtiene todas las empresas que un usuario puede gestionar"""
        user_companies = db.query(UserCompany).filter(UserCompany.user_id == user_id).all()
        company_ids = [uc.company_id for uc in user_companies]
        return db.query(Company).filter(Company.id.in_(company_ids)).all()
    
    @staticmethod
    def add_user_to_company(
        db: Session, 
        user_id: int, 
        company_id: int, 
        role: UserRole = UserRole.USER
    ) -> UserCompany:
        """Añade un usuario a una empresa"""
        user_company = UserCompany(
            user_id=user_id,
            company_id=company_id,
            role=role
        )
        db.add(user_company)
        db.commit()
        db.refresh(user_company)
        return user_company
    
    @staticmethod
    def query_sri_info(ruc: str) -> Optional[dict]:
        """
        Consulta información del SRI por RUC
        NOTA: Esto requiere integración con los web services del SRI
        Por ahora retorna datos simulados para desarrollo
        """
        # TODO: Implementar consulta real al SRI en Fase 3
        # Simulación para desarrollo
        if len(ruc) == 13 and ruc.isdigit():
            return {
                "ruc": ruc,
                "business_name": f"EMPRESA EJEMPLO {ruc}",
                "trade_name": f"COMERCIAL {ruc[-4:]}",
                "contributor_type": "Obligado a llevar contabilidad",
                "regime": "Régimen General"
            }
        return None


class LicenseService:
    """Servicio para gestión de licencias"""
    
    @staticmethod
    def create_license(
        db: Session,
        user_id: int,
        license_type: LicenseType,
        start_date: datetime,
        end_date: datetime
    ) -> License:
        """Crea una nueva licencia para un usuario"""
        # Verificar si ya existe licencia
        existing = db.query(License).filter(License.user_id == user_id).first()
        if existing:
            # Actualizar licencia existente
            existing.license_type = license_type
            existing.start_date = start_date
            existing.end_date = end_date
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing
        
        license_obj = License(
            user_id=user_id,
            license_type=license_type,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        
        db.add(license_obj)
        db.commit()
        db.refresh(license_obj)
        return license_obj
    
    @staticmethod
    def get_user_license(db: Session, user_id: int) -> Optional[License]:
        """Obtiene la licencia de un usuario"""
        return db.query(License).filter(License.user_id == user_id).first()
    
    @staticmethod
    def check_license_validity(db: Session, user_id: int) -> tuple[bool, int]:
        """
        Verifica si la licencia de un usuario es válida
        Retorna (es_valida, dias_restantes)
        """
        license_obj = db.query(License).filter(
            License.user_id == user_id,
            License.is_active == True
        ).first()
        
        if not license_obj:
            return False, 0
        
        now = datetime.utcnow()
        if now > license_obj.end_date:
            return False, 0
        
        days_remaining = (license_obj.end_date - now).days
        return True, days_remaining
    
    @staticmethod
    def update_license(
        db: Session,
        license_id: int,
        update_data: LicenseUpdate
    ) -> Optional[License]:
        """Actualiza una licencia"""
        license_obj = db.query(License).filter(License.id == license_id).first()
        if not license_obj:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(license_obj, field, value)
        
        db.commit()
        db.refresh(license_obj)
        return license_obj
    
    @staticmethod
    def get_expiring_licenses(db: Session, days_threshold: int = 30) -> List[License]:
        """Obtiene licencias que expirarán en los próximos X días"""
        threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
        return db.query(License).filter(
            License.is_active == True,
            License.end_date <= threshold_date,
            License.end_date >= datetime.utcnow()
        ).all()
    
    @staticmethod
    def get_expired_licenses(db: Session) -> List[License]:
        """Obtiene licencias expiradas"""
        return db.query(License).filter(
            License.is_active == True,
            License.end_date < datetime.utcnow()
        ).all()


class UserConfigurationService:
    """Servicio para gestión de configuración de usuarios"""
    
    @staticmethod
    def get_user_config(db: Session, user_id: int) -> Optional[UserConfiguration]:
        """Obtiene la configuración de un usuario"""
        return db.query(UserConfiguration).filter(
            UserConfiguration.user_id == user_id
        ).first()
    
    @staticmethod
    def update_configuration(
        db: Session,
        user_id: int,
        config_data: UserConfigurationCreate
    ) -> UserConfiguration:
        """Actualiza la configuración de un usuario"""
        config = db.query(UserConfiguration).filter(
            UserConfiguration.user_id == user_id
        ).first()
        
        if not config:
            config = UserConfiguration(user_id=user_id)
            db.add(config)
        
        update_dict = config_data.model_dump(exclude_unset=True)
        
        # Encriptar datos sensibles
        if "firma_electronica" in update_dict and update_dict["firma_electronica"]:
            config.encrypted_firma_electronica = encrypt_sensitive_data(
                update_dict.pop("firma_electronica")
            )
        
        if "firma_clave" in update_dict and update_dict["firma_clave"]:
            config.encrypted_firma_clave = encrypt_sensitive_data(
                update_dict.pop("firma_clave")
            )
        
        if "backup_key" in update_dict and update_dict["backup_key"]:
            config.encrypted_backup_key = encrypt_sensitive_data(
                update_dict.pop("backup_key")
            )
        
        if "smtp_config" in update_dict and update_dict["smtp_config"]:
            # Encriptar configuración SMTP completa
            import json
            smtp_json = json.dumps(update_dict.pop("smtp_config"))
            config.encrypted_smtp_config = encrypt_sensitive_data(smtp_json)
        
        # Campos normales
        for field, value in update_dict.items():
            if hasattr(config, field):
                setattr(config, field, value)
        
        db.commit()
        db.refresh(config)
        return config
    
    @staticmethod
    def get_decrypted_firma(db: Session, user_id: int) -> Optional[tuple[str, str]]:
        """
        Obtiene la firma electrónica desencriptada
        Retorna (firma, clave) o None
        """
        config = db.query(UserConfiguration).filter(
            UserConfiguration.user_id == user_id
        ).first()
        
        if not config or not config.encrypted_firma_electronica:
            return None
        
        try:
            firma = decrypt_sensitive_data(config.encrypted_firma_electronica)
            clave = decrypt_sensitive_data(config.encrypted_firma_clave) if config.encrypted_firma_clave else None
            return (firma, clave)
        except Exception:
            return None
    
    @staticmethod
    def get_decrypted_smtp_config(db: Session, user_id: int) -> Optional[dict]:
        """Obtiene configuración SMTP desencriptada"""
        config = db.query(UserConfiguration).filter(
            UserConfiguration.user_id == user_id
        ).first()
        
        if not config or not config.encrypted_smtp_config:
            return None
        
        try:
            import json
            smtp_json = decrypt_sensitive_data(config.encrypted_smtp_config)
            return json.loads(smtp_json)
        except Exception:
            return None
