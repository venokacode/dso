from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app, g

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    account_code TEXT NOT NULL UNIQUE,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    billing_email TEXT NOT NULL,
    settlement_due_days INTEGER NOT NULL DEFAULT 30,
    credit_limit_cents INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    po_number TEXT,
    order_date TEXT NOT NULL,
    delivery_date TEXT,
    status TEXT NOT NULL CHECK(status IN ('draft', 'confirmed', 'shipped', 'monthly_billed', 'closed')),
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    item_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    subtotal_cents INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    period_month TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    total_amount_cents INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft', 'sent', 'settled')),
    created_at TEXT NOT NULL,
    UNIQUE(customer_id, period_month)
);

CREATE TABLE IF NOT EXISTS statement_orders (
    statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),
    PRIMARY KEY (statement_id, order_id)
);
"""


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_error: object | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    connection = get_db()
    connection.executescript(SCHEMA)
    connection.commit()


def seed_demo_data() -> None:
    connection = get_db()
    if connection.execute("SELECT 1 FROM customers LIMIT 1").fetchone():
        return

    created_at = _timestamp()
    connection.executemany(
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "华东连锁口腔集团",
                "EAST-DENTAL",
                "王敏",
                "wangmin@eastdental.example",
                "finance@eastdental.example",
                30,
                3_500_000_00,
                "标准月结客户，PO 必填。",
                1,
                created_at,
            ),
            (
                "北方口腔联合采购中心",
                "NORTH-DSO",
                "刘洋",
                "liuyang@northdso.example",
                "ap@northdso.example",
                45,
                5_000_000_00,
                "支持批量门店发货，统一月结。",
                1,
                created_at,
            ),
        ],
    )
    connection.executemany(
        """
        INSERT INTO products (sku, name, unit, unit_price_cents, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("IMPLANT-KIT", "种植耗材套装", "套", 128_000, created_at),
            ("ORTHO-BRACKET", "正畸托槽包", "盒", 48_500, created_at),
            ("SCAN-TIP", "口扫探头耗材", "支", 9_800, created_at),
        ],
    )
    connection.commit()


def ensure_database() -> None:
    database = current_app.config["DATABASE"]
    if database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)
    init_db()
    if current_app.config.get("DEMO_DATA", True):
        seed_demo_data()
