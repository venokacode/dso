from __future__ import annotations

import csv
import io
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .db import get_db

ORDER_STATUSES = {
    "draft": "草稿",
    "confirmed": "已确认",
    "shipped": "已发货",
    "monthly_billed": "已纳入月结",
    "closed": "已结清",
}

STATEMENT_STATUSES = {
    "draft": "草稿",
    "sent": "已发送",
    "settled": "已结清",
}


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def today_iso() -> str:
    return date.today().isoformat()


def parse_money_to_cents(value: str) -> int:
    try:
        amount = Decimal((value or "").strip())
    except InvalidOperation as exc:
        raise ValueError("金额格式不正确。") from exc
    if amount < 0:
        raise ValueError("金额不能为负数。")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_quantity(value: str) -> Decimal:
    try:
        quantity = Decimal((value or "").strip())
    except InvalidOperation as exc:
        raise ValueError("数量格式不正确。") from exc
    if quantity <= 0:
        raise ValueError("数量必须大于 0。")
    return quantity


def cents_to_display(cents: int) -> str:
    return f"¥{cents / 100:,.2f}"


def quantity_to_display(quantity: float | Decimal) -> str:
    if isinstance(quantity, Decimal):
        normalized = quantity.normalize()
        return format(normalized, "f").rstrip("0").rstrip(".") or "0"
    if float(quantity).is_integer():
        return str(int(quantity))
    return str(quantity)


def month_boundaries(period_month: str) -> tuple[date, date]:
    try:
        year, month = [int(part) for part in period_month.split("-", 1)]
        start = date(year, month, 1)
    except (ValueError, TypeError) as exc:
        raise ValueError("账期格式需要是 YYYY-MM。") from exc
    end = date(year, month, monthrange(year, month)[1])
    return start, end


def generate_order_no() -> str:
    db = get_db()
    prefix = date.today().strftime("ORD-%Y%m%d")
    sequence = (
        db.execute("SELECT COUNT(*) AS count FROM orders WHERE order_no LIKE ?", (f"{prefix}-%",))
        .fetchone()["count"]
        + 1
    )
    return f"{prefix}-{sequence:03d}"


def generate_statement_no(customer_code: str, period_month: str) -> str:
    db = get_db()
    compact_month = period_month.replace("-", "")
    prefix = f"ST-{compact_month}-{customer_code.upper()}"
    sequence = (
        db.execute(
            "SELECT COUNT(*) AS count FROM statements WHERE statement_no LIKE ?",
            (f"{prefix}-%",),
        ).fetchone()["count"]
        + 1
    )
    return f"{prefix}-{sequence:02d}"


def recalculate_statement_total(statement_id: int) -> int:
    db = get_db()
    total = db.execute(
        """
        SELECT COALESCE(SUM(oi.subtotal_cents), 0) AS total_amount
        FROM statement_orders so
        JOIN order_items oi ON oi.order_id = so.order_id
        WHERE so.statement_id = ?
        """,
        (statement_id,),
    ).fetchone()["total_amount"]
    db.execute(
        "UPDATE statements SET total_amount_cents = ? WHERE id = ?",
        (total, statement_id),
    )
    return int(total)


def create_or_update_statement(customer_id: int, period_month: str) -> int:
    db = get_db()
    customer = db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if customer is None:
        raise ValueError("客户不存在。")

    start_date, end_date = month_boundaries(period_month)
    statement = db.execute(
        "SELECT * FROM statements WHERE customer_id = ? AND period_month = ?",
        (customer_id, period_month),
    ).fetchone()
    if statement is not None and statement["status"] != "draft":
        raise ValueError("该账期结算单已发送或结清，不能追加订单。")

    eligible_orders = db.execute(
        """
        SELECT o.id
        FROM orders o
        LEFT JOIN statement_orders so ON so.order_id = o.id
        WHERE o.customer_id = ?
          AND o.status = 'shipped'
          AND so.order_id IS NULL
          AND date(COALESCE(o.delivery_date, o.order_date)) BETWEEN date(?) AND date(?)
        ORDER BY date(COALESCE(o.delivery_date, o.order_date)), o.id
        """,
        (customer_id, start_date.isoformat(), end_date.isoformat()),
    ).fetchall()

    if statement is None and not eligible_orders:
        raise ValueError("该账期没有可月结的已发货订单。")

    if statement is None:
        due_date = end_date + timedelta(days=int(customer["settlement_due_days"]))
        cursor = db.execute(
            """
            INSERT INTO statements (
                statement_no,
                customer_id,
                period_month,
                start_date,
                end_date,
                due_date,
                total_amount_cents,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                generate_statement_no(customer["account_code"], period_month),
                customer_id,
                period_month,
                start_date.isoformat(),
                end_date.isoformat(),
                due_date.isoformat(),
                0,
                "draft",
                timestamp(),
            ),
        )
        statement_id = int(cursor.lastrowid)
    else:
        statement_id = int(statement["id"])

    if not eligible_orders:
        raise ValueError("没有新的已发货订单可以追加到该月结算单。")

    db.executemany(
        "INSERT INTO statement_orders (statement_id, order_id) VALUES (?, ?)",
        [(statement_id, order["id"]) for order in eligible_orders],
    )
    db.executemany(
        "UPDATE orders SET status = 'monthly_billed' WHERE id = ?",
        [(order["id"],) for order in eligible_orders],
    )
    recalculate_statement_total(statement_id)
    db.commit()
    return statement_id


def update_statement_status(statement_id: int, new_status: str) -> None:
    if new_status not in STATEMENT_STATUSES:
        raise ValueError("结算单状态不合法。")

    db = get_db()
    statement = db.execute("SELECT * FROM statements WHERE id = ?", (statement_id,)).fetchone()
    if statement is None:
        raise ValueError("结算单不存在。")

    current_status = statement["status"]
    if current_status == "settled" and new_status != "settled":
        raise ValueError("已结清的结算单不能回退。")
    if current_status == "sent" and new_status == "draft":
        raise ValueError("已发送的结算单不能回退到草稿。")

    db.execute("UPDATE statements SET status = ? WHERE id = ?", (new_status, statement_id))
    if new_status == "settled":
        db.execute(
            """
            UPDATE orders
            SET status = 'closed'
            WHERE id IN (
                SELECT order_id
                FROM statement_orders
                WHERE statement_id = ?
            )
            """,
            (statement_id,),
        )
    db.commit()


def get_statement_orders(statement_id: int):
    db = get_db()
    return db.execute(
        """
        SELECT
            o.*,
            COALESCE(SUM(oi.subtotal_cents), 0) AS total_cents
        FROM statement_orders so
        JOIN orders o ON o.id = so.order_id
        LEFT JOIN order_items oi ON oi.order_id = o.id
        WHERE so.statement_id = ?
        GROUP BY o.id
        ORDER BY date(COALESCE(o.delivery_date, o.order_date)), o.id
        """,
        (statement_id,),
    ).fetchall()


def build_statement_csv(statement, customer, orders) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["结算单号", statement["statement_no"]])
    writer.writerow(["客户名称", customer["name"]])
    writer.writerow(["账期", statement["period_month"]])
    writer.writerow(["到期日", statement["due_date"]])
    writer.writerow([])
    writer.writerow(["订单号", "PO号", "订单日期", "发货日期", "订单状态", "金额"])
    for order in orders:
        writer.writerow(
            [
                order["order_no"],
                order["po_number"] or "",
                order["order_date"],
                order["delivery_date"] or "",
                ORDER_STATUSES.get(order["status"], order["status"]),
                f"{order['total_cents'] / 100:.2f}",
            ]
        )
    writer.writerow([])
    writer.writerow(["合计", f"{statement['total_amount_cents'] / 100:.2f}"])
    return output.getvalue()
