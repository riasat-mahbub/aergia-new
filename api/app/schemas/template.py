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
    layout_config: dict
    section_schema: dict
    default_customizations: dict | None
    content: str | None = None
    is_user_template: bool = False

    @classmethod
    def model_validate(cls, obj):
        data = super().model_validate(obj)
        data.is_user_template = not obj.is_system
        if data.is_user_template:
            data.content = obj.content
        return data


class UserTemplateCreate(BaseModel):
    name: str
    content: str
