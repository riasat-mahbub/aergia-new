"""Tests for the explicit, dry-run-first application cleanup utility."""

import json
import sqlite3

from scripts.cleanup_application_artifacts import cleanup_database


def _database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE applications (id TEXT PRIMARY KEY, cv_id TEXT);
            CREATE TABLE application_status_history (id TEXT PRIMARY KEY, application_id TEXT);
            CREATE TABLE cvs (id TEXT PRIMARY KEY, metadata TEXT);
            """,
        )
        connection.execute("INSERT INTO applications VALUES ('app-linked', 'cv-linked')")
        connection.execute("INSERT INTO application_status_history VALUES ('history', 'app-linked')")
        connection.executemany(
            "INSERT INTO cvs VALUES (?, ?)",
            [
                ("cv-linked", json.dumps({"application_id": "app-linked"})),
                ("cv-orphan", json.dumps({"application_id": "old-app"})),
                ("cv-ordinary", json.dumps({"title": "Personal CV"})),
            ],
        )


def test_cleanup_dry_run_does_not_change_rows(tmp_path):
    database = tmp_path / "test.db"
    _database(database)

    report = cleanup_database(database)

    assert report.status == "dry-run"
    assert report.applications_before == 1
    assert report.generated_cv_candidates == 1
    assert report.unrelated_cvs_preserved == 2
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM cvs").fetchone()[0] == 3


def test_cleanup_removes_applications_and_generated_cvs_preserves_unlinked(tmp_path):
    database = tmp_path / "test.db"
    backup_dir = tmp_path / "backups"
    _database(database)

    report = cleanup_database(database, apply=True, backup_dir=backup_dir)

    assert report.status == "applied"
    assert report.generated_cvs_removed == 1
    assert report.unrelated_cvs_preserved == 2
    assert report.backup is not None
    assert (backup_dir / report.backup.split("/")[-1]).exists()
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM application_status_history").fetchone()[0] == 0
        assert connection.execute("SELECT id FROM cvs ORDER BY id").fetchall() == [
            ("cv-ordinary",),
            ("cv-orphan",),
        ]


def test_cleanup_skips_database_without_application_schema(tmp_path):
    database = tmp_path / "empty.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE cvs (id TEXT PRIMARY KEY, metadata TEXT)")

    report = cleanup_database(database)

    assert report.status == "skipped-no-applications-table"
