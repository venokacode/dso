export type CustomerStatus = 'active' | 'inactive';
export type OrderStatus = 'draft' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';
export type StatementStatus = 'open' | 'issued' | 'paid' | 'overdue';

export interface Customer {
  id: number;
  code: string;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  address?: string;
  credit_limit: string;
  payment_terms_days: number;
  status: CustomerStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  description?: string;
  unit: string;
  unit_price: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
  id: number;
  product_id: number;
  product: Product;
  quantity: string;
  unit_price: string;
  discount_rate: string;
  line_total: string;
  notes?: string;
}

export interface Order {
  id: number;
  order_no: string;
  customer_id: number;
  customer: Customer;
  status: OrderStatus;
  order_date: string;
  delivery_date?: string;
  delivery_address?: string;
  notes?: string;
  subtotal: string;
  discount_amount: string;
  total_amount: string;
  statement_id?: number;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

export interface OrderListItem {
  id: number;
  order_no: string;
  customer_id: number;
  customer: Customer;
  status: OrderStatus;
  order_date: string;
  total_amount: string;
  created_at: string;
}

export interface MonthlyStatement {
  id: number;
  statement_no: string;
  customer_id: number;
  customer: Customer;
  year: number;
  month: number;
  total_amount: string;
  status: StatementStatus;
  issued_date?: string;
  due_date?: string;
  paid_date?: string;
  notes?: string;
  orders: OrderListItem[];
  created_at: string;
  updated_at: string;
}

export interface StatementListItem {
  id: number;
  statement_no: string;
  customer_id: number;
  customer: Customer;
  year: number;
  month: number;
  total_amount: string;
  status: StatementStatus;
  issued_date?: string;
  due_date?: string;
  paid_date?: string;
  created_at: string;
}

export interface DashboardStats {
  total_customers: number;
  active_customers: number;
  total_orders_this_month: number;
  total_amount_this_month: string;
  pending_statements: number;
  overdue_statements: number;
  overdue_amount: string;
}
