from datetime import datetime

from pydantic import BaseModel


DEFAULT_SECTIONS = [
    {
        "id": "sec_profile",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "", "title": "", "email": "", "phone": "", "location": "", "summary": "", "photo_url": ""},
    }
]


class CVCreate(BaseModel):
    title: str
    description: str | None = None
    template_id: str = "generic-modern"
    sections: list | dict = DEFAULT_SECTIONS
    customizations: dict = {}
    extra_metadata: dict = {}
    template_content: str | None = None


class CVUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    template_id: str | None = None
    sections: list | dict | None = None
    customizations: dict | None = None
    template_content: str | None = None


class CVResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    description: str | None
    template_id: str
    customizations: dict
    sections: list | dict
    extra_metadata: dict
    created_at: datetime
    updated_at: datetime
    template_content: str | None = None


class CVListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    template_id: str
    created_at: datetime
    updated_at: datetime
