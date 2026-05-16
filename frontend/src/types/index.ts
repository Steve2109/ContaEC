export interface User {
  id: string;
  email: string;
  full_name: string;
  is_admin?: boolean;
  created_at: string;
}

export interface Company {
  id: string;
  ruc: string;
  name: string;
  business_name: string;
  address: string;
  phone: string;
  email: string;
  regime: string;
  contributor_type: string;
  logo_url?: string;
  user_id: string;
  created_at: string;
}

export interface License {
  id: string;
  user_id: string;
  type: 'mensual' | 'trimestral' | 'semestral' | 'anual';
  start_date: string;
  end_date: string;
  status: 'active' | 'expired' | 'pending';
  created_at: string;
}

export interface Invoice {
  id: string;
  company_id: string;
  sequential: string;
  type: 'factura' | 'nota_credito' | 'nota_debito' | 'retencion' | 'guia_remision' | 'proforma';
  customer: Customer;
  items: InvoiceItem[];
  subtotal: number;
  iva: number;
  ice?: number;
  total: number;
  status: 'borrador' | 'autorizado' | 'rechazado' | 'anulado';
  sri_response?: any;
  created_at: string;
}

export interface Customer {
  id: string;
  ruc_ci: string;
  name: string;
  email: string;
  phone: string;
  address: string;
  contributor_type: string;
}

export interface InvoiceItem {
  product_id: string;
  description: string;
  quantity: number;
  unit_price: number;
  discount: number;
  iva_percentage: number;
  ice_percentage?: number;
  subtotal: number;
  iva: number;
  total: number;
}

export interface Product {
  id: string;
  company_id: string;
  sku: string;
  barcode?: string;
  name: string;
  description: string;
  category: string;
  unit_price: number;
  cost_price: number;
  stock: number;
  min_stock: number;
  iva_percentage: number;
  ice_percentage?: number;
  warehouses: WarehouseStock[];
}

export interface WarehouseStock {
  warehouse_id: string;
  location: string;
  quantity: number;
}

export interface Warehouse {
  id: string;
  company_id: string;
  name: string;
  address: string;
  locations: Location[];
}

export interface Location {
  id: string;
  code: string;
  rack: string;
  shelf: string;
  level: string;
  bin: string;
}

export interface Employee {
  id: string;
  company_id: string;
  ruc_ci: string;
  full_name: string;
  position: string;
  salary: number;
  contract_type: string;
  start_date: string;
  iess_number: string;
  bank_account?: string;
}

export interface Payroll {
  id: string;
  company_id: string;
  period: string;
  employees: PayrollEmployee[];
  total_gross: number;
  total_deductions: number;
  total_net: number;
  status: 'borrador' | 'aprobado' | 'pagado';
}

export interface PayrollEmployee {
  employee_id: string;
  gross_salary: number;
  overtime: number;
  bonuses: number;
  deductions: Deduction[];
  net_salary: number;
}

export interface Deduction {
  type: string;
  amount: number;
  description: string;
}

export interface Supplier {
  id: string;
  company_id: string;
  ruc: string;
  name: string;
  contact_name: string;
  email: string;
  phone: string;
  address: string;
  credit_limit?: number;
}

export interface PurchaseOrder {
  id: string;
  company_id: string;
  supplier_id: string;
  sequential: string;
  items: PurchaseOrderItem[];
  subtotal: number;
  iva: number;
  total: number;
  status: 'borrador' | 'aprobada' | 'recibida_parcial' | 'recibida_total' | 'cancelada';
}

export interface PurchaseOrderItem {
  product_id: string;
  description: string;
  quantity: number;
  received_quantity: number;
  unit_price: number;
  subtotal: number;
  tax_amount: number;
  total: number;
}

export interface CRMLead {
  id: string;
  company_id: string;
  name: string;
  email: string;
  phone: string;
  source: string;
  status: 'nuevo' | 'contactado' | 'calificado' | 'propuesta' | 'negociacion' | 'ganado' | 'perdido';
  value: number;
  assigned_to: string;
}

export interface Project {
  id: string;
  company_id: string;
  name: string;
  description: string;
  client_id: string;
  budget: number;
  start_date: string;
  end_date: string;
  status: 'planificacion' | 'en_curso' | 'pausado' | 'completado' | 'cancelado';
  team: ProjectMember[];
}

export interface ProjectMember {
  user_id: string;
  full_name: string;
  role: string;
  hourly_rate?: number;
}

export interface Budget {
  id: string;
  company_id: string;
  year: number;
  account_code: string;
  monthly_amounts: number[];
  status: 'borrador' | 'aprobado' | 'cerrado';
}
