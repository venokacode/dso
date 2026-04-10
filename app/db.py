from __future__ import annotations

import sqlite3
from flask import current_app, g


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        billing_cycle TEXT NOT NULL DEFAULT 'monthly',
        credit_days INTEGER NOT NULL DEFAULT 30 CHECK(credit_days >= 0),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT NOT NULL UNIQUE,
        client_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
        status TEXT NOT NULL DEFAULT 'confirmed'
            CHECK(status IN ('confirmed', 'invoiced', 'cancelled')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT NOT NULL UNIQUE,
        client_id INTEGER NOT NULL,
        period TEXT NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        total_amount_cents INTEGER NOT NULL CHECK(total_amount_cents >= 0),
        status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'paid')),
        paid_at TEXT,
        settlement_ref TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(client_id, period),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS invoice_orders (
        invoice_id INTEGER NOT NULL,
        order_id INTEGER NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        PRIMARY KEY(invoice_id, order_id),
        FOREIGN KEY (invoice_id) REFERENCES invoices(id),
        FOREIGN KEY (order_id) REFERENCES orders(id)
    );
    """,
)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_schema() -> None:
    db = get_db()
    for stmt in SCHEMA_STATEMENTS:
        db.execute(stmt)
    db.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
