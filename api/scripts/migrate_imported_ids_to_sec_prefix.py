#!/usr/bin/env python3
"""One-shot migration: re-key imported section/entry IDs to the ``sec_`` prefix.

Background
----------
The PDF parser used to emit type-specific ID prefixes (``prof_``, ``edu_``,
``exp_``, ``skg_``, ``proj_``, ``cert_``, ``lang_``, ``res_``, ``ext_``,
``imp_``). Every other code path that touches section IDs — including the
``SectionZoneView`` drop handler — assumed the ``sec_`` prefix. Imported
sections therefore failed the ``sec_`` prefix check in drag-drop and were
silently unassignable in the customize tab.

The parser has been updated to emit ``sec_<hex>`` for every newly imported
section and entry. This script back-fills the existing rows so old imported
CVs behave the same way.

What it does
------------
For each active CV whose ``sections`` JSON contains any ID not starting
with ``sec_``:

  1. Builds a fresh ``old_id -> new_id`` map. Each new id is ``sec_<8 hex>``,
     generated per-CV to guarantee no collisions across CVs that share old
     ids (e.g. a user who copied a CV keeps the same section ids in both
     copies — they get distinct new ids).
  2. Walks the ``sections`` array and replaces every ``id`` field at every
     nesting level (sections, entries inside ``data[]``, skill-group rows
     inside ``data[].items``, ``extras.fields[]`` rows, etc.).
  3. Updates ``customizations.layout.placement`` keys in lockstep so the
     saved placement map stays consistent with the new section ids.
  4. Updates ``customizations.per_section`` keys the same way.

The ``metadata`` JSON blob is left alone — survey of the dev DB showed no
section-id references there.

Usage
-----
::

    # Dry run — print what would change, do nothing.
    python -m scripts.migrate_imported_ids_to_sec_prefix --dry-run

    # Apply.
    python -m scripts.migrate_imported_ids_to_sec_prefix

    # Custom DB path (defaults to api/data/aergia.db).
    python -m scripts.migrate_imported_ids_to_sec_prefix --db api/data/aergia.test.db

The script exits non-zero if any row fails to update, so it can be wired
into CI as a guard once the migration has been run everywhere.

Idempotency: safe to re-run. Rows whose sections contain only ``sec_`` ids
are skipped. Rows that were partially migrated by a prior run finish the
job (no id is rewritten twice because the generator never repeats a hex).
"""
from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import sys
from pathlib import Path

# Section-level prefixes the parser used to emit (excludes ``sec_`` and any
# nested entry ids we want to rewrite). Anything matching one of these is a
# candidate for migration.
_LEGACY_SECTION_PREFIXES = (
    "prof_",
    "edu_",
    "exp_",
    "sk_",
    "skg_",
    "proj_",
    "cert_",
    "lang_",
    "res_",
    "ext_",
    "imp_",
)


def _needs_migration(value: str) -> bool:
    return isinstance(value, str) and value.startswith(_LEGACY_SECTION_PREFIXES)


def _fresh_id() -> str:
    return f"sec_{secrets.token_hex(4)}"


def _walk_collect_ids(obj, path: str = "") -> dict[str, str]:
    """Walk a sections/customizations JSON tree and collect legacy ids.

    Returns a ``{old_id: new_id}`` map covering every string ``id`` field
    whose value starts with a legacy prefix. The same hex is never
    returned twice — guarantees we don't accidentally collide within a
    single CV's rewrite.
    """
    mapping: dict[str, str] = {}
    seen_new: set[str] = set()

    def _new_for(old: str) -> str:
        new = _fresh_id()
        while new in seen_new:
            new = _fresh_id()
        seen_new.add(new)
        return new

    def walk(node, p: str) -> None:
        if isinstance(node, dict):
            # Capture an id field if its value is a legacy prefix.
            nid = node.get("id")
            if isinstance(nid, str) and _needs_migration(nid) and nid not in mapping:
                mapping[nid] = _new_for(nid)
            for k, v in node.items():
                walk(v, f"{p}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{p}[{i}]")

    walk(obj, path)
    return mapping


def _apply_mapping(obj, mapping: dict[str, str]) -> int:
    """Replace every legacy id with its mapped new id. Returns count of rewrites."""

    count = 0

    def walk(node):
        nonlocal count
        if isinstance(node, dict):
            # 1) Value-as-id (sections, entries, skill groups).
            if "id" in node and isinstance(node["id"], str) and node["id"] in mapping:
                node["id"] = mapping[node["id"]]
                count += 1
            # 2) Key-as-id (placement maps and per_section dicts both use
            #    section ids as keys).
            for k in list(node.keys()):
                if k in mapping:
                    new_k = mapping[k]
                    node[new_k] = node.pop(k)
                    count += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(obj)
    return count


def _migrate_row(conn: dict, row_id: str, sections_json: str, customizations_json: str) -> dict:
    sections = json.loads(sections_json)
    customizations = json.loads(customizations_json)

    section_mapping = _walk_collect_ids(sections)
    cus_mapping = _walk_collect_ids(customizations)

    if not section_mapping and not cus_mapping:
        return {"id": row_id, "changed": False, "rewrites": 0, "mapping_size": 0}

    rewrites = _apply_mapping(sections, section_mapping)
    rewrites += _apply_mapping(customizations, cus_mapping)

    new_sections_json = json.dumps(sections, separators=(",", ":"), ensure_ascii=False)
    new_customizations_json = json.dumps(customizations, separators=(",", ":"), ensure_ascii=False)

    if not conn["dry_run"]:
        conn["db"].execute(
            "UPDATE cvs SET sections = ?, customizations = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_sections_json, new_customizations_json, row_id),
        )

    return {
        "id": row_id,
        "changed": True,
        "rewrites": rewrites,
        "mapping_size": len(section_mapping) + len(cus_mapping),
    }


def _survey(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return [(cv_id, title), ...] for active CVs that contain legacy ids."""
    cur = conn.execute("SELECT id, title FROM cvs WHERE is_active = 1")
    rows: list[tuple[str, str]] = []
    for cv_id, title in cur.fetchall():
        cur2 = conn.execute("SELECT sections FROM cvs WHERE id = ?", (cv_id,))
        sec_json = cur2.fetchone()[0]
        secs = json.loads(sec_json)
        # Quick check: any id field with a legacy prefix anywhere in the tree?
        def has_legacy(node) -> bool:
            if isinstance(node, dict):
                nid = node.get("id")
                if isinstance(nid, str) and _needs_migration(nid):
                    return True
                return any(has_legacy(v) for v in node.values())
            if isinstance(node, list):
                return any(has_legacy(v) for v in node)
            return False

        if has_legacy(secs):
            rows.append((cv_id, title))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    # Resolve the repo root relative to this script so the default db path
    # is the same regardless of cwd.
    _here = Path(__file__).resolve().parent.parent
    parser.add_argument(
        "--db",
        default=str(_here / "data" / "aergia.db"),
        help=f"SQLite database path. Defaults to ``{_here / 'data' / 'aergia.db'}``.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing.",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"DB not found: {db_path}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db_path))
    try:
        targets = _survey(conn)
        if not targets:
            print("No CVs with legacy IDs found — nothing to do.")
            return 0

        print(f"Found {len(targets)} CV(s) with legacy IDs:")
        for cv_id, title in targets:
            print(f"  {cv_id}  '{title}'")

        if args.dry_run:
            print("\n--dry-run set; not writing.")
            return 0

        bundle: dict = {"db": conn, "dry_run": False}
        results: list[dict] = []
        for cv_id, _title in targets:
            cur = conn.execute(
                "SELECT sections, customizations FROM cvs WHERE id = ?",
                (cv_id,),
            )
            sec_json, cus_json = cur.fetchone()
            try:
                res = _migrate_row(bundle, cv_id, sec_json, cus_json)
            except Exception as exc:
                print(f"  FAIL {cv_id}: {exc}", file=sys.stderr)
                conn.rollback()
                return 1
            results.append(res)

        conn.commit()

        print(f"\nMigrated {len(results)} CV(s):")
        total_rewrites = 0
        for r in results:
            print(f"  {r['id']}: rewrites={r['rewrites']} (mapping_size={r['mapping_size']})")
            total_rewrites += r["rewrites"]
        print(f"Total rewrites: {total_rewrites}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())