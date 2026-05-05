from pydantic import BaseModel


class TemplateListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str | None
    preview_image_url: str | None
    is_user_template: bool = False

    @classmethod
    def model_validate(cls, obj):
        data = super().model_validate(obj)
        data.is_user_template = not obj.is_system
        return data


class TemplateDetail(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str | None
    preview_image_url: str | None
    default_customizations: dict | None
    manifest: dict | None = None
    assets: dict | None = None
    generated_html_url: str | None = None
    is_user_template: bool = False

    @classmethod
    def model_validate(cls, obj):
        data = super().model_validate(obj)
        data.is_user_template = not obj.is_system
        return data


class UserTemplateCreate(BaseModel):
    name: str
    manifest: dict | None = None
    description: str | None = None
    default_customizations: dict | None = None
