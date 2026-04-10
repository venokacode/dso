from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from sqlite3 import IntegrityError, Row

from flask import Blueprint, jsonify, request

from .db import get_db


api_bp = Blueprint("api", __name__)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 必须是 YYYY-MM-DD 格式") from exc


def _parse_period(value: str) -> tuple[date, date]:
    try:
        year_str, month_str = value.split("-")
        year, month = int(year_str), int(month_str)
        start = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end = date(year, month, last_day)
        return start, end
    except (ValueError, AttributeError) as exc:
        raise ValueError("period 必须是 YYYY-MM 格式") from exc


def _to_cents(amount: object) -> int:
    try:
        value = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("amount 必须是有效金额") from exc
    if value < 0:
        raise ValueError("amount 不能小于 0")
    return int(value * 100)


def _money(cents: int) -> str:
    return f"{cents / 100:.2f}"


def _error(message: str, status_code: int = 400):
    return jsonify({"error": message}), status_code


def _client_to_dict(row: Row) -> dict:
    return {
        "id": row["id"],
        "client_code": row["client_code"],
        "name": row["name"],
        "billing_cycle": row["billing_cycle"],
        "credit_days": row["credit_days"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


def _order_to_dict(row: Row) -> dict:
    return {
        "id": row["id"],
        "order_no": row["order_no"],
        "client_id": row["client_id"],
        "order_date": row["order_date"],
        "description": row["description"],
        "amount": _money(row["amount_cents"]),
        "status": row["status"],
        "created_at": row["created_at"],
    }


def _invoice_to_dict(row: Row, today: date | None = None) -> dict:
    today = today or date.today()
    due_date = _parse_date(row["due_date"], "due_date")
    is_overdue = row["status"] == "open" and due_date < today
    return {
        "id": row["id"],
        "invoice_no": row["invoice_no"],
        "client_id": row["client_id"],
        "client_code": row["client_code"],
        "client_name": row["client_name"],
        "period": row["period"],
        "issue_date": row["issue_date"],
        "due_date": row["due_date"],
        "total_amount": _money(row["total_amount_cents"]),
        "status": row["status"],
        "paid_at": row["paid_at"],
        "settlement_ref": row["settlement_ref"],
        "order_count": row["order_count"],
        "is_overdue": is_overdue,
        "created_at": row["created_at"],
    }


def _first_day_of_next_month(period_start: date) -> date:
    if period_start.month == 12:
        return date(period_start.year + 1, 1, 1)
    return date(period_start.year, period_start.month + 1, 1)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.post("/clients")
def create_client():
    payload = request.get_json(silent=True) or {}
    client_code = str(payload.get("client_code", "")).strip()
    name = str(payload.get("name", "")).strip()
    credit_days = payload.get("credit_days", 30)

    if not client_code:
        return _error("client_code 不能为空")
    if not name:
        return _error("name 不能为空")
    try:
        credit_days = int(credit_days)
    except (TypeError, ValueError):
        return _error("credit_days 必须是整数")
    if credit_days < 0:
        return _error("credit_days 不能小于 0")

    db = get_db()
    now = _utc_now_iso()
    try:
        cursor = db.execute(
            """
            INSERT INTO clients (client_code, name, billing_cycle, credit_days, is_active, created_at)
            VALUES (?, ?, 'monthly', ?, 1, ?)
            """,
            (client_code, name, credit_days, now),
        )
        db.commit()
    except IntegrityError:
        return _error("client_code 已存在", 409)

    row = db.execute("SELECT * FROM clients WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(_client_to_dict(row)), 201


@api_bp.get("/clients")
def list_clients():
    db = get_db()
    rows = db.execute("SELECT * FROM clients ORDER BY id ASC").fetchall()
    return jsonify([_client_to_dict(row) for row in rows])


@api_bp.post("/orders")
def create_order():
    payload = request.get_json(silent=True) or {}
    order_no = str(payload.get("order_no", "")).strip()
    description = str(payload.get("description", "")).strip()
    order_date_raw = payload.get("order_date")
    client_id = payload.get("client_id")

    if not order_no:
        return _error("order_no 不能为空")
    if not description:
        return _error("description 不能为空")
    if client_id is None:
        return _error("client_id 不能为空")
    try:
        client_id = int(client_id)
    except (TypeError, ValueError):
        return _error("client_id 必须是整数")
    if not isinstance(order_date_raw, str):
        return _error("order_date 不能为空")
    try:
        order_date = _parse_date(order_date_raw, "order_date")
        amount_cents = _to_cents(payload.get("amount"))
    except ValueError as exc:
        return _error(str(exc))

    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if client is None:
        return _error("client_id 不存在", 404)
    if not client["is_active"]:
        return _error("客户已停用", 400)

    now = _utc_now_iso()
    try:
        cursor = db.execute(
            """
            INSERT INTO orders (order_no, client_id, order_date, description, amount_cents, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'confirmed', ?)
            """,
            (order_no, client_id, order_date.isoformat(), description, amount_cents, now),
        )
        db.commit()
    except IntegrityError:
        return _error("order_no 已存在", 409)

    row = db.execute("SELECT * FROM orders WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(_order_to_dict(row)), 201


@api_bp.get("/orders")
def list_orders():
    client_id = request.args.get("client_id")
    status = request.args.get("status")
    period = request.args.get("period")

    query = "SELECT * FROM orders WHERE 1=1"
    params: list[object] = []

    if client_id:
        query += " AND client_id = ?"
        params.append(client_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if period:
        try:
            start, end = _parse_period(period)
        except ValueError as exc:
            return _error(str(exc))
        query += " AND order_date BETWEEN ? AND ?"
        params.extend([start.isoformat(), end.isoformat()])

    query += " ORDER BY order_date DESC, id DESC"
    db = get_db()
    rows = db.execute(query, params).fetchall()
    return jsonify([_order_to_dict(row) for row in rows])


@api_bp.post("/invoices/generate")
def generate_invoice():
    payload = request.get_json(silent=True) or {}
    client_id = payload.get("client_id")
    period = payload.get("period")
    if client_id is None:
        return _error("client_id 不能为空")
    if not isinstance(period, str):
        return _error("period 不能为空")

    try:
        client_id = int(client_id)
        start, end = _parse_period(period)
    except ValueError as exc:
        return _error(str(exc))

    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if client is None:
        return _error("client_id 不存在", 404)

    exists = db.execute(
        "SELECT id FROM invoices WHERE client_id = ? AND period = ?",
        (client_id, period),
    ).fetchone()
    if exists is not None:
        return _error("该客户在该结算月已经出账", 409)

    billable_orders = db.execute(
        """
        SELECT o.id, o.amount_cents
        FROM orders o
        LEFT JOIN invoice_orders io ON io.order_id = o.id
        WHERE o.client_id = ?
          AND o.status = 'confirmed'
          AND io.order_id IS NULL
          AND o.order_date BETWEEN ? AND ?
        ORDER BY o.order_date ASC, o.id ASC
        """,
        (client_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    if not billable_orders:
        return _error("没有可出账订单", 400)

    issue_date_raw = payload.get("issue_date")
    due_date_raw = payload.get("due_date")
    try:
        issue_date = (
            _parse_date(issue_date_raw, "issue_date")
            if issue_date_raw
            else _first_day_of_next_month(start)
        )
        due_date = (
            _parse_date(due_date_raw, "due_date")
            if due_date_raw
            else issue_date + timedelta(days=client["credit_days"])
        )
    except ValueError as exc:
        return _error(str(exc))
    if due_date < issue_date:
        return _error("due_date 不能早于 issue_date")

    total_amount_cents = sum(row["amount_cents"] for row in billable_orders)
    seq_row = db.execute("SELECT COUNT(*) AS count FROM invoices WHERE period = ?", (period,)).fetchone()
    sequence = seq_row["count"] + 1
    invoice_no = f"INV-{period.replace('-', '')}-{client['client_code']}-{sequence:03d}"
    now = _utc_now_iso()

    try:
        cursor = db.execute(
            """
            INSERT INTO invoices (
                invoice_no, client_id, period, issue_date, due_date,
                total_amount_cents, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                invoice_no,
                client_id,
                period,
                issue_date.isoformat(),
                due_date.isoformat(),
                total_amount_cents,
                now,
            ),
        )
        invoice_id = cursor.lastrowid
        for row in billable_orders:
            db.execute(
                """
                INSERT INTO invoice_orders (invoice_id, order_id, created_at)
                VALUES (?, ?, ?)
                """,
                (invoice_id, row["id"], now),
            )
            db.execute("UPDATE orders SET status = 'invoiced' WHERE id = ?", (row["id"],))
        db.commit()
    except IntegrityError:
        db.rollback()
        return _error("出账失败，请重试", 409)

    invoice = db.execute(
        """
        SELECT i.*, c.client_code, c.name AS client_name, COUNT(io.order_id) AS order_count
        FROM invoices i
        JOIN clients c ON c.id = i.client_id
        LEFT JOIN invoice_orders io ON io.invoice_id = i.id
        WHERE i.id = ?
        GROUP BY i.id
        """,
        (invoice_id,),
    ).fetchone()
    return jsonify(_invoice_to_dict(invoice))


@api_bp.get("/invoices")
def list_invoices():
    client_id = request.args.get("client_id")
    period = request.args.get("period")
    status = request.args.get("status")

    query = """
        SELECT i.*, c.client_code, c.name AS client_name, COUNT(io.order_id) AS order_count
        FROM invoices i
        JOIN clients c ON c.id = i.client_id
        LEFT JOIN invoice_orders io ON io.invoice_id = i.id
        WHERE 1=1
    """
    params: list[object] = []
    if client_id:
        query += " AND i.client_id = ?"
        params.append(client_id)
    if period:
        query += " AND i.period = ?"
        params.append(period)
    if status:
        query += " AND i.status = ?"
        params.append(status)

    query += " GROUP BY i.id ORDER BY i.issue_date DESC, i.id DESC"
    db = get_db()
    rows = db.execute(query, params).fetchall()
    today = date.today()
    return jsonify([_invoice_to_dict(row, today=today) for row in rows])


@api_bp.post("/invoices/<int:invoice_id>/mark-paid")
def mark_invoice_paid(invoice_id: int):
    payload = request.get_json(silent=True) or {}
    settlement_ref = str(payload.get("settlement_ref", "")).strip() or None
    paid_at_raw = payload.get("paid_at")
    if paid_at_raw is None:
        paid_at = date.today().isoformat()
    else:
        if not isinstance(paid_at_raw, str):
            return _error("paid_at 必须是 YYYY-MM-DD 格式")
        try:
            paid_at = _parse_date(paid_at_raw, "paid_at").isoformat()
        except ValueError as exc:
            return _error(str(exc))

    db = get_db()
    invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if invoice is None:
        return _error("invoice 不存在", 404)
    if invoice["status"] == "paid":
        return _error("invoice 已结清", 409)

    db.execute(
        """
        UPDATE invoices
        SET status = 'paid', paid_at = ?, settlement_ref = ?
        WHERE id = ?
        """,
        (paid_at, settlement_ref, invoice_id),
    )
    db.commit()

    row = db.execute(
        """
        SELECT i.*, c.client_code, c.name AS client_name, COUNT(io.order_id) AS order_count
        FROM invoices i
        JOIN clients c ON c.id = i.client_id
        LEFT JOIN invoice_orders io ON io.invoice_id = i.id
        WHERE i.id = ?
        GROUP BY i.id
        """,
        (invoice_id,),
    ).fetchone()
    return jsonify(_invoice_to_dict(row))


@api_bp.get("/receivables/summary")
def receivables_summary():
    db = get_db()
    rows = db.execute(
        """
        SELECT
            i.client_id,
            c.client_code,
            c.name AS client_name,
            i.total_amount_cents,
            i.due_date
        FROM invoices i
        JOIN clients c ON c.id = i.client_id
        WHERE i.status = 'open'
        """
    ).fetchall()

    today = date.today()
    total_open = 0
    total_overdue = 0
    per_client: dict[int, dict] = {}

    for row in rows:
        amount = row["total_amount_cents"]
        total_open += amount
        is_overdue = _parse_date(row["due_date"], "due_date") < today
        if is_overdue:
            total_overdue += amount
        client_data = per_client.setdefault(
            row["client_id"],
            {
                "client_id": row["client_id"],
                "client_code": row["client_code"],
                "client_name": row["client_name"],
                "open_amount_cents": 0,
                "overdue_amount_cents": 0,
                "open_invoice_count": 0,
            },
        )
        client_data["open_amount_cents"] += amount
        client_data["open_invoice_count"] += 1
        if is_overdue:
            client_data["overdue_amount_cents"] += amount

    breakdown = sorted(
        (
            {
                "client_id": item["client_id"],
                "client_code": item["client_code"],
                "client_name": item["client_name"],
                "open_amount": _money(item["open_amount_cents"]),
                "overdue_amount": _money(item["overdue_amount_cents"]),
                "open_invoice_count": item["open_invoice_count"],
            }
            for item in per_client.values()
        ),
        key=lambda x: (Decimal(x["open_amount"]), x["client_id"]),
        reverse=True,
    )

    return jsonify(
        {
            "currency": "CNY",
            "open_amount": _money(total_open),
            "overdue_amount": _money(total_overdue),
            "client_breakdown": breakdown,
        }
    )
