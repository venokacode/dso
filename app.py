import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for

ORDER_STATUS_LABELS = {
    "pending": "待处理",
    "confirmed": "已确认",
    "delivered": "已交付",
    "cancelled": "已取消",
}

STATEMENT_STATUS_LABELS = {
    "open": "待发送",
    "sent": "已发送",
    "settled": "已结清",
}


def format_money(value):
    return f"{float(value or 0):,.2f}"


def month_window(billing_month):
    start = datetime.strptime(billing_month, "%Y-%m").date().replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start.isoformat(), end.isoformat()


def init_database(database_path):
    connection = sqlite3.connect(database_path)
    try:
        schema = Path(__file__).with_name("schema.sql")
        connection.executescript(schema.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dso-dev",
        DATABASE=str(Path(app.instance_path) / "dso.sqlite3"),
        SEED_DEMO_DATA=True,
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        schema = Path(app.root_path) / "schema.sql"
        db.executescript(schema.read_text(encoding="utf-8"))
        db.commit()

    def seed_demo_data():
        db = get_db()
        existing = db.execute("SELECT COUNT(*) AS count FROM customers").fetchone()["count"]
        if existing:
            return

        customers = [
            (
                "华东口腔连锁集团",
                "DSO-001",
                "周倩",
                "zhouqian@example.com",
                "月结 30 天",
                30,
                "区域型大客户，统一月结。",
            ),
            (
                "北方齿科管理公司",
                "DSO-002",
                "刘洋",
                "liuyang@example.com",
                "月结 45 天",
                45,
                "总部集中采购，门店分批交付。",
            ),
        ]

        db.executemany(
            """
            INSERT INTO customers (
                name,
                customer_code,
                contact_name,
                contact_email,
                credit_terms,
                billing_day,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            customers,
        )

        customer_ids = {
            row["customer_code"]: row["id"]
            for row in db.execute("SELECT id, customer_code FROM customers").fetchall()
        }
        demo_orders = [
            (
                customer_ids["DSO-001"],
                "隐形矫治器批量采购",
                20,
                2600,
                "2026-04-02",
                "2026-04-05",
                "delivered",
                "总部统一下单，按门店拆分履约。",
            ),
            (
                customer_ids["DSO-001"],
                "种植体套装",
                12,
                1850,
                "2026-04-06",
                "2026-04-09",
                "delivered",
                "",
            ),
            (
                customer_ids["DSO-002"],
                "数字化扫描服务包",
                5,
                6800,
                "2026-04-07",
                "",
                "confirmed",
                "等待客户安排实施时间。",
            ),
        ]

        db.executemany(
            """
            INSERT INTO orders (
                customer_id,
                item_name,
                quantity,
                unit_price,
                order_date,
                delivery_date,
                status,
                remarks
            ) VALUES (?, ?, ?, ?, ?, NULLIF(?, ''), ?, ?)
            """,
            demo_orders,
        )
        db.commit()

    app.teardown_appcontext(close_db)
    app.get_db = get_db
    app.init_db = init_db
    app.seed_demo_data = seed_demo_data

    @app.context_processor
    def inject_helpers():
        return {
            "format_money": format_money,
            "order_status_labels": ORDER_STATUS_LABELS,
            "statement_status_labels": STATEMENT_STATUS_LABELS,
        }

    @app.route("/")
    def dashboard():
        db = get_db()
        current_month = date.today().strftime("%Y-%m")

        metrics = {
            "customer_count": db.execute(
                "SELECT COUNT(*) AS count FROM customers"
            ).fetchone()["count"],
            "active_order_count": db.execute(
                "SELECT COUNT(*) AS count FROM orders WHERE status != 'cancelled'"
            ).fetchone()["count"],
            "pending_billing_amount": db.execute(
                """
                SELECT COALESCE(SUM(quantity * unit_price), 0) AS total
                FROM orders
                WHERE status = 'delivered' AND statement_id IS NULL
                """
            ).fetchone()["total"],
            "current_month_statement_total": db.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total
                FROM statements
                WHERE billing_month = ?
                """,
                (current_month,),
            ).fetchone()["total"],
        }

        recent_orders = db.execute(
            """
            SELECT
                o.*,
                c.name AS customer_name,
                c.customer_code,
                s.billing_month,
                s.status AS statement_status
            FROM orders AS o
            JOIN customers AS c ON c.id = o.customer_id
            LEFT JOIN statements AS s ON s.id = o.statement_id
            ORDER BY COALESCE(o.delivery_date, o.order_date) DESC, o.id DESC
            LIMIT 8
            """
        ).fetchall()

        open_statements = db.execute(
            """
            SELECT
                s.*,
                c.name AS customer_name,
                c.customer_code,
                COUNT(o.id) AS order_count
            FROM statements AS s
            JOIN customers AS c ON c.id = s.customer_id
            LEFT JOIN orders AS o ON o.statement_id = s.id
            GROUP BY s.id
            ORDER BY s.billing_month DESC, s.id DESC
            LIMIT 8
            """
        ).fetchall()

        return render_template(
            "dashboard.html",
            metrics=metrics,
            recent_orders=recent_orders,
            open_statements=open_statements,
            current_month=current_month,
        )

    @app.route("/customers", methods=("GET", "POST"))
    def customers():
        db = get_db()

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            customer_code = request.form.get("customer_code", "").strip().upper()
            contact_name = request.form.get("contact_name", "").strip()
            contact_email = request.form.get("contact_email", "").strip()
            credit_terms = request.form.get("credit_terms", "").strip() or "月结 30 天"
            notes = request.form.get("notes", "").strip()

            try:
                billing_day = int(request.form.get("billing_day", "30") or 30)
            except ValueError:
                billing_day = 30

            if not name or not customer_code:
                flash("客户名称和客户编号不能为空。", "error")
            else:
                try:
                    db.execute(
                        """
                        INSERT INTO customers (
                            name,
                            customer_code,
                            contact_name,
                            contact_email,
                            credit_terms,
                            billing_day,
                            notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            name,
                            customer_code,
                            contact_name,
                            contact_email,
                            credit_terms,
                            billing_day,
                            notes,
                        ),
                    )
                    db.commit()
                    flash("客户已创建。", "success")
                    return redirect(url_for("customers"))
                except sqlite3.IntegrityError:
                    flash("客户编号已存在，请使用新的编号。", "error")

        customer_rows = db.execute(
            """
            SELECT
                c.*,
                COUNT(o.id) AS order_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN o.status = 'delivered' AND o.statement_id IS NULL
                            THEN o.quantity * o.unit_price
                            ELSE 0
                        END
                    ),
                    0
                ) AS pending_amount
            FROM customers AS c
            LEFT JOIN orders AS o ON o.customer_id = c.id
            GROUP BY c.id
            ORDER BY c.id DESC
            """
        ).fetchall()

        return render_template("customers.html", customers=customer_rows)

    @app.route("/orders", methods=("GET", "POST"))
    def orders():
        db = get_db()
        customer_rows = db.execute(
            "SELECT id, name, customer_code FROM customers ORDER BY name"
        ).fetchall()

        if request.method == "POST":
            if not customer_rows:
                flash("请先创建客户，再录入订单。", "error")
                return redirect(url_for("customers"))

            customer_id = request.form.get("customer_id", "").strip()
            item_name = request.form.get("item_name", "").strip()
            order_date = request.form.get("order_date", "").strip() or date.today().isoformat()
            delivery_date = request.form.get("delivery_date", "").strip()
            status = request.form.get("status", "pending").strip()
            remarks = request.form.get("remarks", "").strip()

            try:
                quantity = float(request.form.get("quantity", "0"))
                unit_price = float(request.form.get("unit_price", "0"))
            except ValueError:
                flash("数量和单价必须是数字。", "error")
                return redirect(url_for("orders"))

            if not customer_id or not item_name:
                flash("客户和订单项目不能为空。", "error")
            elif quantity <= 0 or unit_price < 0:
                flash("数量必须大于 0，单价不能为负。", "error")
            elif status == "delivered" and not delivery_date:
                flash("已交付订单必须填写交付日期。", "error")
            else:
                db.execute(
                    """
                    INSERT INTO orders (
                        customer_id,
                        item_name,
                        quantity,
                        unit_price,
                        order_date,
                        delivery_date,
                        status,
                        remarks
                    ) VALUES (?, ?, ?, ?, ?, NULLIF(?, ''), ?, ?)
                    """,
                    (
                        int(customer_id),
                        item_name,
                        quantity,
                        unit_price,
                        order_date,
                        delivery_date,
                        status,
                        remarks,
                    ),
                )
                db.commit()
                flash("订单已录入。", "success")
                return redirect(url_for("orders"))

        order_rows = db.execute(
            """
            SELECT
                o.*,
                c.name AS customer_name,
                c.customer_code,
                s.billing_month,
                s.status AS statement_status
            FROM orders AS o
            JOIN customers AS c ON c.id = o.customer_id
            LEFT JOIN statements AS s ON s.id = o.statement_id
            ORDER BY o.id DESC
            """
        ).fetchall()

        return render_template(
            "orders.html",
            customers=customer_rows,
            orders=order_rows,
            today=date.today().isoformat(),
        )

    @app.route("/statements", methods=("GET", "POST"))
    def statements():
        db = get_db()

        if request.method == "POST":
            customer_id = request.form.get("customer_id", "").strip()
            billing_month = request.form.get("billing_month", "").strip()

            if not customer_id or not billing_month:
                flash("请选择客户和账单月份。", "error")
                return redirect(url_for("statements"))

            try:
                start_date, end_date = month_window(billing_month)
            except ValueError:
                flash("账单月份格式不正确，应为 YYYY-MM。", "error")
                return redirect(url_for("statements"))

            existing = db.execute(
                """
                SELECT id
                FROM statements
                WHERE customer_id = ? AND billing_month = ?
                """,
                (int(customer_id), billing_month),
            ).fetchone()
            if existing:
                flash("该客户该月份的月结对账单已存在。", "error")
                return redirect(url_for("statement_detail", statement_id=existing["id"]))

            eligible_orders = db.execute(
                """
                SELECT
                    id,
                    quantity * unit_price AS line_total
                FROM orders
                WHERE customer_id = ?
                  AND status = 'delivered'
                  AND statement_id IS NULL
                  AND delivery_date >= ?
                  AND delivery_date < ?
                ORDER BY delivery_date, id
                """,
                (int(customer_id), start_date, end_date),
            ).fetchall()

            if not eligible_orders:
                flash("该月份没有可出账的已交付订单。", "error")
                return redirect(url_for("statements"))

            total_amount = sum(row["line_total"] for row in eligible_orders)
            cursor = db.execute(
                """
                INSERT INTO statements (
                    customer_id,
                    billing_month,
                    total_amount,
                    status
                ) VALUES (?, ?, ?, 'open')
                """,
                (int(customer_id), billing_month, total_amount),
            )
            statement_id = cursor.lastrowid

            db.executemany(
                "UPDATE orders SET statement_id = ? WHERE id = ?",
                [(statement_id, row["id"]) for row in eligible_orders],
            )
            db.commit()

            flash("月结对账单已生成。", "success")
            return redirect(url_for("statement_detail", statement_id=statement_id))

        customer_rows = db.execute(
            "SELECT id, name, customer_code FROM customers ORDER BY name"
        ).fetchall()
        statement_rows = db.execute(
            """
            SELECT
                s.*,
                c.name AS customer_name,
                c.customer_code,
                COUNT(o.id) AS order_count
            FROM statements AS s
            JOIN customers AS c ON c.id = s.customer_id
            LEFT JOIN orders AS o ON o.statement_id = s.id
            GROUP BY s.id
            ORDER BY s.billing_month DESC, s.id DESC
            """
        ).fetchall()

        return render_template(
            "statements.html",
            customers=customer_rows,
            statements=statement_rows,
            default_billing_month=date.today().strftime("%Y-%m"),
        )

    @app.route("/statements/<int:statement_id>")
    def statement_detail(statement_id):
        db = get_db()
        statement = db.execute(
            """
            SELECT
                s.*,
                c.name AS customer_name,
                c.customer_code,
                c.contact_name,
                c.contact_email,
                c.credit_terms
            FROM statements AS s
            JOIN customers AS c ON c.id = s.customer_id
            WHERE s.id = ?
            """,
            (statement_id,),
        ).fetchone()

        if statement is None:
            flash("未找到该对账单。", "error")
            return redirect(url_for("statements"))

        line_items = db.execute(
            """
            SELECT *
            FROM orders
            WHERE statement_id = ?
            ORDER BY delivery_date, id
            """,
            (statement_id,),
        ).fetchall()

        return render_template(
            "statement_detail.html",
            statement=statement,
            line_items=line_items,
        )

    @app.post("/statements/<int:statement_id>/status")
    def update_statement_status(statement_id):
        db = get_db()
        new_status = request.form.get("status", "").strip()
        if new_status not in STATEMENT_STATUS_LABELS:
            flash("无效的账单状态。", "error")
            return redirect(url_for("statement_detail", statement_id=statement_id))

        db.execute(
            "UPDATE statements SET status = ? WHERE id = ?",
            (new_status, statement_id),
        )
        db.commit()
        flash("账单状态已更新。", "success")
        return redirect(url_for("statement_detail", statement_id=statement_id))

    with app.app_context():
        database_path = Path(app.config["DATABASE"])
        first_boot = not database_path.exists()
        init_db()
        if first_boot and app.config["SEED_DEMO_DATA"]:
            seed_demo_data()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
