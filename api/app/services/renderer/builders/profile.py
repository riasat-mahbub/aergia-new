"""AST builder for the ``profile`` section.

Emits a single ``Entry`` whose fields mirror the existing
``ProfileData`` shape: ``name``, ``title``, ``email``, ``phone``,
``location``, ``site_text``, ``site_url``, ``summary``, and one
``social_links.<i>`` field per social entry.

The builder only constructs the AST. No styling, no defaults — the resolver
cascades three-axis style and the renderer emits HTML.
"""

from __future__ import annotations

from app.schema.models import Entry, FieldBlock, Section, SectionInstance, TextRun


def build_profile(instance: SectionInstance) -> Section:
    data = instance.data if isinstance(instance.data, dict) else {}

    fields: list[FieldBlock] = []
    fields.append(FieldBlock(key="name", group="main", runs=[TextRun(text=str(data.get("name", "") or ""))]))
    if data.get("title"):
        fields.append(FieldBlock(key="title", group="subtitle", runs=[TextRun(text=str(data["title"]))]))
    if data.get("email"):
        fields.append(FieldBlock(key="email", group="contact", runs=[TextRun(text=str(data["email"]))]))
    if data.get("phone"):
        fields.append(FieldBlock(key="phone", group="contact", runs=[TextRun(text=str(data["phone"]))]))
    if data.get("location"):
        fields.append(FieldBlock(key="location", group="contact", runs=[TextRun(text=str(data["location"]))]))

    site_url = str(data.get("site_url") or "").strip()
    site_text = str(data.get("site_text") or "").strip()
    if site_url:
        fields.append(
            FieldBlock(
                key="site",
                group="contact",
                runs=[TextRun(text=site_text or site_url)],
            )
        )
    elif site_text:
        # Free-floating site text without a URL is just a text label.
        fields.append(FieldBlock(key="site_text", group="contact", runs=[TextRun(text=site_text)]))

    social_links = data.get("social_links") or []
    for i, link in enumerate(social_links):
        if not isinstance(link, dict):
            continue
        url = str(link.get("url") or "")
        if not url:
            continue
        label = str(link.get("label") or url)
        icon = str(link.get("icon") or "") or None
        fields.append(
            FieldBlock(
                key=f"social_links.{i}",
                group="social",
                icon=icon,
                runs=[TextRun(text=label)],
            )
        )

    if data.get("summary"):
        fields.append(FieldBlock(key="summary", group="summary", runs=[TextRun(text=str(data["summary"]))]))

    entry = Entry(id=f"{instance.id}__main", fields=fields)
    return Section(
        id=instance.id,
        type="profile",
        title=instance.title or "Profile",
        enabled=instance.enabled,
        entries=[entry],
    )
