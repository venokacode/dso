from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import extract, func

from ..database import get_db
from ..models.customer import Customer
from ..models.product import Product
from ..models.order import Order
from ..models.invoice import MonthlyInvoice
from ..schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()
    year, month = today.year, today.month

    total_customers = db.query(func.count(Customer.id)).filter(Customer.is_active == True).scalar()
    total_products = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()

    orders_this_month = (
        db.query(func.count(Order.id))
        .filter(extract("year", Order.order_date) == year, extract("month", Order.order_date) == month)
        .scalar()
    )
    revenue_this_month = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            extract("year", Order.order_date) == year,
            extract("month", Order.order_date) == month,
            Order.status.in_(["confirmed", "shipped", "completed"]),
        )
        .scalar()
    )

    pending_invoices = (
        db.query(func.count(MonthlyInvoice.id))
        .filter(MonthlyInvoice.status.in_(["draft", "confirmed"]))
        .scalar()
    )
    unpaid_amount = (
        db.query(func.coalesce(func.sum(MonthlyInvoice.total_amount), 0))
        .filter(MonthlyInvoice.status.in_(["draft", "confirmed"]))
        .scalar()
    )

    return DashboardStats(
        total_customers=total_customers or 0,
        total_products=total_products or 0,
        total_orders=total_orders or 0,
        orders_this_month=orders_this_month or 0,
        revenue_this_month=revenue_this_month or 0,
        pending_invoices=pending_invoices or 0,
        unpaid_amount=unpaid_amount or 0,
    )
