"""Schemas mínimos para compatibilidad de POS."""
from pydantic import BaseModel, Field
from typing import List, Optional


class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount: float = 0


class InvoiceCreate(BaseModel):
    company_id: int
    customer_id: Optional[int] = None
    customer_ruc: Optional[str] = None
    customer_name: Optional[str] = None
    items: List[InvoiceItemCreate]


class InvoiceResponse(BaseModel):
    id: int
    company_id: int
    status: str
    total: float

    class Config:
        from_attributes = True
