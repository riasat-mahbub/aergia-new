"""Library backend tests — service + routes.

Covers the 12 cases enumerated in Phase F of the implementation plan:
service-level helpers + race safety, route-level CRUD + isolation,
cross-feature invariants (Library doesn't affect renderer).
"""

from __future__ import annotations

import pytest
import sqlalchemy
from uuid import uuid4

from app.db.session import async_session
from app.models.library import Library, LibraryEntry
from app.schemas.library import library_kind_for_section_type, section_type_for_library_kind
from app.services.library import LibraryService, _content_hash, _derive_title


def test_library_kind_mapping_round_trips_renderer_section_types():
    expected = {
        "experience": "experience",
        "education": "education",
        "skills": "skill",
        "projects": "project",
        "languages": "language",
        "certifications": "certification",
        "research": "research",
    }
    assert {
        section: library_kind_for_section_type(section)
        for section in expected
    } == expected
    assert {
        kind: section_type_for_library_kind(kind)
        for kind in expected.values()
    } == {kind: section for section, kind in expected.items()}


def test_add_entry_route_is_registered_as_post():
    from app.app import app

    path = "/api/v1/cvs/{cv_id}/sections/{section_id}/entries/{entry_id}/add-to-library"
    assert "post" in app.openapi()["paths"][path]


@pytest.fixture
async def auth_headers(client):
    email = f"library-test-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def other_auth_headers(client):
    email = f"library-other-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def clean_library():
    """Clear library + library_entries rows so each test starts fresh.

    The test DB is shared across runs (see conftest note). Without this
    fixture, repeated test runs accumulate Library entries and break
    tests that assert exact counts (e.g. promote_is_idempotent_via_content_hash).
    """
    async with async_session() as db:
        await db.execute(sqlalchemy.delete(LibraryEntry))
        await db.execute(sqlalchemy.delete(Library))
        await db.commit()

@pytest.fixture
async def user_id(client):
    """Return the Library-test user's id, registering the user on demand.

    Some tests use this fixture without ``auth_headers`` (the
    service-level tests). Creating the user via the API here keeps the
    fixture self-sufficient.
    """
    email = f"library-test-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    async with async_session() as db:
        from app.models.user import User
        result = await db.execute(sqlalchemy.select(User.id).where(User.email == email))
        uid = result.scalar_one()
        return uid


def test_content_hash_is_order_independent():
    a = _content_hash([{"x": 1, "y": 2}])
    b = _content_hash([{"y": 2, "x": 1}])
    assert a == b


def test_content_hash_distinguishes_values():
    a = _content_hash([{"x": 1}])
    b = _content_hash([{"x": 2}])
    assert a != b


def test_derive_title_prefers_payload_title():
    assert _derive_title([{"title": "Acme Corp"}], "experience") == "Acme Corp"


def test_derive_title_falls_back_to_kind():
    assert _derive_title([], "skill") == "Skill"
    assert _derive_title([{"unrelated": "x"}], "education") == "Education"

def test_derive_title_uses_normal_section_fields():
    assert _derive_title([{"company": "Acme", "position": "Lead Engineer"}], "experience") == "Lead Engineer"
    assert _derive_title([{"institution": "State U", "degree": "BS"}], "education") == "BS"


# ─── Service-level behaviour ────────────────────────────────────────


@pytest.mark.asyncio
async def test_library_auto_created_on_first_write(user_id, clean_library):
    async with async_session() as db:
        svc = LibraryService(db)
        lib_a = await svc._get_or_create_library(user_id)
        lib_b = await svc._get_or_create_library(user_id)
        assert lib_a.id == lib_b.id
        await db.rollback()


@pytest.mark.asyncio
async def test_get_or_create_library_concurrent_safe(user_id, clean_library):
    """Two concurrent calls cannot both insert; the loser re-SELECTs.

    SQLite serialises writes, so the simpler test is sufficient: two
    back-to-back ``_get_or_create_library`` calls return the same row.
    """
    async with async_session() as db:
        svc = LibraryService(db)
        lib_a = await svc._get_or_create_library(user_id)
        lib_b = await svc._get_or_create_library(user_id)
    assert lib_a.id == lib_b.id


@pytest.mark.asyncio
async def test_create_list_update_delete_entry(client, auth_headers, clean_library):
    create = await client.post(
        "/api/v1/library",
        json={"kind": "experience", "payload": [{"company": "Acme"}]},
        headers=auth_headers,
    )
    assert create.status_code == 201
    entry = create.json()
    assert entry["kind"] == "experience"
    assert entry["payload"] == [{"company": "Acme"}]
    entry_id = entry["id"]

    lst = await client.get("/api/v1/library", headers=auth_headers)
    assert lst.status_code == 200
    ids = [e["id"] for e in lst.json()]
    assert entry_id in ids

    upd = await client.patch(
        f"/api/v1/library/{entry_id}",
        json={"payload": [{"company": "Initech"}]},
        headers=auth_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["payload"] == [{"company": "Initech"}]

    delete = await client.delete(f"/api/v1/library/{entry_id}", headers=auth_headers)
    assert delete.status_code == 204

    after = await client.get(f"/api/v1/library/{entry_id}", headers=auth_headers)
    assert after.status_code == 404

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "section_type"),
    [
        ("experience", "experience"),
        ("education", "education"),
        ("skill", "skills"),
        ("project", "projects"),
        ("language", "languages"),
        ("certification", "certifications"),
        ("research", "research"),
    ],
)
async def test_clone_maps_library_kind_to_renderer_section_type(
    client, auth_headers, clean_library, kind, section_type
):
    create = await client.post(
        "/api/v1/library",
        json={"kind": kind, "payload": [{"name": "Reusable item"}]},
        headers=auth_headers,
    )
    entry_id = create.json()["id"]

    clone = await client.post(f"/api/v1/library/{entry_id}/clone", headers=auth_headers)

    assert clone.status_code == 200
    assert clone.json()["section_instance"]["type"] == section_type


@pytest.mark.asyncio
async def test_clone_returns_section_instance_with_fresh_id(client, auth_headers, clean_library):
    create = await client.post(
        "/api/v1/library",
        json={"kind": "experience", "payload": [{"title": "Senior"}]},
        headers=auth_headers,
    )
    entry_id = create.json()["id"]

    clone_a = (await client.post(f"/api/v1/library/{entry_id}/clone", headers=auth_headers)).json()
    clone_b = (await client.post(f"/api/v1/library/{entry_id}/clone", headers=auth_headers)).json()

    a_id = clone_a["section_instance"]["id"]
    b_id = clone_b["section_instance"]["id"]
    assert a_id != b_id
    assert clone_a["section_instance"]["type"] == "experience"
    assert clone_a["section_instance"]["title"] == "Senior"


@pytest.mark.asyncio
async def test_clone_is_isolated_from_library_edits(client, auth_headers, clean_library):
    create = await client.post(
        "/api/v1/library",
        json={"kind": "skill", "payload": [{"name": "Python"}]},
        headers=auth_headers,
    )
    entry_id = create.json()["id"]

    clone_resp = (await client.post(f"/api/v1/library/{entry_id}/clone", headers=auth_headers)).json()
    cloned = clone_resp["section_instance"]

    await client.patch(
        f"/api/v1/library/{entry_id}",
        json={"payload": [{"name": "Rust"}]},
        headers=auth_headers,
    )
    assert cloned["data"] == [{"name": "Python"}]


@pytest.mark.asyncio
async def test_clone_payload_is_deepcopy(client, auth_headers, clean_library):
    create = await client.post(
        "/api/v1/library",
        json={"kind": "experience", "payload": [{"company": "Acme"}]},
        headers=auth_headers,
    )
    entry_id = create.json()["id"]
    clone_resp = (await client.post(f"/api/v1/library/{entry_id}/clone", headers=auth_headers)).json()
    cloned = clone_resp["section_instance"]
    assert cloned["data"] == [{"company": "Acme"}]
    cloned["data"].append({"company": "Mutated"})
    reread = (await client.get(f"/api/v1/library/{entry_id}", headers=auth_headers)).json()
    assert reread["payload"] == [{"company": "Acme"}]


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_library(
    client, auth_headers, other_auth_headers, clean_library
):
    create = await client.post(
        "/api/v1/library",
        json={"kind": "skill", "payload": [{"name": "X"}]},
        headers=auth_headers,
    )
    entry_id = create.json()["id"]

    other_get = await client.get(f"/api/v1/library/{entry_id}", headers=other_auth_headers)
    assert other_get.status_code == 404

    other_patch = await client.patch(
        f"/api/v1/library/{entry_id}",
        json={"payload": [{"name": "Y"}]},
        headers=other_auth_headers,
    )
    assert other_patch.status_code == 404

    other_delete = await client.delete(f"/api/v1/library/{entry_id}", headers=other_auth_headers)
    assert other_delete.status_code == 404


@pytest.mark.asyncio
async def test_unknown_kind_rejected(client, auth_headers, clean_library):
    resp = await client.post(
        "/api/v1/library",
        json={"kind": "bogus", "payload": []},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_does_not_affect_cv_copies(client, auth_headers, clean_library):
    """A Library entry's deletion does NOT roll back a CV's structural copy."""
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Carryover CV",
            "sections": [
                {
                    "id": "sec_exp",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [{"title": "Original Role", "company": "Acme"}],
                }
            ],
        },
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]

    promote = await client.post(
        f"/api/v1/cvs/{cv_id}/promote-to-library", headers=auth_headers
    )
    assert promote.status_code == 200
    assert promote.json()["promoted"].get("experience", 0) == 1

    entries = (await client.get("/api/v1/library", headers=auth_headers)).json()
    lib_entry_id = entries[0]["id"]
    clone = (await client.post(
        f"/api/v1/library/{lib_entry_id}/clone", headers=auth_headers
    )).json()

    cv2_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Second CV",
            "sections": [
                clone["section_instance"],
                {
                    "id": "sec_exp_local",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [{"title": "Local Extra", "company": "Initech"}],
                },
            ],
        },
        headers=auth_headers,
    )
    cv2_id = cv2_resp.json()["id"]

    delete = await client.delete(f"/api/v1/library/{lib_entry_id}", headers=auth_headers)
    assert delete.status_code == 204

    cv2 = (await client.get(f"/api/v1/cvs/{cv2_id}", headers=auth_headers)).json()
    section_titles = [s.get("title") for s in cv2["sections"]]
    # Cloned section's outer title (derived from first entry's title field) is
    # "Original Role".
    assert "Original Role" in section_titles


@pytest.mark.asyncio
async def test_promote_cv_to_library_extracts_sections(client, auth_headers, clean_library):
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Multi-section CV",
            "sections": [
                {"id": "s_exp", "type": "experience", "title": "Experience", "enabled": True, "data": [{"title": "Eng"}]},
                {"id": "s_edu", "type": "education", "title": "Education", "enabled": True, "data": [{"school": "Uni"}]},
                {"id": "s_sk", "type": "skills", "title": "Skills", "enabled": True, "data": [{"name": "Python"}]},
                {"id": "s_prof", "type": "profile", "title": "Profile", "enabled": True, "data": {"name": "X"}},
            ],
        },
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]

    promote = await client.post(
        f"/api/v1/cvs/{cv_id}/promote-to-library", headers=auth_headers
    )
    assert promote.status_code == 200
    body = promote.json()
    assert body["promoted"].get("experience") == 1
    assert body["promoted"].get("education") == 1
    assert body["promoted"].get("skill") == 1
    assert "s_prof" in body["skipped"]
    assert "library_id" in body


@pytest.mark.asyncio
async def test_promote_cv_to_library_accepts_all_renderer_section_types(
    client, auth_headers, clean_library
):
    sections = [
        {
            "id": "s_exp",
            "type": "experience",
            "title": "Experience",
            "enabled": True,
            "data": [{"id": "exp_1", "company": "Acme", "position": "Engineer"}],
        },
        {
            "id": "s_edu",
            "type": "education",
            "title": "Education",
            "enabled": True,
            "data": [{"id": "edu_1", "institution": "State U", "degree": "BS"}],
        },
        {
            "id": "s_skills",
            "type": "skills",
            "title": "Skills",
            "enabled": True,
            "data": [{"id": "skill_1", "category": "Languages", "items": ["Python"]}],
        },
        {
            "id": "s_projects",
            "type": "projects",
            "title": "Projects",
            "enabled": True,
            "data": [{"id": "project_1", "name": "Aergia"}],
        },
        {
            "id": "s_languages",
            "type": "languages",
            "title": "Languages",
            "enabled": True,
            "data": [{"id": "language_1", "language": "English"}],
        },
        {
            "id": "s_certifications",
            "type": "certifications",
            "title": "Certifications",
            "enabled": True,
            "data": [{"id": "cert_1", "name": "AWS"}],
        },
        {
            "id": "s_profile",
            "type": "profile",
            "title": "Profile",
            "enabled": True,
            "data": {"name": "X"},
        },
    ]
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={"title": "All renderer sections", "sections": sections},
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]

    promote = await client.post(
        f"/api/v1/cvs/{cv_id}/promote-to-library", headers=auth_headers
    )

    assert promote.status_code == 200
    assert promote.json()["promoted"] == {
        "experience": 1,
        "education": 1,
        "skill": 1,
        "project": 1,
        "language": 1,
        "certification": 1,
    }
    assert promote.json()["skipped"] == ["s_profile"]


@pytest.mark.asyncio
async def test_add_section_entry_accepts_plural_renderer_section_type(
    client, auth_headers, clean_library
):
    sections = [
        {
            "id": "s_skills",
            "type": "skills",
            "title": "Skills",
            "enabled": True,
            "data": [{"id": "skill_1", "category": "Languages", "items": ["Python"]}],
        },
        {
            "id": "s_projects",
            "type": "projects",
            "title": "Projects",
            "enabled": True,
            "data": [{"id": "project_1", "name": "Aergia"}],
        },
        {
            "id": "s_languages",
            "type": "languages",
            "title": "Languages",
            "enabled": True,
            "data": [{"id": "language_1", "language": "English"}],
        },
        {
            "id": "s_certifications",
            "type": "certifications",
            "title": "Certifications",
            "enabled": True,
            "data": [{"id": "cert_1", "name": "AWS"}],
        },
    ]
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={"title": "Plural entry sections", "sections": sections},
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]

    for section, kind in zip(sections, ("skill", "project", "language", "certification")):
        entry = section["data"][0]
        response = await client.post(
            f"/api/v1/cvs/{cv_id}/sections/{section['id']}/entries/{entry['id']}/add-to-library",
            json={"kind": kind, "entry": entry},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["created"] is True

    persisted_only = await client.post(
        f"/api/v1/cvs/{cv_id}/sections/s_skills/entries/skill_1/add-to-library",
        headers=auth_headers,
    )
    assert persisted_only.status_code == 200
    assert persisted_only.json()["created"] is False

    listing = (await client.get("/api/v1/library", headers=auth_headers)).json()
    assert {entry["kind"] for entry in listing} == {
        "skill",
        "project",
        "language",
        "certification",
    }


@pytest.mark.asyncio
async def test_promote_is_idempotent_via_content_hash(client, auth_headers, clean_library):
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Idem CV",
            "sections": [
                {"id": "s_a", "type": "experience", "title": "Experience", "enabled": True, "data": [{"title": "Eng"}]},
            ],
        },
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]

    first = (await client.post(
        f"/api/v1/cvs/{cv_id}/promote-to-library", headers=auth_headers
    )).json()
    second = (await client.post(
        f"/api/v1/cvs/{cv_id}/promote-to-library", headers=auth_headers
    )).json()
    assert first["promoted"].get("experience") == 1
    assert second["promoted"] == {}


@pytest.mark.asyncio
async def test_library_unaffected_by_renderer(client, auth_headers, clean_library):
    """Renderer pipeline never touches the Library tables."""
    await client.post(
        "/api/v1/library",
        json={"kind": "experience", "payload": [{"title": "X"}]},
        headers=auth_headers,
    )

    async with async_session() as db:
        lib_before = (await db.execute(sqlalchemy.select(sqlalchemy.func.count(Library.id)))).scalar_one()
        entry_before = (
            await db.execute(sqlalchemy.select(sqlalchemy.func.count(LibraryEntry.id)))
        ).scalar_one()

    cv = (await client.post(
        "/api/v1/cvs",
        json={"title": "Render Probe"},
        headers=auth_headers,
    )).json()
    preview = await client.get(f"/api/v1/cvs/{cv['id']}/preview", headers=auth_headers)
    assert preview.status_code == 200

    async with async_session() as db:
        lib_after = (await db.execute(sqlalchemy.select(sqlalchemy.func.count(Library.id)))).scalar_one()
        entry_after = (
            await db.execute(sqlalchemy.select(sqlalchemy.func.count(LibraryEntry.id)))
        ).scalar_one()
    assert lib_before == lib_after
    assert entry_before == entry_after


# ─── Per-entry Add to Library ────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_section_entry_to_library_uses_current_entry_snapshot(
    client, auth_headers, clean_library
):
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "CV with edited experience",
            "sections": [
                {
                    "id": "s_exp",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [{"id": "exp_1", "company": "Old Company", "position": "Engineer"}],
                }
            ],
        },
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]

    current_entry = {
        "id": "exp_1",
        "company": "Current Company",
        "position": "Lead Engineer",
    }
    resp = await client.post(
        f"/api/v1/cvs/{cv_id}/sections/s_exp/entries/exp_1/add-to-library",
        json={"kind": "experience", "entry": current_entry},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    listing = (await client.get("/api/v1/library?kind=experience", headers=auth_headers)).json()
    assert listing[0]["payload"] == [current_entry]


@pytest.mark.asyncio
async def test_add_section_entry_to_library_creates_entry(client, auth_headers, clean_library):
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "CV with one education entry",
            "sections": [
                {
                    "id": "s_edu",
                    "type": "education",
                    "title": "Education",
                    "enabled": True,
                    "data": [
                        {
                            "id": "edu_1",
                            "institution": "State U",
                            "degree": "BS",
                            "start_date": "2018",
                            "end_date": "2022",
                            "current": False,
                            "gpa": "",
                            "summary": "",
                        }
                    ],
                }
            ],
        },
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/cvs/{cv_id}/sections/s_edu/entries/edu_1/add-to-library",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] is True
    assert body["library_id"]
    assert body["entry_id"]

    # New Library entry exists with the right kind + payload shape.
    listing = (await client.get("/api/v1/library?kind=education", headers=auth_headers)).json()
    assert len(listing) == 1
    assert listing[0]["payload"] == [
        {
            "id": "edu_1",
            "institution": "State U",
            "degree": "BS",
            "start_date": "2018",
            "end_date": "2022",
            "current": False,
            "gpa": "",
            "summary": "",
        }
    ]


@pytest.mark.asyncio
async def test_add_section_entry_to_library_is_idempotent(client, auth_headers, clean_library):
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Idempotent CV",
            "sections": [
                {
                    "id": "s_exp",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [{"id": "exp_1", "company": "Acme", "position": "SWE"}],
                }
            ],
        },
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]

    first = (await client.post(
        f"/api/v1/cvs/{cv_id}/sections/s_exp/entries/exp_1/add-to-library",
        headers=auth_headers,
    )).json()
    second = (await client.post(
        f"/api/v1/cvs/{cv_id}/sections/s_exp/entries/exp_1/add-to-library",
        headers=auth_headers,
    )).json()
    assert first["created"] is True
    assert second["created"] is False
    assert first["entry_id"] == second["entry_id"]


@pytest.mark.asyncio
async def test_add_section_entry_to_library_rejects_ineligible_kind(
    client, auth_headers, clean_library
):
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Profile-only CV",
            "sections": [
                {
                    "id": "s_prof",
                    "type": "profile",
                    "title": "Profile",
                    "enabled": True,
                    "data": {"name": "Test"},
                }
            ],
        },
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/cvs/{cv_id}/sections/s_prof/entries/none/add-to-library",
        headers=auth_headers,
    )
    # Either 422 (not library-eligible) or 404 (no matching entry) — but never 200.
    assert resp.status_code in (404, 422)


@pytest.mark.asyncio
async def test_add_section_entry_to_library_other_users_cv_404(
    client, auth_headers, other_auth_headers, clean_library
):
    cv_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Private CV",
            "sections": [
                {
                    "id": "s_exp",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [{"id": "exp_1", "company": "Acme"}],
                }
            ],
        },
        headers=auth_headers,
    )
    cv_id = cv_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/cvs/{cv_id}/sections/s_exp/entries/exp_1/add-to-library",
        headers=other_auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_section_entry_to_library_missing_cv_404(client, auth_headers, clean_library):
    resp = await client.post(
        "/api/v1/cvs/00000000-0000-0000-0000-000000000000/sections/s_exp/entries/exp_1/add-to-library",
        headers=auth_headers,
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_research_library_crud_clone_and_promotion(client, auth_headers, clean_library):
    created = await client.post(
        "/api/v1/library",
        json={"kind": "research", "payload": [{"id": "r1", "title": "Systems Paper"}]},
        headers=auth_headers,
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/library/{entry_id}",
        json={"payload": [{"id": "r1", "title": "Updated Systems Paper"}]},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    clone = await client.post(f"/api/v1/library/{entry_id}/clone", headers=auth_headers)
    assert clone.status_code == 200
    assert clone.json()["section_instance"]["type"] == "research"
    assert clone.json()["section_instance"]["data"] == [{"id": "r1", "title": "Updated Systems Paper"}]

    cv = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Research CV",
            "sections": [
                {
                    "id": "research-section",
                    "type": "research",
                    "title": "Research",
                    "enabled": True,
                    "data": [{"id": "r2", "title": "Promotable Paper"}],
                }
            ],
        },
        headers=auth_headers,
    )
    promoted = await client.post(
        f"/api/v1/cvs/{cv.json()['id']}/promote-to-library",
        headers=auth_headers,
    )
    assert promoted.status_code == 200
    assert promoted.json()["promoted"]["research"] == 1

    snapshot = await client.post(
        f"/api/v1/cvs/{cv.json()['id']}/sections/research-section/entries/r2/add-to-library",
        json={"kind": "research", "entry": {"id": "r2", "title": "Current Paper"}},
        headers=auth_headers,
    )
    assert snapshot.status_code == 200
    research_entries = await client.get("/api/v1/library?kind=research", headers=auth_headers)
    assert research_entries.status_code == 200
    assert any(entry["payload"] == [{"id": "r2", "title": "Current Paper"}] for entry in research_entries.json())
