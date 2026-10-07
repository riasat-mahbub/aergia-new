"""Render only the fictional semantic fixtures through Aergia's canonical pipeline.

Run from the repository root with PYTHONPATH=api api/.venv/bin/python
docs/fixtures/tailoring-v10-semantic/render.py <candidate-raw.json path>.
Rendering writes candidate.json, candidate.pdf, render.json and page thumbnails.
The original input must be named candidate-raw.json or candidate-final-raw.json.
"""

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import pypdfium2

from app.db.seed import SEED_TEMPLATES
from app.document_schema.models import TemplateManifest
from app.http_schemas.profile import UserProfile
from app.http_schemas.tailoring import TailoringCandidateCV
from app.services.pdf import pdf_page_count
from app.services.renderer import prepare_render_source, render_source_pdf
from app.services.renderer._pdf_runtime import close_browser
from app.services.tailoring import TailoringService

ROOT = Path(__file__).resolve().parent


async def main():
    try:
        for arg in sys.argv[1:]:
            path = Path(arg).resolve()
            if (
                not path.is_relative_to(ROOT)
                or path.name not in {"candidate-raw.json", "candidate-final-raw.json"}
                or path.parent.name not in {"baseline", "revised"}
                or path.parent.parent.name not in {"software", "analysis", "collaboration"}
            ):
                raise ValueError("Only the named synthetic author fixtures may be rendered")
            raw = json.loads(path.read_text())
            template = next(item for item in SEED_TEMPLATES if item["id"] == "generic-minimal")
            candidate, _ = TailoringService._normalize_candidate(
                TailoringCandidateCV.model_validate(raw),
                {
                    "manifest_by_id": {template["id"]: template["manifest"]},
                    "profile": UserProfile(
                        name="Avery Chen", email="avery.chen@example.test",
                        location="Halifax, Canada", social_links=[],
                    ),
                },
            )
            stem = "candidate-final" if path.name.startswith("candidate-final") else "candidate"
            source = prepare_render_source(
                candidate["sections"], TemplateManifest.model_validate(template["manifest"]),
                candidate.get("customizations", {}),
            )
            pdf = await render_source_pdf(source)
            (path.parent / f"{stem}.json").write_text(json.dumps(candidate, indent=2) + "\n")
            (path.parent / f"{stem}.pdf").write_bytes(pdf)
            metadata = {
                "candidate_hash": TailoringService._candidate_hash(candidate),
                "pdf_sha256": hashlib.sha256(pdf).hexdigest(),
                "page_count": pdf_page_count(pdf),
            }
            (path.parent / f"{stem}-render.json").write_text(json.dumps(metadata, indent=2) + "\n")
            document = pypdfium2.PdfDocument(pdf)
            try:
                for index in range(len(document)):
                    page = document[index]
                    bitmap = page.render(scale=1.3)
                    bitmap.to_pil().save(path.parent / f"{stem}.page-{index + 1}.png")
                    bitmap.close()
                    page.close()
            finally:
                document.close()
            print(path.relative_to(ROOT), metadata["page_count"], "page(s)")
    finally:
        await close_browser()


if __name__ == "__main__":
    asyncio.run(main())
