from __future__ import annotations

from pathlib import Path

from flask import Flask

from .db import init_app as init_db_app
from .db import init_schema
from .routes import api_bp


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE_PATH=str(Path(app.instance_path) / "dso_orders.sqlite3"),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    init_db_app(app)

    with app.app_context():
        init_schema()

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
