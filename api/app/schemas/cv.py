from datetime import datetime

from pydantic import BaseModel


class CVCreate(BaseModel):
    title: str
    description: str | None = None
    template_id: str = "generic-modern"
    sections: dict = {"order": [], "enabled": [], "data": {}}
    customizations: dict = {}
    extra_metadata: dict = {}


class CVUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    template_id: str | None = None
    sections: dict | None = None
    customizations: dict | None = None


class CVResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    description: str | None
    template_id: str
    customizations: dict
    sections: dict
    extra_metadata: dict
    created_at: datetime
    updated_at: datetime


class CVListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    template_id: str
    created_at: datetime
    updated_at: datetime
