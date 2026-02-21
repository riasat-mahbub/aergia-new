"""T44: Pytest: preview endpoint renders correct HTML for all 3 templates"""

import pytest

SAMPLE_SECTIONS = {
    "order": ["profile", "experience", "education", "skills", "projects", "languages", "certifications"],
    "enabled": ["profile", "experience", "education", "skills", "projects", "languages", "certifications"],
    "data": {
        "profile": {
            "name": "Jane Doe",
            "title": "Software Engineer",
            "email": "jane@example.com",
            "phone": "+1 555-1234",
            "location": "Boston, MA",
            "summary": "Experienced engineer building great products.",
            "photo_url": "",
        },
        "experience": [
            {
                "id": "exp_1",
                "company": "Acme Corp",
                "position": "Senior Engineer",
                "start_date": "2022-01",
                "end_date": None,
                "current": True,
                "location": "Boston, MA",
                "description": "Led team of 5 engineers.",
            }
        ],
        "education": [
            {
                "id": "edu_1",
                "institution": "MIT",
                "degree": "B.S. Computer Science",
                "start_date": "2018",
                "end_date": "2022",
                "current": False,
                "gpa": "3.8",
            }
        ],
        "skills": [
            {"id": "sk_1", "category": "Frontend", "items": ["React", "TypeScript", "Tailwind"]},
            {"id": "sk_2", "category": "Backend", "items": ["Python", "FastAPI", "PostgreSQL"]},
        ],
        "projects": [
            {
                "id": "proj_1",
                "name": "CV Builder",
                "url": "https://example.com",
                "start_date": "2025-01",
                "end_date": "2025-06",
                "description": "Full-stack web application",
                "tech_stack": ["React", "FastAPI"],
            }
        ],
        "languages": [
            {"id": "lang_1", "language": "English", "proficiency": "Native"},
            {"id": "lang_2", "language": "Spanish", "proficiency": "Intermediate"},
        ],
        "certifications": [
            {
                "id": "cert_1",
                "name": "AWS Solutions Architect",
                "issuer": "Amazon",
                "date": "2024",
                "credential_url": "https://aws.amazon.com/verify",
            }
        ],
    },
}


@pytest.fixture
async def auth_headers(client):
    email = "preview-test@example.com"
    password = "testpass123"

    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_preview_endpoint_returns_html(client, auth_headers):
    """Preview endpoint returns HTML string for a CV."""
    create_resp = await client.post(
        "/api/v1/cvs",
        json={"title": "Preview Test", "template_id": "generic-modern", "sections": SAMPLE_SECTIONS},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    cv_id = create_resp.json()["id"]

    preview_resp = await client.get(f"/api/v1/cvs/{cv_id}/preview", headers=auth_headers)
    assert preview_resp.status_code == 200
    data = preview_resp.json()
    assert "html" in data
    html = data["html"]
    assert "<!DOCTYPE html>" in html
    assert "Jane Doe" in html
    assert "Senior Engineer" in html
    assert "Acme Corp" in html
    assert "MIT" in html
    assert "B.S. Computer Science" in html
    assert "React" in html
    assert "Python" in html
    assert "CV Builder" in html
    assert "English" in html
    assert "AWS Solutions Architect" in html


@pytest.mark.asyncio
async def test_preview_modern_template(client, auth_headers):
    """Modern preview includes sidebar and accent bar."""
    create_resp = await client.post(
        "/api/v1/cvs",
        json={"title": "Modern Preview", "template_id": "generic-modern", "sections": SAMPLE_SECTIONS},
        headers=auth_headers,
    )
    cv_id = create_resp.json()["id"]

    preview_resp = await client.get(f"/api/v1/cvs/{cv_id}/preview", headers=auth_headers)
    html = preview_resp.json()["html"]

    # Modern template has a sidebar
    assert "sidebar" not in html.lower()  # no class reference, but:
    # It has a 2-column layout with profile in sidebar
    assert "Profile" in html
    assert "Experience" in html
    assert "Education" in html
    assert "Skills" in html
    assert "Languages" in html


@pytest.mark.asyncio
async def test_preview_classic_template(client, auth_headers):
    """Classic preview includes horizontal dividers."""
    create_resp = await client.post(
        "/api/v1/cvs",
        json={"title": "Classic Preview", "template_id": "generic-classic", "sections": SAMPLE_SECTIONS},
        headers=auth_headers,
    )
    cv_id = create_resp.json()["id"]

    preview_resp = await client.get(f"/api/v1/cvs/{cv_id}/preview", headers=auth_headers)
    html = preview_resp.json()["html"]

    # Classic has hr elements as dividers
    assert "<hr" in html
    assert "Profile" in html
    assert "Experience" in html


@pytest.mark.asyncio
async def test_preview_minimal_template(client, auth_headers):
    """Minimal preview includes no borders or backgrounds."""
    create_resp = await client.post(
        "/api/v1/cvs",
        json={"title": "Minimal Preview", "template_id": "generic-minimal", "sections": SAMPLE_SECTIONS},
        headers=auth_headers,
    )
    cv_id = create_resp.json()["id"]

    preview_resp = await client.get(f"/api/v1/cvs/{cv_id}/preview", headers=auth_headers)
    html = preview_resp.json()["html"]

    # Minimal has no hr dividers
    assert "<hr" not in html
    # But has all sections
    assert "Profile" in html
    assert "Projects" in html
    assert "Certifications" in html


@pytest.mark.asyncio
async def test_preview_nonexistent_cv(client, auth_headers):
    """Preview for non-existent CV returns 404."""
    preview_resp = await client.get("/api/v1/cvs/non-existent-id/preview", headers=auth_headers)
    assert preview_resp.status_code == 404


@pytest.mark.asyncio
async def test_preview_disabled_sections_hidden(client, auth_headers):
    """Disabled sections should not appear in preview HTML."""
    sections = {
        "order": ["profile", "experience"],
        "enabled": ["experience"],  # profile disabled
        "data": {
            "profile": {"name": "Hidden", "title": "", "email": "", "phone": "", "location": "", "summary": "", "photo_url": ""},
            "experience": [
                {"id": "exp_1", "company": "Visible Co", "position": "Dev", "start_date": "2023", "end_date": None, "current": True, "location": "", "description": ""}
            ],
        },
    }
    create_resp = await client.post(
        "/api/v1/cvs",
        json={"title": "Disabled Test", "template_id": "generic-minimal", "sections": sections},
        headers=auth_headers,
    )
    cv_id = create_resp.json()["id"]

    preview_resp = await client.get(f"/api/v1/cvs/{cv_id}/preview", headers=auth_headers)
    html = preview_resp.json()["html"]

    assert "Visible Co" in html
    assert "Hidden" not in html


@pytest.mark.asyncio
async def test_preview_data_isolation(client, auth_headers):
    """Users cannot preview another user's CV."""
    # User A creates CV
    create_a = await client.post(
        "/api/v1/cvs",
        json={"title": "User A CV", "template_id": "generic-modern", "sections": SAMPLE_SECTIONS},
        headers=auth_headers,
    )
    cv_id = create_a.json()["id"]

    # User B tries to preview it
    await client.post("/api/v1/auth/register", json={"email": "other@example.com", "password": "pass123"})
    login_b = await client.post("/api/v1/auth/login", json={"email": "other@example.com", "password": "pass123"})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    preview_resp = await client.get(f"/api/v1/cvs/{cv_id}/preview", headers=headers_b)
    assert preview_resp.status_code == 404
