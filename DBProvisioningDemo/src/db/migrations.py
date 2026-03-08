"""Simple schema migration runner."""
import hashlib
import logging
from pathlib import Path

from .manager import DatabaseManager

log = logging.getLogger(__name__)

MIGRATIONS_TABLE = "schema_migrations"

INIT_SQL = f"""
CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
    id          SERIAL PRIMARY KEY,
    version     VARCHAR(255) UNIQUE NOT NULL,
    checksum    VARCHAR(64)  NOT NULL,
    applied_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""


class MigrationRunner:
    """Applies SQL migration files in order."""

    def __init__(self, manager: DatabaseManager, migrations_dir: str = "migrations"):
        self.db = manager
        self.dir = Path(migrations_dir)

    def migrate(self) -> int:
        """Apply all pending migrations. Returns count of applied migrations."""
        self.db.execute(INIT_SQL)
        applied = self._applied_versions()
        files = sorted(self.dir.glob("*.sql"))
        count = 0
        for f in files:
            if f.stem in applied:
                log.debug(f"Already applied: {f.stem}")
                continue
            sql = f.read_text()
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            log.info(f"Applying migration: {f.stem}")
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        f"INSERT INTO {MIGRATIONS_TABLE} (version, checksum) VALUES (%s, %s);",
                        (f.stem, checksum),
                    )
            count += 1
            log.info(f"Applied: {f.stem}")
        return count

    def _applied_versions(self) -> set[str]:
        rows = self.db.execute(f"SELECT version FROM {MIGRATIONS_TABLE};")
        return {r["version"] for r in rows}

    def status(self) -> list[dict]:
        """Return migration status for all files."""
        applied = self._applied_versions()
        files = sorted(self.dir.glob("*.sql"))
        return [
            {"version": f.stem, "applied": f.stem in applied}
            for f in files
        ]
