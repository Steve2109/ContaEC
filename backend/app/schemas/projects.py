"""
Schemas para Proyectos (Fase 14)
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from app.models.projects import ProjectStatus, TaskStatus

class ProjectCreate(BaseModel):
    company_id: int
    nombre: str
    descripcion: Optional[str] = None
    estado: Optional[ProjectStatus] = ProjectStatus.PLANIFICACION
    fecha_inicio: Optional[date] = None
    fecha_fin_estimada: Optional[date] = None
    presupuesto: Optional[float] = 0.0
    costo_total: Optional[float] = 0.0
    cliente_id: Optional[int] = None
    gerente_id: Optional[int] = None

class ProjectResponse(ProjectCreate):
    id: int
    fecha_fin_real: Optional[date] = None
    creado_en: datetime

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    project_id: int
    nombre: str
    descripcion: Optional[str] = None
    estado: Optional[TaskStatus] = TaskStatus.PENDIENTE
    prioridad: Optional[str] = "media"
    asignado_a: Optional[int] = None
    fecha_inicio: Optional[date] = None
    fecha_fin_estimada: Optional[date] = None
    horas_estimadas: Optional[float] = 0.0
    costo_horas: Optional[float] = 0.0

class TaskResponse(TaskCreate):
    id: int
    horas_reales: Optional[float] = 0.0
    creado_en: datetime

    class Config:
        from_attributes = True

class TimeSheetCreate(BaseModel):
    project_id: int
    task_id: Optional[int] = None
    fecha: date
    horas: float
    descripcion: Optional[str] = None
