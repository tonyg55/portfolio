"""Database manager for running queries and migrations."""
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)


class DatabaseManager:
    """High-level manager for PostgreSQL operations."""

    def __init__(self, host: str, port: int, db_name: str,
                 username: str, password: str):
        self.dsn = {
            "host": host,
            "port": port,
            "dbname": db_name,
            "user": username,
            "password": password,
            "connect_timeout": 10,
        }

    @contextmanager
    def connection(self):
        conn = psycopg2.connect(**self.dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, sql: str, params=None) -> list[dict]:
        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                if cur.description:
                    return [dict(row) for row in cur.fetchall()]
                return []

    def server_version(self) -> str:
        rows = self.execute("SELECT version();")
        return rows[0]["version"] if rows else "unknown"

    def active_connections(self) -> int:
        rows = self.execute(
            "SELECT count(*) AS n FROM pg_stat_activity WHERE state = 'active';"
        )
        return rows[0]["n"] if rows else 0

    def database_size(self, db_name: str) -> str:
        rows = self.execute(
            "SELECT pg_size_pretty(pg_database_size(%s)) AS size;",
            (db_name,)
        )
        return rows[0]["size"] if rows else "unknown"

    def list_tables(self, schema: str = "public") -> list[str]:
        rows = self.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = %s ORDER BY tablename;",
            (schema,)
        )
        return [r["tablename"] for r in rows]

    def create_role(self, username: str, password: str, readonly: bool = False):
        """Create a database role with optional read-only access."""
        self.execute(f"CREATE ROLE {username} WITH LOGIN PASSWORD %s;", (password,))
        if readonly:
            self.execute(f"GRANT CONNECT ON DATABASE current_database() TO {username};")
            self.execute(f"GRANT USAGE ON SCHEMA public TO {username};")
            self.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {username};")
            log.info(f"Read-only role created: {username}")
        else:
            self.execute(f"GRANT ALL PRIVILEGES ON DATABASE current_database() TO {username};")
            log.info(f"Full-access role created: {username}")
