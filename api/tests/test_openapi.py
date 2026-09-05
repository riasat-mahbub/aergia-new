"""Focused checks for the development OpenAPI surface."""

from app.app import app
from app.config import Settings


def _operations():
    schema = app.openapi()
    for path, item in schema["paths"].items():
        for method, operation in item.items():
            if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head", "trace"}:
                yield path, method, operation


def test_api_docs_are_same_origin_and_disabled_in_production():
    assert app.docs_url == "/api/docs"
    assert app.redoc_url is None
    assert app.openapi_url == "/api/openapi.json"
    assert Settings(environment="production").api_docs_enabled is False


def test_every_operation_has_one_tag_and_a_unique_operation_id():
    operations = list(_operations())
    operation_ids = [operation["operationId"] for _, _, operation in operations]
    assert len(operation_ids) == len(set(operation_ids))
    assert all(len(operation.get("tags", [])) == 1 for _, _, operation in operations)


def test_openapi_contains_the_primary_api_groups():
    schema = app.openapi()
    tags = {tag for _, _, operation in _operations() for tag in operation.get("tags", [])}
    assert {"auth", "cvs", "applications", "library", "render", "tailoring", "system"} <= tags
    assert "/api/v1/cvs" in schema["paths"]
    assert "/api/v1/tailoring/exchange" in schema["paths"]
