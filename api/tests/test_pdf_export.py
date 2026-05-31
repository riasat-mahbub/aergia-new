"""T49, T50, T52: PDF export tests"""

import pytest

SAMPLE_INSTANCES = [
    {
        "id": "sec_profile",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Jane Doe",
            "title": "Software Engineer",
            "email": "jane@example.com",
            "phone": "+1 555-1234",
            "location": "Boston, MA",
            "summary": "Experienced engineer building great products.",
            "photo_url": "",
        },
    },
    {
        "id": "sec_experience",
        "type": "experience",
        "title": "Experience",
        "enabled": True,
        "data": [
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
    },
    {
        "id": "sec_education",
        "type": "education",
        "title": "Education",
        "enabled": True,
        "data": [
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
    },
    {
        "id": "sec_skills",
        "type": "skills",
        "title": "Skills",
        "enabled": True,
        "data": [
            {"id": "sk_1", "category": "Frontend", "items": ["React", "TypeScript"]},
        ],
    },
    {
        "id": "sec_languages",
        "type": "languages",
        "title": "Languages",
        "enabled": True,
        "data": [
            {"id": "lang_1", "language": "English", "proficiency": "Native"},
        ],
    },
]


async def register_and_login(client, email: str) -> dict:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_pdf_export_valid_pdf_all_templates(client):
    """T49: PDF export returns valid PDF for all 3 templates"""
    headers = await register_and_login(client, "pdf-t49@example.com")
    templates = ["generic-modern", "generic-classic", "generic-minimal"]

    for template_id in templates:
        create_resp = await client.post(
            "/api/v1/cvs",
            json={"title": f"PDF Test {template_id}", "template_id": template_id, "sections": SAMPLE_INSTANCES},
            headers=headers,
        )
        cv_id = create_resp.json()["id"]

        export_resp = await client.post(f"/api/v1/cvs/{cv_id}/export/pdf", headers=headers)
        assert export_resp.status_code == 200
        assert export_resp.headers["content-type"] == "application/pdf"
        assert export_resp.content[:5] == b"%PDF-"
        assert len(export_resp.content) > 1000


@pytest.mark.asyncio
async def test_pdf_content_matches_cv_data(client):
    """T50: PDF content matches CV data"""
    headers = await register_and_login(client, "pdf-t50@example.com")

    create_resp = await client.post(
        "/api/v1/cvs",
        json={"title": "Content Check CV", "template_id": "generic-modern", "sections": SAMPLE_INSTANCES},
        headers=headers,
    )
    cv_id = create_resp.json()["id"]

    export_resp = await client.post(f"/api/v1/cvs/{cv_id}/export/pdf", headers=headers)
    assert export_resp.status_code == 200

    # Extract text from compressed PDF using pypdf
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(export_resp.content))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    assert "Jane Doe" in text
    assert "Software Engineer" in text
    assert "Acme Corp" in text
    assert "MIT" in text


@pytest.mark.asyncio
async def test_pdf_export_nonexistent_cv(client):
    """T52: PDF export fails gracefully for non-existent CV"""
    headers = await register_and_login(client, "pdf-t52@example.com")
    export_resp = await client.post("/api/v1/cvs/nonexistent-id/export/pdf", headers=headers)
    assert export_resp.status_code == 404


@pytest.mark.asyncio
async def test_pdf_export_respects_custom_zone_layout(client):
    """PDF export honours the CV's customizations.layout (zone widths, styles)."""
    headers = await register_and_login(client, "pdf-custom-layout@example.com")
    custom_layout = {
        "zones": [
            {"id": "left", "styles": {"width": "40%", "background-color": "#f0f0f0", "padding": "16px"}},
            {"id": "right", "styles": {"width": "60%", "padding": "16px"}},
        ],
        "placement": {"sec_profile": "left", "sec_experience": "right"},
    }
    create_resp = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Custom PDF Layout",
            "template_id": "generic-modern",
            "sections": SAMPLE_INSTANCES,
            "customizations": {"layout": custom_layout},
        },
        headers=headers,
    )
    cv_id = create_resp.json()["id"]
    export_resp = await client.post(f"/api/v1/cvs/{cv_id}/export/pdf", headers=headers)
    assert export_resp.status_code == 200
    assert export_resp.content[:5] == b"%PDF-"
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(export_resp.content))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Jane Doe" in text
    assert "Acme" in text
