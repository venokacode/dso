from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from openpyxl import Workbook

from ..database import get_db
from ..models.customer import Customer
from ..models.order import Order, OrderItem
from ..models.invoice import MonthlyInvoice
from ..schemas import InvoiceOut, InvoiceUpdate

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    customer_id: int | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(MonthlyInvoice)
    if customer_id:
        q = q.filter(MonthlyInvoice.customer_id == customer_id)
    if year:
        q = q.filter(MonthlyInvoice.year == year)
    if month:
        q = q.filter(MonthlyInvoice.month == month)
    if status:
        q = q.filter(MonthlyInvoice.status == status)

    invoices = q.order_by(MonthlyInvoice.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    result = []
    for inv in invoices:
        d = InvoiceOut.model_validate(inv)
        cust = db.query(Customer).filter(Customer.id == inv.customer_id).first()
        d.customer_name = cust.name if cust else None
        result.append(d)
    return result


@router.post("/generate")
def generate_invoices(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
):
    """Generate monthly invoices for all customers with completed orders in the given month."""
    from sqlalchemy import extract

    orders = (
        db.query(Order)
        .filter(
            extract("year", Order.order_date) == year,
            extract("month", Order.order_date) == month,
            Order.status.in_(["confirmed", "shipped", "completed"]),
        )
        .all()
    )

    customer_totals: dict[int, dict] = {}
    for o in orders:
        if o.customer_id not in customer_totals:
            customer_totals[o.customer_id] = {"amount": 0, "count": 0}
        customer_totals[o.customer_id]["amount"] += o.total_amount
        customer_totals[o.customer_id]["count"] += 1

    created = 0
    for cid, data in customer_totals.items():
        existing = (
            db.query(MonthlyInvoice)
            .filter(
                MonthlyInvoice.customer_id == cid,
                MonthlyInvoice.year == year,
                MonthlyInvoice.month == month,
            )
            .first()
        )
        if existing:
            existing.total_amount = data["amount"]
            existing.order_count = data["count"]
        else:
            inv = MonthlyInvoice(
                invoice_no=f"INV-{year}{month:02d}-{cid:04d}",
                customer_id=cid,
                year=year,
                month=month,
                total_amount=data["amount"],
                order_count=data["count"],
                status="draft",
            )
            db.add(inv)
            created += 1

    db.commit()
    return {"ok": True, "created": created, "updated": len(customer_totals) - created}


@router.put("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(invoice_id: int, data: InvoiceUpdate, db: Session = Depends(get_db)):
    inv = db.query(MonthlyInvoice).filter(MonthlyInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="账单不存在")

    if data.status:
        if data.status == "confirmed" and inv.status == "draft":
            inv.status = "confirmed"
            inv.confirmed_at = datetime.now(timezone.utc)
        elif data.status == "paid" and inv.status == "confirmed":
            inv.status = "paid"
            inv.paid_at = datetime.now(timezone.utc)
        elif data.status != inv.status:
            raise HTTPException(status_code=400, detail=f"无法从 {inv.status} 变更为 {data.status}")

    if data.notes is not None:
        inv.notes = data.notes

    db.commit()
    db.refresh(inv)
    d = InvoiceOut.model_validate(inv)
    cust = db.query(Customer).filter(Customer.id == inv.customer_id).first()
    d.customer_name = cust.name if cust else None
    return d


@router.get("/{invoice_id}/export")
def export_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Export invoice details as an Excel file."""
    inv = db.query(MonthlyInvoice).filter(MonthlyInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="账单不存在")

    customer = db.query(Customer).filter(Customer.id == inv.customer_id).first()
    from sqlalchemy import extract
    orders = (
        db.query(Order)
        .filter(
            Order.customer_id == inv.customer_id,
            extract("year", Order.order_date) == inv.year,
            extract("month", Order.order_date) == inv.month,
            Order.status.in_(["confirmed", "shipped", "completed"]),
        )
        .all()
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "月结账单"

    ws.append(["月结账单"])
    ws.append(["账单编号", inv.invoice_no])
    ws.append(["客户名称", customer.name if customer else ""])
    ws.append(["账期", f"{inv.year}年{inv.month}月"])
    ws.append(["订单数量", inv.order_count])
    ws.append(["总金额（元）", inv.total_amount / 100])
    ws.append(["状态", inv.status])
    ws.append([])

    ws.append(["订单编号", "订单日期", "产品名称", "规格编码", "单位", "单价（元）", "数量", "小计（元）"])
    for order in orders:
        for item in order.items:
            ws.append([
                order.order_no,
                str(order.order_date),
                item.product_name,
                item.product_code,
                item.unit,
                item.unit_price / 100,
                item.quantity,
                item.amount / 100,
            ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"{inv.invoice_no}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
