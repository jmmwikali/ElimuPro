"""Regenerate database/schema.sql from the SQLAlchemy models (PostgreSQL dialect)."""
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex

from app import create_app
from app.config import TestConfig
from app.extensions import db

app = create_app(TestConfig)
with app.app_context():
    out = ["-- ElimuNova PostgreSQL schema (generated from backend/app/models by export_schema.py)", ""]
    for t in db.metadata.sorted_tables:
        table_sql = str(CreateTable(t).compile(dialect=postgresql.dialect())).strip()
        out.append("\n".join(line.rstrip() for line in table_sql.splitlines()) + ";")
        for ix in t.indexes:
            index_sql = str(CreateIndex(ix).compile(dialect=postgresql.dialect())).strip()
            out.append("\n".join(line.rstrip() for line in index_sql.splitlines()) + ";")
        out.append("")
    output_path = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
    output_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(len(db.metadata.sorted_tables), "tables written")
