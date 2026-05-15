"""
Rutas para Presupuestos y Control Presupuestario - Fase 12
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional, List

from app.database.session import get_db
from app.utils.dependencies import get_current_user, verify_company_access
from app.models.user import User
from app.models.company import Company

router = APIRouter(prefix="/api/budget", tags=["Presupuestos"])

@router.post("/annual")
async def create_annual_budget(
    budget_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Crear presupuesto anual por cuenta contable
    """
    from app.models.budget import Budget, BudgetLine
    
    year = budget_data.get("year", datetime.utcnow().year)
    
    # Verificar si ya existe presupuesto para ese año
    existing = db.query(Budget).filter(
        Budget.company_id == company.id,
        Budget.year == year
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un presupuesto para el año {year}"
        )
    
    new_budget = Budget(
        company_id=company.id,
        user_id=current_user.id,
        year=year,
        total_amount=budget_data.get("total_amount", 0.0),
        status="BORRADOR",
        notes=budget_data.get("notes")
    )
    
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    
    # Crear líneas presupuestarias
    lines = budget_data.get("lines", [])
    for line in lines:
        budget_line = BudgetLine(
            budget_id=new_budget.id,
            account_code=line.get("account_code"),
            account_name=line.get("account_name"),
            monthly_amounts=line.get("monthly_amounts", [0.0] * 12),
            annual_total=sum(line.get("monthly_amounts", [0.0] * 12))
        )
        db.add(budget_line)
    
    db.commit()
    
    return {"message": "Presupuesto creado exitosamente", "budget_id": new_budget.id}

@router.get("/{year}/execution")
async def get_budget_execution(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Obtener ejecución presupuestaria comparativo vs real
    """
    from app.models.budget import Budget, BudgetLine
    
    budget = db.query(Budget).filter(
        Budget.company_id == company.id,
        Budget.year == year
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe presupuesto para el año {year}"
        )
    
    # Calcular ejecución por mes
    execution_data = []
    for month in range(1, 13):
        # Presupuesto del mes
        monthly_budget = sum(
            line.monthly_amounts[month-1] if len(line.monthly_amounts) >= month else 0
            for line in budget.lines
        )
        
        # Real del mes (aquí iría consulta a tabla de movimientos reales)
        # Por simplicidad, simulamos 0
        monthly_real = 0.0
        
        variance = monthly_budget - monthly_real
        variance_percent = (variance / monthly_budget * 100) if monthly_budget > 0 else 0
        
        execution_data.append({
            "month": month,
            "budgeted": round(monthly_budget, 2),
            "actual": round(monthly_real, 2),
            "variance": round(variance, 2),
            "variance_percent": round(variance_percent, 2),
            "status": "SOBRE_GIRO" if variance < 0 else "OK"
        })
    
    return {
        "year": year,
        "budget_name": f"Presupuesto {year}",
        "total_budget": budget.total_amount,
        "execution_by_month": execution_data,
        "alerts": [
            {
                "month": item["month"],
                "message": f"Sobregiro de ${abs(item['variance'])} en mes {item['month']}",
                "severity": "HIGH"
            }
            for item in execution_data if item["status"] == "SOBRE_GIRO"
        ]
    }

@router.get("/alerts")
async def get_budget_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: Company = Depends(verify_company_access)
):
    """
    Alertas inteligentes de sobregiro presupuestario
    """
    from app.models.budget import Budget, BudgetLine
    
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month
    
    budgets = db.query(Budget).filter(
        Budget.company_id == company.id,
        Budget.year == current_year,
        Budget.status == "APROBADO"
    ).all()
    
    alerts = []
    
    for budget in budgets:
        # Verificar cada línea
        for line in budget.lines:
            if len(line.monthly_amounts) >= current_month:
                budgeted = line.monthly_amounts[current_month - 1]
                # Simular real (en producción consultar tabla de gastos)
                actual = 0.0
                
                if actual > budgeted and budgeted > 0:
                    over_percentage = ((actual - budgeted) / budgeted) * 100
                    
                    alerts.append({
                        "budget_id": budget.id,
                        "account_code": line.account_code,
                        "account_name": line.account_name,
                        "month": current_month,
                        "budgeted": round(budgeted, 2),
                        "actual": round(actual, 2),
                        "over_amount": round(actual - budgeted, 2),
                        "over_percentage": round(over_percentage, 2),
                        "message": f"La cuenta {line.account_code} supera el presupuesto en {over_percentage:.1f}%"
                    })
    
    return {
        "current_period": f"{current_year}-{current_month:02d}",
        "total_alerts": len(alerts),
        "alerts": alerts
    }
