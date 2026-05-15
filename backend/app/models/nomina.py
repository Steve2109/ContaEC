"""
Modelos de Nómina y Recursos Humanos - Fase 5
Gestión de empleados, contratos, roles de pago, IESS, décimos, fondos de reserva
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, JSON, Date, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ContractType(str, enum.Enum):
    """Tipos de contrato laboral"""
    INDEFINIDO = "indefinido"
    PLAZO_FIJO = "plazo_fijo"
    OCASIONAL = "ocasional"
    APRENDIZAJE = "aprendizaje"
    TELETRABAJO = "teletrabajo"


class PaymentFrequency(str, enum.Enum):
    """Frecuencia de pago"""
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"


class DeductionType(str, enum.Enum):
    """Tipos de deducciones"""
    IESS = "iess"
    IECE = "iece"
    SECAP = "secap"
    IMPUESTO_RENTA = "impuesto_renta"
    PRESTAMO = "prestamo"
    EMBARGO = "embargo"
    ANTICIPO = "anticipo"
    OTRO = "otro"


class Employee(Base):
    """
    Tabla de empleados
    """
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    # Datos personales
    identification = Column(String(20), unique=True, index=True, nullable=False)  # Cédula/RUC
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    birth_date = Column(Date)
    gender = Column(String(20))
    marital_status = Column(String(50))  # Estado civil
    
    # Datos laborales
    employee_code = Column(String(50), unique=True, index=True)
    job_title = Column(String(100))  # Cargo
    department = Column(String(100))  # Departamento
    contract_type = Column(SQLEnum(ContractType), default=ContractType.INDEFINIDO)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # Para contratos de plazo fijo
    base_salary = Column(Numeric(12, 2), nullable=False)
    payment_frequency = Column(SQLEnum(PaymentFrequency), default=PaymentFrequency.MENSUAL)
    
    # Cargas familiares
    has_children = Column(Boolean, default=False)
    children_count = Column(Integer, default=0)
    disabled_dependents = Column(Integer, default=0)
    
    # Datos bancarios para pagos masivos
    bank_name = Column(String(100))
    bank_account = Column(String(50))
    bank_account_type = Column(String(20))  # ahorros, corriente
    
    # Estado
    is_active = Column(Boolean, default=True)
    termination_date = Column(Date)
    termination_reason = Column(String(255))
    
    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    company = relationship("Company", back_populates="empleados")
    contracts = relationship("EmployeeContract", back_populates="employee", cascade="all, delete-orphan")
    payroll_records = relationship("PayrollRecord", back_populates="employee", cascade="all, delete-orphan")
    loans = relationship("EmployeeLoan", back_populates="employee", cascade="all, delete-orphan")
    evaluations = relationship("EmployeeEvaluation", back_populates="employee", cascade="all, delete-orphan")


class EmployeeContract(Base):
    """
    Historial de contratos por empleado
    """
    __tablename__ = "employee_contracts"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    contract_type = Column(SQLEnum(ContractType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    salary = Column(Numeric(12, 2), nullable=False)
    job_title = Column(String(100))
    department = Column(String(100))
    work_schedule = Column(String(200))  # Horario de trabajo
    location = Column(String(200))  # Lugar de trabajo
    
    # Documento del contrato
    contract_document_path = Column(String(500))
    
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    employee = relationship("Employee", back_populates="contracts")


class PayrollPeriod(Base):
    """
    Períodos de nómina
    """
    __tablename__ = "payroll_periods"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    period_name = Column(String(100), nullable=False)  # Ej: "Quincena 1 Enero 2024"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=False)
    
    # Estado del período
    status = Column(String(50), default="open")  # open, closed, paid
    
    # Totales del período
    total_gross = Column(Numeric(15, 2), default=0)
    total_deductions = Column(Numeric(15, 2), default=0)
    total_net = Column(Numeric(15, 2), default=0)
    total_employer_contributions = Column(Numeric(15, 2), default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relación
    company = relationship("Company", backref="payroll_periods")
    records = relationship("PayrollRecord", back_populates="period", cascade="all, delete-orphan")


class PayrollRecord(Base):
    """
    Registro individual de nómina por empleado en cada período
    """
    __tablename__ = "payroll_records"

    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey("payroll_periods.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Ingresos
    basic_salary = Column(Numeric(12, 2), default=0)
    overtime_hours = Column(Float, default=0)
    overtime_amount = Column(Numeric(12, 2), default=0)
    bonuses = Column(Numeric(12, 2), default=0)  # Bonificaciones
    commissions = Column(Numeric(12, 2), default=0)
    food_allowance = Column(Numeric(12, 2), default=0)  # Alimentación
    transportation_allowance = Column(Numeric(12, 2), default=0)
    other_earnings = Column(Numeric(12, 2), default=0)
    
    # Décimos (acumulados o pagados)
    thirteenth_salary = Column(Numeric(12, 2), default=0)  # Décimo tercero
    fourteenth_salary = Column(Numeric(12, 2), default=0)  # Décimo cuarto
    
    # Fondo de Reserva
    reserve_fund = Column(Numeric(12, 2), default=0)
    
    # Utilidades
    profit_sharing = Column(Numeric(12, 2), default=0)
    
    # Vacaciones
    vacation_pay = Column(Numeric(12, 2), default=0)
    vacation_days = Column(Integer, default=0)
    
    # Total ingresos
    gross_total = Column(Numeric(12, 2), default=0)
    
    # Deducciones
    iess_deduction = Column(Numeric(12, 2), default=0)  # Aporte personal IESS (9.45%)
    iece_deduction = Column(Numeric(12, 2), default=0)
    secap_deduction = Column(Numeric(12, 2), default=0)
    income_tax = Column(Numeric(12, 2), default=0)  # Impuesto a la renta
    loan_deduction = Column(Numeric(12, 2), default=0)
    advance_deduction = Column(Numeric(12, 2), default=0)  # Anticipos
    garnishment = Column(Numeric(12, 2), default=0)  # Embargos
    other_deductions = Column(Numeric(12, 2), default=0)
    
    # Total deducciones
    total_deductions = Column(Numeric(12, 2), default=0)
    
    # Neto a pagar
    net_pay = Column(Numeric(12, 2), default=0)
    
    # Aportes patronales (para contabilidad)
    employer_ieee = Column(Numeric(12, 2), default=0)  # IESS Patronal (11.27%)
    employer_iece = Column(Numeric(12, 2), default=0)  # IECE (0.5%)
    employer_secap = Column(Numeric(12, 2), default=0)  # SECAP (0.5%)
    employer_reserve_fund = Column(Numeric(12, 2), default=0)
    employer_vacation = Column(Numeric(12, 2), default=0)
    employer_thirteenth = Column(Numeric(12, 2), default=0)
    employer_fourteenth = Column(Numeric(12, 2), default=0)
    
    # Total aportes patronales
    total_employer_contributions = Column(Numeric(12, 2), default=0)
    
    # Estado
    is_paid = Column(Boolean, default=False)
    payment_date = Column(Date)
    payment_reference = Column(String(100))  # Referencia de transferencia
    
    # Notas
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    period = relationship("PayrollPeriod", back_populates="records")
    employee = relationship("Employee", back_populates="payroll_records")
    deductions = relationship("PayrollDeduction", back_populates="payroll_record", cascade="all, delete-orphan")
    earnings = relationship("PayrollEarning", back_populates="payroll_record", cascade="all, delete-orphan")


class PayrollEarning(Base):
    """
    Rubros personalizables de ingresos
    """
    __tablename__ = "payroll_earnings"

    id = Column(Integer, primary_key=True, index=True)
    payroll_record_id = Column(Integer, ForeignKey("payroll_records.id"), nullable=False)
    
    concept = Column(String(200), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    is_recurring = Column(Boolean, default=False)
    
    # Impacto contable
    accounting_account = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    payroll_record = relationship("PayrollRecord", back_populates="earnings")


class PayrollDeduction(Base):
    """
    Rubros personalizables de deducciones
    """
    __tablename__ = "payroll_deductions"

    id = Column(Integer, primary_key=True, index=True)
    payroll_record_id = Column(Integer, ForeignKey("payroll_records.id"), nullable=False)
    
    deduction_type = Column(SQLEnum(DeductionType), nullable=False)
    concept = Column(String(200), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    is_recurring = Column(Boolean, default=False)
    
    # Impacto contable
    accounting_account = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    payroll_record = relationship("PayrollRecord", back_populates="deductions")


class EmployeeLoan(Base):
    """
    Préstamos a empleados
    """
    __tablename__ = "employee_loans"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    amount = Column(Numeric(12, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), default=0)
    months = Column(Integer, nullable=False)
    monthly_payment = Column(Numeric(12, 2), nullable=False)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    balance = Column(Numeric(12, 2))
    paid_amount = Column(Numeric(12, 2), default=0)
    
    status = Column(String(50), default="active")  # active, paid, cancelled
    
    description = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    employee = relationship("Employee", back_populates="loans")


class EmployeeEvaluation(Base):
    """
    Evaluaciones de desempeño y valuación de puestos
    """
    __tablename__ = "employee_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    evaluation_date = Column(Date, nullable=False)
    evaluator_id = Column(Integer, ForeignKey("users.id"))
    
    # Calificaciones (1-5 o 1-10)
    performance_score = Column(Numeric(3, 2))
    attitude_score = Column(Numeric(3, 2))
    punctuality_score = Column(Numeric(3, 2))
    teamwork_score = Column(Numeric(3, 2))
    responsibility_score = Column(Numeric(3, 2))
    
    overall_score = Column(Numeric(3, 2))
    
    # Comentarios
    strengths = Column(Text)
    areas_for_improvement = Column(Text)
    recommendations = Column(Text)
    
    # Valuación del puesto
    current_position_value = Column(Numeric(12, 2))
    recommended_salary_increase = Column(Numeric(5, 2))
    
    # Seguimiento
    follow_up_date = Column(Date)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    employee = relationship("Employee", back_populates="evaluations")
    evaluator = relationship("User")


class AttendanceRecord(Base):
    """
    Registro de asistencia (sincronización con biométricos)
    """
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    date = Column(Date, nullable=False, index=True)
    check_in = Column(DateTime(timezone=True))
    check_out = Column(DateTime(timezone=True))
    
    # Turnos
    shift_start = Column(String(20))  # Ej: "08:00"
    shift_end = Column(String(20))  # Ej: "17:00"
    shift_type = Column(String(50))  # morning, afternoon, night, rotating
    
    # Horas trabajadas
    regular_hours = Column(Float, default=0)
    overtime_hours = Column(Float, default=0)
    late_minutes = Column(Integer, default=0)
    early_departure_minutes = Column(Integer, default=0)
    
    # Estado
    status = Column(String(50))  # present, absent, late, half_day, vacation, sick_leave
    
    # Justificaciones
    justification = Column(Text)
    justified = Column(Boolean, default=False)
    
    # Origen del dato
    source = Column(String(50))  # biometric, manual, web
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    employee = relationship("Employee")
    company = relationship("Company")


class RDEPRecord(Base):
    """
    Registros para RDEP (Relación Dependientes) - SRI
    """
    __tablename__ = "rdep_records"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    fiscal_year = Column(Integer, nullable=False)
    
    # Totales anuales
    total_gross_income = Column(Numeric(12, 2), default=0)
    total_exempt_income = Column(Numeric(12, 2), default=0)
    total_iess_deductions = Column(Numeric(12, 2), default=0)
    total_income_tax = Column(Numeric(12, 2), default=0)
    
    # Décimos pagados
    thirteenth_paid = Column(Numeric(12, 2), default=0)
    fourteenth_paid = Column(Numeric(12, 2), default=0)
    
    # Utilidades
    profit_sharing_paid = Column(Numeric(12, 2), default=0)
    
    # Fondo de reserva
    reserve_fund_paid = Column(Numeric(12, 2), default=0)
    
    # XML generado
    xml_content = Column(Text)
    xml_file_path = Column(String(500))
    
    submitted_to_sri = Column(Boolean, default=False)
    submitted_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    company = relationship("Company")
    employee = relationship("Employee")


class IESSBatch(Base):
    """
    Lotes para envío al IESS (Anexos)
    """
    __tablename__ = "iess_batches"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    batch_name = Column(String(100), nullable=False)
    period_month = Column(Integer, nullable=False)
    period_year = Column(Integer, nullable=False)
    
    # Tipo de anexo
    annex_type = Column(String(50))  # entrada, salida, modificación, reporte
    
    # Empleados en el lote
    employee_ids = Column(JSON)  # Lista de IDs de empleados
    
    # Archivo generado
    file_content = Column(Text)
    file_path = Column(String(500))
    
    status = Column(String(50), default="draft")  # draft, submitted, approved, rejected
    
    submitted_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    company = relationship("Company")
