from datetime import datetime

from pydantic import BaseModel, model_validator

from app.schemas.sections import SECTION_DATA_MODELS, SectionStyle


DEFAULT_SECTIONS = [
    {
        "id": "sec_profile",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "", "title": "", "email": "", "phone": "", "location": "", "summary": "", "photo_url": ""},
    }
]


class ValidatedSectionInstance(BaseModel):
    """Section instance with type-aware data validation."""
    id: str
    type: str
    title: str
    enabled: bool = True
    data: list | dict = {}
    style: SectionStyle | None = None

    @model_validator(mode="after")
    def validate_data(self):
        model_def = SECTION_DATA_MODELS.get(self.type)
        if model_def is None:
            return self  # unknown type, pass through
        if isinstance(model_def, list):
            # List-based type (experience, education, skills, projects, languages, certifications)
            entry_model = model_def[0]
            if isinstance(self.data, list):
                validated = []
                for item in self.data:
                    if isinstance(item, dict):
                        validated.append(entry_model(**item).model_dump())
                    else:
                        validated.append(item)
                self.data = validated
            else:
                raise ValueError(f"Expected list for section type '{self.type}', got {type(self.data).__name__}")
        else:
            # Object-based type (profile)
            if isinstance(self.data, dict):
                validated = model_def(**self.data)
                self.data = validated.model_dump()
            else:
                raise ValueError(f"Expected dict for section type '{self.type}', got {type(self.data).__name__}")
        return self


class CVCreate(BaseModel):
    title: str
    description: str | None = None
    template_id: str = "generic-modern"
    sections: list[ValidatedSectionInstance] | dict = DEFAULT_SECTIONS
    customizations: dict = {}
    extra_metadata: dict = {}


class CVUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    template_id: str | None = None
    sections: list[ValidatedSectionInstance] | dict | None = None
    customizations: dict | None = None


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


class CVListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    template_id: str
    created_at: datetime
    updated_at: datetime
