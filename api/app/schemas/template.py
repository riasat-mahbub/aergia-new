from pydantic import BaseModel


class TemplateListItem(BaseModel):
    id: str
    name: str
    description: str | None
    preview_image_url: str | None


class TemplateDetail(BaseModel):
    id: str
    name: str
    description: str | None
    preview_image_url: str | None
    layout_config: dict
    section_schema: dict
    default_customizations: dict | None
