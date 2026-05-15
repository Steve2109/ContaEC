"""
Rutas para Proyectos y Servicios (Fase 14)
Gestión de proyectos, tareas, timesheets.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.database.session import get_db
from app.models.projects import Project, Task, TimeSheet, ProjectStatus, TaskStatus
from app.schemas.projects import ProjectCreate, ProjectResponse, TaskCreate, TaskResponse, TimeSheetCreate
from app.utils.dependencies import get_current_user, verify_company_access
from app.models.user import User

router = APIRouter(prefix="/api/projects", tags=["Proyectos"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear nuevo proyecto"""
    verify_company_access(db, current_user.id, project_data.company_id)
    
    project = Project(**project_data.dict(), creado_en=datetime.utcnow())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.get("/", response_model=List[ProjectResponse])
def get_projects(
    company_id: int,
    estado: Optional[ProjectStatus] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener lista de proyectos"""
    verify_company_access(db, current_user.id, company_id)
    
    query = db.query(Project).filter(Project.company_id == company_id)
    if estado:
        query = query.filter(Project.estado == estado)
    
    projects = query.offset(skip).limit(limit).all()
    return projects

@router.get("/{project_id}/profitability")
def get_project_profitability(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calcular rentabilidad del proyecto"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    verify_company_access(db, current_user.id, project.company_id)
    
    # Calcular costos totales de timesheets
    total_hours = db.query(
        db.func.sum(TimeSheet.horas).label("horas_totales")
    ).filter(TimeSheet.project_id == project_id).scalar() or 0
    
    # Costo estimado vs real
    rentabilidad = {
        "presupuesto": project.presupuesto,
        "costo_estimado": project.costo_total,
        "horas_trabajadas": float(total_hours),
        "margen_estimado": project.presupuesto - project.costo_total if project.presupuesto else 0,
        "porcentaje_margen": ((project.presupuesto - project.costo_total) / project.presupuesto * 100) if project.presupuesto else 0
    }
    
    return rentabilidad

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear nueva tarea en proyecto"""
    project = db.query(Project).filter(Project.id == task_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    verify_company_access(db, current_user.id, project.company_id)
    
    task = Task(**task_data.dict(), creado_en=datetime.utcnow())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.post("/timesheets", status_code=status.HTTP_201_CREATED)
def log_timesheet(
    timesheet_data: TimeSheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registrar horas trabajadas (timesheet)"""
    project = db.query(Project).filter(Project.id == timesheet_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    verify_company_access(db, current_user.id, project.company_id)
    
    timesheet = TimeSheet(
        **timesheet_data.dict(),
        user_id=current_user.id,
        creado_en=datetime.utcnow()
    )
    db.add(timesheet)
    
    # Actualizar horas reales de la tarea si existe
    if timesheet_data.task_id:
        task = db.query(Task).filter(Task.id == timesheet_data.task_id).first()
        if task:
            task.horas_reales = (task.horas_reales or 0) + timesheet_data.horas
    
    db.commit()
    return {"message": "Horas registradas exitosamente"}

@router.get("/{project_id}/tasks")
def get_project_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener todas las tareas de un proyecto"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    verify_company_access(db, current_user.id, project.company_id)
    
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    return tasks
