"""Health checks for PostgreSQL instances."""
import logging
import socket
import time

import psycopg2

log = logging.getLogger(__name__)


class HealthChecker:
    """Runs a suite of health checks against a PostgreSQL instance."""

    def __init__(self, host: str, port: int, db_name: str,
                 username: str, password: str):
        self.host = host
        self.port = port
        self.db_name = db_name
        self.username = username
        self.password = password

    def run_all(self) -> list[dict]:
        checks = [
            ("TCP Connectivity", self._check_tcp),
            ("Authentication", self._check_auth),
            ("Query Execution", self._check_query),
            ("Replication Slots", self._check_replication_slots),
            ("Max Connections", self._check_max_connections),
            ("Autovacuum", self._check_autovacuum),
        ]
        results = []
        for name, fn in checks:
            try:
                detail = fn()
                results.append({"name": name, "passed": True, "detail": detail})
            except Exception as e:
                results.append({"name": name, "passed": False, "detail": str(e)})
        return results

    def _check_tcp(self) -> str:
        start = time.monotonic()
        with socket.create_connection((self.host, self.port), timeout=5):
            pass
        elapsed = (time.monotonic() - start) * 1000
        return f"Connected in {elapsed:.1f}ms"

    def _check_auth(self) -> str:
        conn = psycopg2.connect(
            host=self.host, port=self.port, dbname=self.db_name,
            user=self.username, password=self.password, connect_timeout=5,
        )
        conn.close()
        return "Authentication successful"

    def _check_query(self) -> str:
        conn = psycopg2.connect(
            host=self.host, port=self.port, dbname=self.db_name,
            user=self.username, password=self.password, connect_timeout=5,
        )
        with conn.cursor() as cur:
            start = time.monotonic()
            cur.execute("SELECT 1;")
            elapsed = (time.monotonic() - start) * 1000
        conn.close()
        return f"SELECT 1 in {elapsed:.2f}ms"

    def _check_replication_slots(self) -> str:
        conn = psycopg2.connect(
            host=self.host, port=self.port, dbname=self.db_name,
            user=self.username, password=self.password, connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM pg_replication_slots WHERE active = false;")
            inactive = cur.fetchone()[0]
        conn.close()
        if inactive > 0:
            raise RuntimeError(f"{inactive} inactive replication slot(s) — may cause WAL bloat")
        return "No inactive replication slots"

    def _check_max_connections(self) -> str:
        conn = psycopg2.connect(
            host=self.host, port=self.port, dbname=self.db_name,
            user=self.username, password=self.password, connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_setting('max_connections')::int AS max,
                       count(*) AS used
                FROM pg_stat_activity;
            """)
            row = cur.fetchone()
        conn.close()
        max_conn, used = row
        pct = used / max_conn * 100
        if pct > 80:
            raise RuntimeError(f"Connection usage at {pct:.0f}% ({used}/{max_conn})")
        return f"Connections: {used}/{max_conn} ({pct:.0f}%)"

    def _check_autovacuum(self) -> str:
        conn = psycopg2.connect(
            host=self.host, port=self.port, dbname=self.db_name,
            user=self.username, password=self.password, connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT current_setting('autovacuum');")
            av = cur.fetchone()[0]
        conn.close()
        if av != "on":
            raise RuntimeError(f"Autovacuum is disabled (setting={av})")
        return "Autovacuum enabled"
