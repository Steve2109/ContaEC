"""
Esquemas Pydantic para Nómina y Recursos Humanos - Fase 5
Validación de datos de entrada/salida para empleados, nómina, asistencia
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class ContractType(str, Enum):
    INDEFINIDO = "indefinido"
    PLAZO_FIJO = "plazo_fijo"
    OCASIONAL = "ocasional"
    APRENDIZAJE = "aprendizaje"
    TELETRABAJO = "teletrabajo"


class PaymentFrequency(str, Enum):
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"


class DeductionType(str, Enum):
    IESS = "iess"
    IECE = "iece"
    SECAP = "secap"
    IMPUESTO_RENTA = "impuesto_renta"
    PRESTAMO = "prestamo"
    EMBARGO = "embargo"
    ANTICIPO = "anticipo"
    OTRO = "otro"


# ===================== EMPLEADOS =====================

class EmployeeBase(BaseModel):
    """Datos base de empleado"""
    identification: str = Field(..., min_length=10, max_length=20, description="Cédula o RUC")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    marital_status: Optional[str] = Field(None, max_length=50)
    
    # Datos laborales
    job_title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    contract_type: ContractType = ContractType.INDEFINIDO
    start_date: date
    end_date: Optional[date] = None
    base_salary: float = Field(..., gt=0, description="Salario base")
    payment_frequency: PaymentFrequency = PaymentFrequency.MENSUAL
    
    # Cargas familiares
    has_children: bool = False
    children_count: int = Field(default=0, ge=0)
    disabled_dependents: int = Field(default=0, ge=0)
    
    # Datos bancarios
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=50)
    bank_account_type: Optional[str] = Field(None, max_length=20)


class EmployeeCreate(EmployeeBase):
    """Esquema para crear empleado"""
    company_id: int
    employee_code: Optional[str] = Field(None, max_length=50)


class EmployeeUpdate(BaseModel):
    """Esquema para actualizar empleado"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    base_salary: Optional[float] = None
    payment_frequency: Optional[PaymentFrequency] = None
    has_children: Optional[bool] = None
    children_count: Optional[int] = None
    disabled_dependents: Optional[int] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    bank_account_type: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    """Esquema de respuesta de empleado"""
    id: int
    company_id: int
    employee_code: str
    is_active: bool
    termination_date: Optional[date] = None
    termination_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ===================== PERÍODOS DE NÓMINA =====================

class PayrollPeriodBase(BaseModel):
    """Datos base de período de nómina"""
    period_name: str = Field(..., max_length=100, description="Nombre del período")
    start_date: date
    end_date: date
    payment_date: date


class PayrollPeriodCreate(PayrollPeriodBase):
    """Esquema para crear período de nómina"""
    company_id: int


class PayrollPeriodResponse(PayrollPeriodBase):
    """Esquema de respuesta de período"""
    id: int
    company_id: int
    status: str
    total_gross: float = 0
    total_deductions: float = 0
    total_net: float = 0
    total_employer_contributions: float = 0
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ===================== REGISTROS DE NÓMINA =====================

class PayrollCalculateRequest(BaseModel):
    """Solicitud para calcular nómina de un empleado"""
    period_id: int
    employee_id: int
    
    # Ingresos variables
    overtime_hours: float = Field(default=0, ge=0)
    bonuses: Optional[float] = Field(default=0, ge=0)
    commissions: Optional[float] = Field(default=0, ge=0)
    food_allowance: Optional[float] = Field(default=0, ge=0)
    transportation_allowance: Optional[float] = Field(default=0, ge=0)
    profit_sharing_amount: Optional[float] = Field(default=0, ge=0)
    
    # Deducciones variables
    loan_deduction: Optional[float] = Field(default=0, ge=0)
    advance_deduction: Optional[float] = Field(default=0, ge=0)


class PayrollRecordBase(BaseModel):
    """Datos base de registro de nómina"""
    basic_salary: float = 0
    overtime_hours: float = 0
    overtime_amount: float = 0
    bonuses: float = 0
    commissions: float = 0
    food_allowance: float = 0
    transportation_allowance: float = 0
    other_earnings: float = 0
    
    # Décimos y beneficios
    thirteenth_salary: float = 0
    fourteenth_salary: float = 0
    reserve_fund: float = 0
    profit_sharing: float = 0
    vacation_pay: float = 0
    vacation_days: int = 0
    
    # Totales ingresos
    gross_total: float = 0
    
    # Deducciones
    iess_deduction: float = 0
    iece_deduction: float = 0
    secap_deduction: float = 0
    income_tax: float = 0
    loan_deduction: float = 0
    advance_deduction: float = 0
    garnishment: float = 0
    other_deductions: float = 0
    total_deductions: float = 0
    
    # Neto
    net_pay: float = 0
    
    # Aportes patronales
    employer_ieee: float = 0
    employer_iece: float = 0
    employer_secap: float = 0
    employer_reserve_fund: float = 0
    employer_thirteenth: float = 0
    employer_fourteenth: float = 0
    employer_vacation: float = 0
    total_employer_contributions: float = 0
    
    # Estado
    is_paid: bool = False
    payment_date: Optional[date] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None


class PayrollRecordCreate(PayrollRecordBase):
    """Esquema para crear registro de nómina"""
    period_id: int
    employee_id: int


class PayrollRecordResponse(PayrollRecordBase):
    """Esquema de respuesta de registro de nómina"""
    id: int
    period_id: int
    employee_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ===================== RUBROS PERSONALIZABLES =====================

class PayrollEarningBase(BaseModel):
    """Rubro de ingreso personalizado"""
    concept: str = Field(..., max_length=200)
    amount: float = Field(..., gt=0)
    is_recurring: bool = False
    accounting_account: Optional[str] = Field(None, max_length=50)


class PayrollEarningCreate(PayrollEarningBase):
    """Crear rubro de ingreso"""
    payroll_record_id: int


class PayrollEarningResponse(PayrollEarningBase):
    """Respuesta de rubro de ingreso"""
    id: int
    payroll_record_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PayrollDeductionBase(BaseModel):
    """Rubro de deducción personalizado"""
    deduction_type: DeductionType
    concept: str = Field(..., max_length=200)
    amount: float = Field(..., gt=0)
    is_recurring: bool = False
    accounting_account: Optional[str] = Field(None, max_length=50)


class PayrollDeductionCreate(PayrollDeductionBase):
    """Crear rubro de deducción"""
    payroll_record_id: int


class PayrollDeductionResponse(PayrollDeductionBase):
    """Respuesta de rubro de deducción"""
    id: int
    payroll_record_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===================== ASISTENCIA =====================

class AttendanceBase(BaseModel):
    """Datos base de asistencia"""
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    shift_start: Optional[str] = Field(None, max_length=20)
    shift_end: Optional[str] = Field(None, max_length=20)
    shift_type: Optional[str] = Field(None, max_length=50)
    regular_hours: float = Field(default=0, ge=0)
    overtime_hours: float = Field(default=0, ge=0)
    late_minutes: int = Field(default=0, ge=0)
    early_departure_minutes: int = Field(default=0, ge=0)
    status: Optional[str] = Field(None, max_length=50)
    justification: Optional[str] = None
    justified: bool = False
    source: Optional[str] = Field(None, max_length=50)


class AttendanceCreate(AttendanceBase):
    """Crear registro de asistencia"""
    employee_id: int
    company_id: int


class AttendanceResponse(AttendanceBase):
    """Respuesta de registro de asistencia"""
    id: int
    employee_id: int
    company_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===================== PRÉSTAMOS =====================

class EmployeeLoanBase(BaseModel):
    """Datos base de préstamo a empleado"""
    amount: float = Field(..., gt=0)
    interest_rate: float = Field(default=0, ge=0)
    months: int = Field(..., gt=0)
    monthly_payment: float = Field(..., gt=0)
    start_date: date
    end_date: date
    description: Optional[str] = None


class EmployeeLoanCreate(EmployeeLoanBase):
    """Crear préstamo"""
    employee_id: int


class EmployeeLoanResponse(EmployeeLoanBase):
    """Respuesta de préstamo"""
    id: int
    employee_id: int
    balance: Optional[float] = None
    paid_amount: float = 0
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===================== EVALUACIONES =====================

class EmployeeEvaluationBase(BaseModel):
    """Datos base de evaluación"""
    evaluation_date: date
    performance_score: Optional[float] = Field(None, ge=0, le=5)
    attitude_score: Optional[float] = Field(None, ge=0, le=5)
    punctuality_score: Optional[float] = Field(None, ge=0, le=5)
    teamwork_score: Optional[float] = Field(None, ge=0, le=5)
    responsibility_score: Optional[float] = Field(None, ge=0, le=5)
    overall_score: Optional[float] = Field(None, ge=0, le=5)
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    recommendations: Optional[str] = None
    current_position_value: Optional[float] = None
    recommended_salary_increase: Optional[float] = Field(None, ge=0, le=100)
    follow_up_date: Optional[date] = None


class EmployeeEvaluationCreate(EmployeeEvaluationBase):
    """Crear evaluación"""
    employee_id: int
    evaluator_id: Optional[int] = None


class EmployeeEvaluationResponse(EmployeeEvaluationBase):
    """Respuesta de evaluación"""
    id: int
    employee_id: int
    evaluator_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===================== RESÚMENES Y REPORTES =====================

class PayrollSummary(BaseModel):
    """Resumen de nómina por período"""
    period_id: int
    period_name: str
    total_employees: int
    total_gross: float
    total_deductions: float
    total_net: float
    total_employer_contributions: float
    status: str
    payment_date: date


class DepartmentCostReport(BaseModel):
    """Reporte de costos por departamento"""
    department: str
    employee_count: int
    total_salary: float
    total_benefits: float
    total_employer_contributions: float
    total_cost: float
    average_cost_per_employee: float


class PayrollProjection(BaseModel):
    """Proyección de nómina"""
    month: int
    year: int
    projected_employees: int
    projected_gross: float
    projected_deductions: float
    projected_net: float
    projected_employer_contributions: float
    notes: Optional[str] = None
