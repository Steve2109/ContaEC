"""
Modelos para Proyectos y Servicios (Fase 14)
Gestión de proyectos, tareas, timesheets y recursos.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database.base_class import Base

class ProjectStatus(str, enum.Enum):
    PLANIFICACION = "planificacion"
    EN_CURSO = "en_curso"
    PAUSADO = "pausado"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"

class TaskStatus(str, enum.Enum):
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    REVISION = "revision"
    COMPLETADA = "completada"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    estado = Column(Enum(ProjectStatus), default=ProjectStatus.PLANIFICACION)
    fecha_inicio = Column(Date)
    fecha_fin_estimada = Column(Date)
    fecha_fin_real = Column(Date)
    presupuesto = Column(Float, default=0.0)
    costo_total = Column(Float, default=0.0)
    cliente_id = Column(Integer, ForeignKey("clients.id"))
    gerente_id = Column(Integer, ForeignKey("users.id"))
    creado_en = Column(DateTime, default=datetime.utcnow)

    tareas = relationship("Task", back_populates="proyecto", cascade="all, delete-orphan")
    timesheets = relationship("TimeSheet", back_populates="proyecto", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "project_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    estado = Column(Enum(TaskStatus), default=TaskStatus.PENDIENTE)
    prioridad = Column(String(20), default="media")  # baja, media, alta, critica
    asignado_a = Column(Integer, ForeignKey("users.id"))
    fecha_inicio = Column(Date)
    fecha_fin_estimada = Column(Date)
    horas_estimadas = Column(Float, default=0.0)
    horas_reales = Column(Float, default=0.0)
    costo_horas = Column(Float, default=0.0)
    creado_en = Column(DateTime, default=datetime.utcnow)

    proyecto = relationship("Project", back_populates="tareas")

class TimeSheet(Base):
    __tablename__ = "project_timesheets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("project_tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    horas = Column(Float, nullable=False)
    descripcion = Column(Text)
    aprobado = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    proyecto = relationship("Project", back_populates="timesheets")
