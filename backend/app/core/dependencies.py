"""
Dependencias comunes para la aplicación
Gestión de empresas, validaciones y utilidades compartidas
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models import User, Company, UserCompany
from app.utils.dependencies import get_current_user


def get_current_empresa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener la empresa actual del usuario
    Se asume que el usuario tiene una empresa principal o se selecciona la primera
    """
    # Obtener la primera empresa del usuario
    company = db.query(Company).filter(Company.owner_id == current_user.id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene ninguna empresa registrada"
        )
    
    return company


def get_empresa_by_id(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener una empresa específica por ID verificando permisos
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.owner_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no encontrada o sin permisos de acceso"
        )
    
    return company


def check_user_has_company_access(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verificar si el usuario tiene acceso a una empresa específica
    (ya sea como dueño o como miembro)
    """
    # Verificar si es el dueño
    is_owner = db.query(Company).filter(
        Company.id == company_id,
        Company.owner_id == current_user.id
    ).first()
    
    if is_owner:
        return True
    
    # Verificar si es miembro a través de user_companies
    is_member = db.query(UserCompany).filter(
        UserCompany.company_id == company_id,
        UserCompany.user_id == current_user.id
    ).first()
    
    if is_member:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tiene acceso a esta empresa"
    )
