from __future__ import annotations

import base64
from email import policy
from email.parser import BytesParser

import httpx
import pytest

from app.services.tailoring_google import (
    GoogleWorkspaceConflictError,
    GoogleWorkspaceError,
    GoogleWorkspaceTransport,
    GoogleWorkspaceUnsupportedDocumentError,
)


def _document_payload(
    document_id: str = "doc_123-test",
    *,
    text: str = "",
    revision_id: str = "rev-1",
) -> dict[str, object]:
    end_index = 2 + max(0, len(text) - 1)
    return {
        "documentId": document_id,
        "title": "Synthetic tailoring request",
        "revisionId": revision_id,
        "body": {
            "content": [
                {"startIndex": 0, "endIndex": 1, "sectionBreak": {}},
                {
                    "startIndex": 1,
                    "endIndex": end_index,
                    "paragraph": {
                        "elements": [
                            {"startIndex": 1, "endIndex": end_index, "textRun": {"content": text or "\n"}}
                        ]
                    },
                },
            ]
        },
    }


def _tab_document_payload(
    *, text: str, revision_id: str = "rev-1", document_id: str = "doc_123-test"
) -> dict[str, object]:
    payload = _document_payload(document_id, text=text, revision_id=revision_id)
    payload.pop("body")
    payload["tabs"] = [
        {
            "tabProperties": {"tabId": "tab-1"},
            "documentTab": {"body": _document_payload(document_id, text=text)["body"]},
        }
    ]
    return payload


def _client(handler: httpx.AsyncBaseTransport | object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_and_read_document_uses_oauth_and_extracts_plain_text() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(200, json=_document_payload(text=""))
        return httpx.Response(200, json=_tab_document_payload(text="Job only\n"))

    async with _client(httpx.MockTransport(handler)) as client:
        transport = GoogleWorkspaceTransport(client, "synthetic-access-token")
        created = await transport.create_document("Synthetic tailoring request")
        loaded = await transport.get_document(created.document_id)

    assert created.document_id == "doc_123-test"
    assert loaded.text == "Job only\n"
    assert "Job only" not in repr(loaded)
    assert loaded.revision_id == "rev-1"
    assert all(request.headers["authorization"] == "Bearer synthetic-access-token" for request in requests)
    assert requests[1].url.params["includeTabsContent"] == "true"


@pytest.mark.asyncio
async def test_replace_document_text_is_whole_body_atomic_and_revision_fenced() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=_tab_document_payload(text="old\n"))
        return httpx.Response(200, json={"writeControl": {"requiredRevisionId": "rev-2"}})

    async with _client(httpx.MockTransport(handler)) as client:
        transport = GoogleWorkspaceTransport(client, "synthetic-access-token")
        new_revision = await transport.replace_document_text("doc_123-test", "new structured content\n")

    update_request = requests[1]
    body = __import__("json").loads(update_request.content)
    assert requests[0].method == "GET"
    assert update_request.url.path.endswith("/documents/doc_123-test:batchUpdate")
    assert body["writeControl"] == {"requiredRevisionId": "rev-1"}
    assert body["requests"] == [
        {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": 4}}},
        {"insertText": {"location": {"index": 1}, "text": "new structured content\n"}},
    ]
    assert new_revision == "rev-2"


@pytest.mark.asyncio
async def test_replace_refuses_stale_expected_revision_without_writing() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_tab_document_payload(text="old\n", revision_id="latest"))

    async with _client(httpx.MockTransport(handler)) as client:
        transport = GoogleWorkspaceTransport(client, "synthetic-access-token")
        with pytest.raises(GoogleWorkspaceConflictError) as raised:
            await transport.replace_document_text(
                "doc_123-test", "new\n", expected_revision_id="stale"
            )

    assert raised.value.retryable is True
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_multi_tab_document_is_rejected_to_avoid_partial_replacement() -> None:
    payload = _tab_document_payload(text="one\n")
    payload["tabs"] = [*payload["tabs"], *payload["tabs"]]  # type: ignore[index]

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with _client(httpx.MockTransport(handler)) as client:
        transport = GoogleWorkspaceTransport(client, "synthetic-access-token")
        with pytest.raises(GoogleWorkspaceUnsupportedDocumentError):
            await transport.get_document("doc_123-test")


@pytest.mark.asyncio
async def test_self_request_email_contains_only_request_id_and_private_doc_url() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"id": "synthetic-message-id"})

    async with _client(httpx.MockTransport(handler)) as client:
        transport = GoogleWorkspaceTransport(client, "synthetic-access-token")
        message_id = await transport.send_request_email("person@example.com", "req_123", "doc_123-test")

    payload = __import__("json").loads(captured[0].content)
    raw = payload["raw"]
    decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    message = BytesParser(policy=policy.default).parsebytes(decoded)
    body = message.get_content()
    assert captured[0].url.path.endswith("/users/me/messages/send")
    assert message["From"] == "person@example.com"
    assert message["To"] == "person@example.com"
    assert message["Subject"] == "[Aergia Tailoring] req_123"
    assert body.replace("\r\n", "\n") == (
        "Request ID: req_123\nGoogle Doc: https://docs.google.com/document/d/doc_123-test/edit\n"
    )
    assert "CV" not in body
    assert message_id == "synthetic-message-id"


@pytest.mark.asyncio
async def test_trash_and_unauthorized_error_are_safe() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/files/file_123"):
            return httpx.Response(200, json={"id": "file_123", "trashed": True})
        return httpx.Response(
            401,
            json={"error": {"message": "private response detail", "status": "UNAUTHENTICATED"}},
        )

    async with _client(httpx.MockTransport(handler)) as client:
        transport = GoogleWorkspaceTransport(client, "synthetic-access-token")
        await transport.trash_file("file_123")
        with pytest.raises(GoogleWorkspaceError) as raised:
            await transport.get_document("doc_123-test")

    assert requests[0].method == "PATCH"
    assert __import__("json").loads(requests[0].content) == {"trashed": True}
    assert raised.value.unauthorized is True
    assert raised.value.status_code == 401
    assert "private response detail" not in str(raised.value)
    assert "synthetic-access-token" not in repr(transport)
