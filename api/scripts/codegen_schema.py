"""Pydantic → TypeScript codegen for the new schema package.

Reads ``api/app/schema/models.py`` via importlib and emits a single
``web/src/generated/schema.ts`` with sorted, deterministic TypeScript
``interface`` declarations.

Why a custom generator instead of ``datamodel-code-generator`` or
``pydantic-to-typescript``? The plan notes both packages have dependency
issues. A small in-tree generator is ~80 lines, has no new deps, and
emits the exact output the frontend wants.

Output conventions:

- Double quotes, trailing semicolons.
- Members sorted alphabetically within each interface (stable diffs).
- ``Literal[...]`` → ``type Foo = "a" | "b"`` discriminated unions.
- A header comment carries the SHA-256 of the source file so CI can
  detect drift.
- TS 5.6 target. No ``satisfies``, no ``as const`` literal unions.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_MODULE = "app.schema.models"
SOURCE_PATH = REPO_ROOT / "api" / "app" / "schema" / "models.py"
OUTPUT_PATH = REPO_ROOT / "web" / "src" / "generated" / "schema.ts"


# Top-level models to emit (excludes HTTP wrappers like TemplateListItem
# — the frontend doesn't import them, and including them risks drift).
EMITTED_MODELS: tuple[str, ...] = (
    "TextStyle",
    "SubsectionStyle",
    "LayoutHints",
    "SectionPolicy",
    "DateStyle",
    "TextRun",
    "FieldBlock",
    "Entry",
    "Section",
    "Document",
    "SectionInstanceStyle",
    "SectionInstance",
    "LayoutDefaults",
    "PolicyOverrides",
    "GlobalStyles",
    "ZoneStyle",
    "Zone",
    "TemplateManifest",
    "ResolvedZone",
    "RenderModel",
    "Customizations",
)


def _load_models() -> dict[str, type[BaseModel]]:
    """Import the schema module and return the named classes."""

    sys.path.insert(0, str(REPO_ROOT / "api"))
    module = importlib.import_module(SOURCE_MODULE)
    return {name: getattr(module, name) for name in EMITTED_MODELS}


def _ref_name(schema: dict[str, Any]) -> str:
    """Return the bare class name for a JSON-Schema ``$ref``."""

    return schema["$ref"].rsplit("/", 1)[-1]


def _ts_type(schema: dict[str, Any], refs: dict[str, str]) -> str:
    """Translate a JSON-Schema fragment into a TS type expression."""

    if "$ref" in schema:
        return refs.get(_ref_name(schema), _ref_name(schema))

    if "anyOf" in schema or "oneOf" in schema:
        variants = schema.get("anyOf") or schema.get("oneOf")
        # Pydantic emits `anyOf` for Optional[Model]. Collapse to T | null.
        if len(variants) == 2 and "type" in variants[1] and variants[1]["type"] == "null":
            return f"({_ts_type(variants[0], refs)}) | null"
        return " | ".join(_ts_type(v, refs) for v in variants)

    if "allOf" in schema:
        # Pydantic emits allOf for $ref-only unions.
        return " & ".join(_ts_type(v, refs) for v in schema["allOf"])

    if "enum" in schema:
        members = " | ".join(f'"{v}"' for v in schema["enum"])
        return f"({members})"

    typ = schema.get("type")
    if typ == "string":
        return "string"
    if typ == "integer":
        return "number"
    if typ == "number":
        return "number"
    if typ == "boolean":
        return "boolean"
    if typ == "null":
        return "null"
    if typ == "array":
        return f"Array<{_ts_type(schema['items'], refs)}>"

    if typ == "object" or "properties" in schema or "additionalProperties" in schema:
        # additionalProperties: { $ref: ... } → dict keyed by string.
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {_ts_type(additional, refs)}>"
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        if not props:
            return "Record<string, unknown>"
        parts = []
        for name in sorted(props):
            t = _ts_type(props[name], refs)
            optional = "" if name in required else "?"
            parts.append(f'"{name}"{optional}: {t}')
        return "{ " + "; ".join(parts) + " }"

    return "unknown"


def _interface_for(name: str, model: type[BaseModel], refs: dict[str, str]) -> str:
    """Emit a single ``export interface NAME { ... }`` block."""
    schema = model.model_json_schema(by_alias=True)

    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    lines = [f"export interface {name} {{"]
    for prop_name in sorted(props):
        prop_schema = props[prop_name]
        t = _ts_type(prop_schema, refs)
        optional = "" if prop_name in required else "?"
        lines.append(f'  "{prop_name}"{optional}: {t};')
    lines.append("}")
    return "\n".join(lines)


def _ref_map() -> dict[str, str]:
    """Build a mapping from JSON-Schema $ref name to our TS interface name."""

    return {name: name for name in EMITTED_MODELS}


def generate() -> str:
    """Return the generated TS source as a string."""

    models = _load_models()
    refs = _ref_map()

    src_bytes = SOURCE_PATH.read_bytes()
    digest = hashlib.sha256(src_bytes).hexdigest()[:16]

    blocks = [
        "// This file is generated. Do not edit by hand.",
        f"// Source: api/app/schema/models.py (sha256:{digest})",
        "",
    ]
    for name in EMITTED_MODELS:
        blocks.append(_interface_for(name, models[name], refs))
        blocks.append("")
    return "\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate web/src/generated/schema.ts from Pydantic models.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if the file would change.")
    parser.add_argument("--out", type=Path, default=OUTPUT_PATH, help="Output path.")
    args = parser.parse_args()

    output = generate()
    if args.check:
        existing = args.out.read_text() if args.out.exists() else ""
        if existing != output:
            sys.stderr.write(
                f"Drift: {args.out} would change. Run `npm run codegen` to update.\n"
            )
            return 1
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
