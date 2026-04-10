from __future__ import annotations

import os
import sqlite3
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import click
from flask import Flask, Response, abort, flash, redirect, render_template, request, url_for

from .db import close_db, ensure_database, get_db, init_db, seed_demo_data
from .services import (
    ORDER_STATUSES,
    STATEMENT_STATUSES,
    build_statement_csv,
    cents_to_display,
    create_or_update_statement,
    generate_order_no,
    get_statement_orders,
    parse_money_to_cents,
    parse_quantity,
    quantity_to_display,
    recalculate_statement_total,
    timestamp,
    today_iso,
    update_statement_status,
)


def _require_text(value: str | None, label: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空。")
    return text


def _normalize_date(value: str | None, label: str, *, required: bool) -> str | None:
    text = (value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{label}不能为空。")
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError(f"{label}格式不正确。") from exc


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dso-order-system-dev",
        DATABASE=os.path.join(app.instance_path, "dso.sqlite3"),
        DEMO_DATA=True,
    )

    if test_config is not None:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)
    app.add_template_filter(cents_to_display, "currency")
    app.add_template_filter(quantity_to_display, "qty")

    @app.context_processor
    def inject_common_context() -> dict[str, object]:
        return {
            "order_statuses": ORDER_STATUSES,
            "statement_statuses": STATEMENT_STATUSES,
            "today_iso": today_iso(),
        }

    @app.cli.command("init-db")
    def init_db_command() -> None:
        with app.app_context():
            init_db()
            if app.config.get("DEMO_DATA", True):
                seed_demo_data()
        click.echo("Database initialized.")

    with app.app_context():
        ensure_database()

    @app.get("/")
    def dashboard():
        db = get_db()
        current_month = date.today().strftime("%Y-%m")
        metrics = {
            "customer_count": db.execute(
                "SELECT COUNT(*) AS count FROM customers WHERE active = 1"
            ).fetchone()["count"],
            "open_orders": db.execute(
                """
                SELECT COUNT(*) AS count
                FROM orders
                WHERE status IN ('draft', 'confirmed', 'shipped', 'monthly_billed')
                """
            ).fetchone()["count"],
            "pending_shipments": db.execute(
                "SELECT COUNT(*) AS count FROM orders WHERE status = 'confirmed'"
            ).fetchone()["count"],
            "statement_total": db.execute(
                "SELECT COALESCE(SUM(total_amount_cents), 0) AS total FROM statements WHERE period_month = ?",
                (current_month,),
            ).fetchone()["total"],
        }
        recent_orders = db.execute(
            """
            SELECT
                o.*,
                c.name AS customer_name,
                COALESCE(SUM(oi.subtotal_cents), 0) AS total_cents
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            GROUP BY o.id
            ORDER BY date(o.order_date) DESC, o.id DESC
            LIMIT 6
            """
        ).fetchall()
        recent_statements = db.execute(
            """
            SELECT
                s.*,
                c.name AS customer_name
            FROM statements s
            JOIN customers c ON c.id = s.customer_id
            ORDER BY s.period_month DESC, s.id DESC
            LIMIT 6
            """
        ).fetchall()
        customers = db.execute(
            "SELECT id, name, account_code FROM customers WHERE active = 1 ORDER BY name"
        ).fetchall()
        return render_template(
            "dashboard.html",
            metrics=metrics,
            recent_orders=recent_orders,
            recent_statements=recent_statements,
            customers=customers,
            current_month=current_month,
        )

    @app.route("/customers", methods=["GET", "POST"])
    def customers():
        db = get_db()
        if request.method == "POST":
            try:
                name = _require_text(request.form.get("name"), "客户名称")
                account_code = _require_text(request.form.get("account_code"), "客户编码").upper()
                contact_name = _require_text(request.form.get("contact_name"), "商务联系人")
                contact_email = _require_text(request.form.get("contact_email"), "商务邮箱")
                billing_email = _require_text(request.form.get("billing_email"), "财务邮箱")
                settlement_due_days = int(request.form.get("settlement_due_days", "30"))
                if settlement_due_days <= 0:
                    raise ValueError("账期天数必须大于 0。")
                credit_limit_raw = (request.form.get("credit_limit") or "0").strip() or "0"
                credit_limit_cents = parse_money_to_cents(credit_limit_raw)
                notes = (request.form.get("notes") or "").strip()
                db.execute(
                    """
                    INSERT INTO customers (
                        name,
                        account_code,
                        contact_name,
                        contact_email,
                        billing_email,
                        settlement_due_days,
                        credit_limit_cents,
                        notes,
                        active,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        name,
                        account_code,
                        contact_name,
                        contact_email,
                        billing_email,
                        settlement_due_days,
                        credit_limit_cents,
                        notes,
                        timestamp(),
                    ),
                )
                db.commit()
                flash("DSO 客户已创建。", "success")
            except ValueError as exc:
                flash(str(exc), "error")
            except sqlite3.IntegrityError:
                flash("客户编码已存在，请更换后重试。", "error")
            return redirect(url_for("customers"))

        customer_rows = db.execute(
            "SELECT * FROM customers ORDER BY active DESC, name ASC"
        ).fetchall()
        return render_template("customers.html", customers=customer_rows)

    @app.route("/products", methods=["GET", "POST"])
    def products():
        db = get_db()
        if request.method == "POST":
            try:
                sku = _require_text(request.form.get("sku"), "SKU").upper()
                name = _require_text(request.form.get("name"), "商品名称")
                unit = _require_text(request.form.get("unit"), "单位")
                unit_price_cents = parse_money_to_cents(request.form.get("unit_price") or "")
                db.execute(
                    """
                    INSERT INTO products (sku, name, unit, unit_price_cents, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (sku, name, unit, unit_price_cents, timestamp()),
                )
                db.commit()
                flash("商品目录已更新。", "success")
            except ValueError as exc:
                flash(str(exc), "error")
            except sqlite3.IntegrityError:
                flash("SKU 已存在，请换一个编码。", "error")
            return redirect(url_for("products"))

        product_rows = db.execute("SELECT * FROM products ORDER BY name ASC").fetchall()
        return render_template("products.html", products=product_rows)

    @app.get("/orders")
    def orders():
        db = get_db()
        order_rows = db.execute(
            """
            SELECT
                o.*,
                c.name AS customer_name,
                COALESCE(SUM(oi.subtotal_cents), 0) AS total_cents,
                COUNT(oi.id) AS line_count
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            GROUP BY o.id
            ORDER BY date(o.order_date) DESC, o.id DESC
            """
        ).fetchall()
        return render_template("orders.html", orders=order_rows)

    @app.get("/orders/new")
    def new_order():
        db = get_db()
        customer_rows = db.execute(
            "SELECT id, name, account_code FROM customers WHERE active = 1 ORDER BY name ASC"
        ).fetchall()
        product_rows = db.execute("SELECT * FROM products ORDER BY name ASC").fetchall()
        return render_template(
            "order_form.html",
            customers=customer_rows,
            products=product_rows,
        )

    @app.post("/orders")
    def create_order():
        db = get_db()
        try:
            customer_id = int(request.form.get("customer_id", "0"))
            customer = db.execute(
                "SELECT id FROM customers WHERE id = ? AND active = 1", (customer_id,)
            ).fetchone()
            if customer is None:
                raise ValueError("请选择有效客户。")

            status = request.form.get("status", "draft")
            if status not in {"draft", "confirmed", "shipped"}:
                raise ValueError("订单状态不合法。")

            order_date = _normalize_date(request.form.get("order_date"), "订单日期", required=True)
            delivery_date = _normalize_date(
                request.form.get("delivery_date"), "发货日期", required=False
            )
            po_number = (request.form.get("po_number") or "").strip()
            notes = (request.form.get("notes") or "").strip()

            product_ids = request.form.getlist("product_id")
            item_names = request.form.getlist("item_name")
            item_units = request.form.getlist("item_unit")
            item_quantities = request.form.getlist("item_quantity")
            item_prices = request.form.getlist("item_price")
            row_count = max(
                len(product_ids),
                len(item_names),
                len(item_units),
                len(item_quantities),
                len(item_prices),
            )
            if row_count == 0:
                raise ValueError("请至少录入一条订单明细。")

            selected_product_ids = sorted(
                {int(raw_id) for raw_id in product_ids if (raw_id or "").strip()}
            )
            products_by_id = {}
            if selected_product_ids:
                placeholders = ",".join(["?"] * len(selected_product_ids))
                product_rows = db.execute(
                    f"SELECT * FROM products WHERE id IN ({placeholders})",
                    tuple(selected_product_ids),
                ).fetchall()
                products_by_id = {product["id"]: product for product in product_rows}

            items: list[tuple[int | None, str, str, float, int, int]] = []
            for index in range(row_count):
                raw_product_id = product_ids[index] if index < len(product_ids) else ""
                raw_name = item_names[index] if index < len(item_names) else ""
                raw_unit = item_units[index] if index < len(item_units) else ""
                raw_quantity = item_quantities[index] if index < len(item_quantities) else ""
                raw_price = item_prices[index] if index < len(item_prices) else ""

                if not any(
                    [
                        (raw_product_id or "").strip(),
                        (raw_name or "").strip(),
                        (raw_unit or "").strip(),
                        (raw_quantity or "").strip(),
                        (raw_price or "").strip(),
                    ]
                ):
                    continue

                product = None
                if (raw_product_id or "").strip():
                    product_id = int(raw_product_id)
                    product = products_by_id.get(product_id)
                    if product is None:
                        raise ValueError("订单中包含不存在的商品。")

                item_name = (raw_name or "").strip() or (product["name"] if product else "")
                item_unit = (raw_unit or "").strip() or (product["unit"] if product else "")
                if not item_name:
                    raise ValueError("订单明细名称不能为空。")
                if not item_unit:
                    raise ValueError("订单明细单位不能为空。")

                quantity = parse_quantity(raw_quantity)
                if (raw_price or "").strip():
                    unit_price_cents = parse_money_to_cents(raw_price)
                elif product is not None:
                    unit_price_cents = int(product["unit_price_cents"])
                else:
                    raise ValueError("订单明细单价不能为空。")

                subtotal_cents = int(
                    (quantity * Decimal(unit_price_cents)).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                )
                items.append(
                    (
                        int(product["id"]) if product is not None else None,
                        item_name,
                        item_unit,
                        float(quantity),
                        unit_price_cents,
                        subtotal_cents,
                    )
                )

            if not items:
                raise ValueError("请至少录入一条有效的订单明细。")

            cursor = db.execute(
                """
                INSERT INTO orders (
                    order_no,
                    customer_id,
                    po_number,
                    order_date,
                    delivery_date,
                    status,
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generate_order_no(),
                    customer_id,
                    po_number,
                    order_date,
                    delivery_date,
                    status,
                    notes,
                    timestamp(),
                ),
            )
            order_id = int(cursor.lastrowid)
            db.executemany(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    item_name,
                    unit,
                    quantity,
                    unit_price_cents,
                    subtotal_cents
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [(order_id, *item) for item in items],
            )
            db.commit()
            flash("订单已创建，可继续推进发货和月结流程。", "success")
            return redirect(url_for("orders"))
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("new_order"))

    @app.post("/orders/<int:order_id>/status")
    def update_order(order_id: int):
        db = get_db()
        order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if order is None:
            abort(404)

        linked_statement = db.execute(
            "SELECT statement_id FROM statement_orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        if linked_statement is not None:
            flash("订单已经纳入月结，请通过结算单推进后续状态。", "error")
            return redirect(url_for("orders"))

        new_status = request.form.get("status", "")
        if new_status not in {"draft", "confirmed", "shipped"}:
            flash("订单状态不合法。", "error")
            return redirect(url_for("orders"))

        db.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        db.commit()
        flash("订单状态已更新。", "success")
        return redirect(url_for("orders"))

    @app.get("/statements")
    def statements():
        db = get_db()
        statement_rows = db.execute(
            """
            SELECT
                s.*,
                c.name AS customer_name,
                c.account_code AS customer_code
            FROM statements s
            JOIN customers c ON c.id = s.customer_id
            ORDER BY s.period_month DESC, s.id DESC
            """
        ).fetchall()
        customer_rows = db.execute(
            "SELECT id, name, account_code FROM customers WHERE active = 1 ORDER BY name ASC"
        ).fetchall()
        return render_template(
            "statements.html",
            statements=statement_rows,
            customers=customer_rows,
            current_month=date.today().strftime("%Y-%m"),
        )

    @app.post("/statements/generate")
    def generate_statement():
        try:
            customer_id = int(request.form.get("customer_id", "0"))
            period_month = _require_text(request.form.get("period_month"), "账期")
            statement_id = create_or_update_statement(customer_id, period_month)
            flash("月结算单已生成。", "success")
            return redirect(url_for("statement_detail", statement_id=statement_id))
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("statements"))

    @app.get("/statements/<int:statement_id>")
    def statement_detail(statement_id: int):
        db = get_db()
        statement = db.execute(
            """
            SELECT
                s.*,
                c.name AS customer_name,
                c.account_code AS customer_code,
                c.billing_email,
                c.settlement_due_days
            FROM statements s
            JOIN customers c ON c.id = s.customer_id
            WHERE s.id = ?
            """,
            (statement_id,),
        ).fetchone()
        if statement is None:
            abort(404)

        orders = get_statement_orders(statement_id)
        if statement["total_amount_cents"] == 0:
            recalculate_statement_total(statement_id)
            db.commit()
            statement = db.execute(
                """
                SELECT
                    s.*,
                    c.name AS customer_name,
                    c.account_code AS customer_code,
                    c.billing_email,
                    c.settlement_due_days
                FROM statements s
                JOIN customers c ON c.id = s.customer_id
                WHERE s.id = ?
                """,
                (statement_id,),
            ).fetchone()
        return render_template(
            "statement_detail.html",
            statement=statement,
            orders=orders,
        )

    @app.post("/statements/<int:statement_id>/status")
    def set_statement_status(statement_id: int):
        try:
            new_status = request.form.get("status", "")
            update_statement_status(statement_id, new_status)
            flash("结算单状态已更新。", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("statement_detail", statement_id=statement_id))

    @app.get("/statements/<int:statement_id>/export")
    def export_statement(statement_id: int):
        db = get_db()
        statement = db.execute(
            "SELECT * FROM statements WHERE id = ?", (statement_id,)
        ).fetchone()
        if statement is None:
            abort(404)
        customer = db.execute(
            "SELECT * FROM customers WHERE id = ?", (statement["customer_id"],)
        ).fetchone()
        orders = get_statement_orders(statement_id)
        csv_content = build_statement_csv(statement, customer, orders)
        filename = f"{statement['statement_no']}.csv"
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app
