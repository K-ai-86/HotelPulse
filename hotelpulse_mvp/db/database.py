"""
Camada de acesso ao banco de dados.
Usa SQLAlchemy puro (Core), sem ORM, para manter o projeto simples
e fácil de entender/estender.
"""

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def init_db():
    """Cria as tabelas caso não existam. Idempotente."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # SQLite não entende SERIAL nem alguns tipos do Postgres —
    # fazemos uma adaptação simples para permitir testes locais.
    if DATABASE_URL.startswith("sqlite"):
        schema_sql = (
            schema_sql
            .replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
            .replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TEXT DEFAULT CURRENT_TIMESTAMP")
        )

    statements = [s.strip() for s in schema_sql.split(";") if s.strip()]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

    print(f"[db] Banco inicializado em: {DATABASE_URL}")


def run_query(sql, params=None):
    """Executa um SELECT e retorna lista de dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


def execute(sql, params=None):
    """Executa um INSERT/UPDATE/DELETE."""
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


if __name__ == "__main__":
    init_db()
