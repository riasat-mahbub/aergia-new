"""Safely remove disposable application records and their generated CVs.

The command is intentionally explicit and dry-run by default. It removes
application status history, applications, and CVs identified by the
application foreign-key relation. CV metadata is user-editable and is not used
as provenance, so unlinked CVs are preserved even if they contain an old or
forged application_id value.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class CleanupReport:
    database: str
    status: str
    applications_before: int = 0
    applications_removed: int = 0
    history_before: int = 0
    history_removed: int = 0
    generated_cv_candidates: int = 0
    generated_cvs_removed: int = 0
    unrelated_cvs_preserved: int = 0
    backup: str | None = None


def _has_table(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _has_column(connection: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in connection.execute(f"PRAGMA table_info({table})"))


def _count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _candidate_cv_ids(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT cv_id
        FROM applications
        WHERE cv_id IS NOT NULL
        ORDER BY cv_id
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def cleanup_database(
    database: str | Path,
    *,
    apply: bool = False,
    backup_dir: str | Path | None = None,
) -> CleanupReport:
    """Report or remove application artifacts from one SQLite database."""

    path = Path(database).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Database does not exist: {path}")

    with sqlite3.connect(path) as connection:
        if not _has_table(connection, "applications"):
            return CleanupReport(database=str(path), status="skipped-no-applications-table")
        if not _has_table(connection, "cvs"):
            raise RuntimeError(f"Database has applications but no cvs table: {path}")

        applications_before = _count(connection, "applications")
        history_before = _count(connection, "application_status_history") if _has_table(
            connection, "application_status_history"
        ) else 0
        all_cvs_before = _count(connection, "cvs")
        candidate_ids = _candidate_cv_ids(connection)
        unrelated_cvs_preserved = all_cvs_before - len(candidate_ids)

        if not apply:
            return CleanupReport(
                database=str(path),
                status="dry-run",
                applications_before=applications_before,
                history_before=history_before,
                generated_cv_candidates=len(candidate_ids),
                unrelated_cvs_preserved=unrelated_cvs_preserved,
            )

        backup_path: Path | None = None
        if backup_dir is None:
            backup_path = Path(tempfile.mkdtemp(prefix="aergia-db-backup-")) / path.name
        else:
            backup_root = Path(backup_dir).expanduser().resolve()
            backup_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = backup_root / f"{path.name}.{stamp}.bak"
        shutil.copy2(path, backup_path)

        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        try:
            if _has_table(connection, "application_status_history"):
                connection.execute("DELETE FROM application_status_history")
            connection.execute("DELETE FROM applications")
            if candidate_ids:
                placeholders = ", ".join("?" for _ in candidate_ids)
                connection.execute(
                    f"DELETE FROM cvs WHERE id IN ({placeholders})",
                    candidate_ids,
                )
            if (
                _has_table(connection, "users")
                and _has_column(connection, "users", "application_count")
                and _has_column(connection, "users", "cv_count")
            ):
                connection.execute(
                    "UPDATE users SET application_count = "
                    "(SELECT COUNT(*) FROM applications WHERE applications.user_id = users.id), "
                    "cv_count = "
                    "(SELECT COUNT(*) FROM cvs WHERE cvs.user_id = users.id AND cvs.is_active = 1)"
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        history_after = _count(connection, "application_status_history") if _has_table(
            connection, "application_status_history"
        ) else 0
        generated_cvs_removed = len(candidate_ids)
        if _count(connection, "applications") != 0 or history_after != 0:
            raise RuntimeError(f"Cleanup verification failed for {path}")
        if _count(connection, "cvs") != unrelated_cvs_preserved:
            raise RuntimeError(f"CV preservation verification failed for {path}")

        return CleanupReport(
            database=str(path),
            status="applied",
            applications_before=applications_before,
            applications_removed=applications_before,
            history_before=history_before,
            history_removed=history_before,
            generated_cv_candidates=len(candidate_ids),
            generated_cvs_removed=generated_cvs_removed,
            unrelated_cvs_preserved=unrelated_cvs_preserved,
            backup=str(backup_path),
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        dest="databases",
        action="append",
        required=True,
        help="Explicit SQLite database path; repeat for each database.",
    )
    parser.add_argument(
        "--backup-dir",
        help="Directory for backups when --apply is used; otherwise a temporary directory is created.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the cleanup. Without this flag the command only reports candidates.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    for database in args.databases:
        report = cleanup_database(database, apply=args.apply, backup_dir=args.backup_dir)
        print(
            f"{report.database}: {report.status}; applications={report.applications_before}"
            f"/{report.applications_removed}; generated_cvs={report.generated_cv_candidates}"
            f"/{report.generated_cvs_removed}; unrelated_cvs_preserved={report.unrelated_cvs_preserved}"
            + (f"; backup={report.backup}" if report.backup else "")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
