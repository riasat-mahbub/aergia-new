"""Small Google Workspace REST transport for the local tailoring flow.

OAuth/token lifecycle belongs to the caller. This module accepts an existing
HTTPX client and access token and never logs request or response contents.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.policy import SMTP
from typing import Any

import httpx
from email_validator import EmailNotValidError, validate_email

_DOCS_API = "https://docs.googleapis.com/v1"
_DRIVE_API = "https://www.googleapis.com/drive/v3"
_GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
_ID_RE = re.compile(r"[A-Za-z0-9_-]+\Z")


class GoogleWorkspaceError(RuntimeError):
    """Safe, structured error raised by the Google Workspace transport."""

    def __init__(
        self,
        message: str,
        *,
        operation: str,
        status_code: int | None = None,
        retryable: bool = False,
        unauthorized: bool = False,
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.status_code = status_code
        self.retryable = retryable
        self.unauthorized = unauthorized


class GoogleWorkspaceConflictError(GoogleWorkspaceError):
    """The requested document revision is no longer current."""


class GoogleWorkspaceUnsupportedDocumentError(GoogleWorkspaceError):
    """The transport cannot safely treat the document as one plain text body."""


class GoogleWorkspaceProtocolError(GoogleWorkspaceError):
    """Google returned a successful response with an unexpected shape."""


@dataclass(frozen=True, slots=True)
class GoogleDocument:
    document_id: str
    title: str
    text: str = field(repr=False)
    revision_id: str | None


class GoogleWorkspaceTransport:
    """REST calls for Docs, Gmail, and Drive using caller-owned OAuth state."""

    __slots__ = ("_access_token", "_client")

    def __init__(self, client: httpx.AsyncClient, access_token: str) -> None:
        if not isinstance(client, httpx.AsyncClient):
            raise TypeError("client must be an httpx.AsyncClient")
        if not isinstance(access_token, str) or not access_token or "\r" in access_token or "\n" in access_token:
            raise ValueError("access_token must be a non-empty token")
        self._client = client
        self._access_token = access_token

    def __repr__(self) -> str:
        return "GoogleWorkspaceTransport(access_token=[redacted])"

    async def create_document(self, title: str) -> GoogleDocument:
        """Create a blank private-by-default Docs file and return its ID."""

        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        response = await self._request(
            "POST",
            f"{_DOCS_API}/documents",
            operation="create_document",
            json={"title": title},
        )
        payload = self._json_object(response, operation="create_document")
        return self._document_from_payload(payload, operation="create_document")

    async def get_document(self, document_id: str) -> GoogleDocument:
        """Read the designated single-tab document as plain text."""

        document_id = self._validate_id(document_id, "document_id")
        response = await self._request(
            "GET",
            f"{_DOCS_API}/documents/{document_id}",
            operation="get_document",
            params={"includeTabsContent": "true"},
        )
        payload = self._json_object(response, operation="get_document")
        document = self._document_from_payload(payload, operation="get_document")
        if document.document_id != document_id:
            raise GoogleWorkspaceProtocolError(
                "Google returned a different document than requested",
                operation="get_document",
            )
        return document

    async def replace_document_text(
        self,
        document_id: str,
        text: str,
        *,
        expected_revision_id: str | None = None,
    ) -> str | None:
        """Replace all text in the sole document tab with a revision fence.

        When the caller supplies ``expected_revision_id``, it must still be
        current. Otherwise the revision read here is used as a fence so edits
        made by another client between GET and batchUpdate are rejected.
        Returns the new revision ID when Google includes it in the response.
        """

        document_id = self._validate_id(document_id, "document_id")
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        response = await self._request(
            "GET",
            f"{_DOCS_API}/documents/{document_id}",
            operation="replace_document_text",
            params={"includeTabsContent": "true"},
        )
        payload = self._json_object(response, operation="replace_document_text")
        document = self._document_from_payload(payload, operation="replace_document_text")
        if document.document_id != document_id:
            raise GoogleWorkspaceProtocolError(
                "Google returned a different document than requested",
                operation="replace_document_text",
            )
        if not document.revision_id:
            raise GoogleWorkspaceProtocolError(
                "Google did not return an editable document revision",
                operation="replace_document_text",
            )
        if expected_revision_id is not None and expected_revision_id != document.revision_id:
            raise GoogleWorkspaceConflictError(
                "Google document changed since the expected revision",
                operation="replace_document_text",
                retryable=True,
            )

        body = self._single_body(payload, operation="replace_document_text")
        end_index = self._body_end_index(body)
        requests: list[dict[str, Any]] = []
        # Docs requires the final newline in a body to remain. startIndex=1 is
        # the first editable position; endIndex is one past that final newline.
        if end_index > 2:
            requests.append(
                {
                    "deleteContentRange": {
                        "range": {"startIndex": 1, "endIndex": end_index - 1}
                    }
                }
            )
        if text:
            requests.append({"insertText": {"location": {"index": 1}, "text": text}})
        if not requests:
            return document.revision_id

        update_response = await self._request(
            "POST",
            f"{_DOCS_API}/documents/{document_id}:batchUpdate",
            operation="replace_document_text",
            json={
                "requests": requests,
                "writeControl": {"requiredRevisionId": document.revision_id},
            },
        )
        if not update_response.content:
            return None
        result = self._json_object(update_response, operation="replace_document_text")
        write_control = result.get("writeControl")
        if not isinstance(write_control, dict):
            return None
        revision_id = write_control.get("requiredRevisionId")
        return revision_id if isinstance(revision_id, str) else None

    async def send_request_email(
        self,
        self_email: str,
        request_id: str,
        document_id: str,
    ) -> str | None:
        """Send the self-addressed trigger containing only ID and Docs URL.

        The constrained signature intentionally gives the transport no CV or
        arbitrary message-body input to accidentally place in email.
        """

        recipient = self._validate_email(self_email)
        if not isinstance(request_id, str) or not _ID_RE.fullmatch(request_id):
            raise ValueError("request_id must contain only letters, numbers, '_' or '-'")
        document_id = self._validate_id(document_id, "document_id")
        document_url = f"https://docs.google.com/document/d/{document_id}/edit"

        message = EmailMessage(policy=SMTP)
        message["From"] = recipient
        message["To"] = recipient
        message["Subject"] = f"[Aergia Tailoring] {request_id}"
        message.set_content(
            f"Request ID: {request_id}\nGoogle Doc: {document_url}\n",
            subtype="plain",
            charset="utf-8",
        )
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")

        response = await self._request(
            "POST",
            f"{_GMAIL_API}/users/me/messages/send",
            operation="send_request_email",
            json={"raw": raw},
        )
        if not response.content:
            return None
        result = self._json_object(response, operation="send_request_email")
        message_id = result.get("id")
        return message_id if isinstance(message_id, str) else None

    async def trash_file(self, file_id: str) -> None:
        """Move a caller-designated Drive file to the trash."""

        file_id = self._validate_id(file_id, "file_id")
        response = await self._request(
            "PATCH",
            f"{_DRIVE_API}/files/{file_id}",
            operation="trash_file",
            params={"supportsAllDrives": "true"},
            json={"trashed": True},
        )
        if response.content:
            self._json_object(response, operation="trash_file")

    async def _request(self, method: str, url: str, *, operation: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self._access_token}"
        try:
            response = await self._client.request(method, url, headers=headers, **kwargs)
        except httpx.TransportError:
            raise GoogleWorkspaceError(
                "Google Workspace transport failed",
                operation=operation,
                retryable=True,
            ) from None

        if response.is_error:
            self._raise_http_error(response, operation=operation)
        return response

    @staticmethod
    def _json_object(response: httpx.Response, *, operation: str) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            raise GoogleWorkspaceProtocolError(
                "Google returned an invalid JSON response",
                operation=operation,
                status_code=response.status_code,
            ) from None
        if not isinstance(payload, dict):
            raise GoogleWorkspaceProtocolError(
                "Google returned an unexpected response shape",
                operation=operation,
                status_code=response.status_code,
            )
        return payload

    @classmethod
    def _document_from_payload(cls, payload: dict[str, Any], *, operation: str) -> GoogleDocument:
        document_id = payload.get("documentId")
        title = payload.get("title")
        revision_id = payload.get("revisionId")
        if not isinstance(document_id, str) or not _ID_RE.fullmatch(document_id):
            raise GoogleWorkspaceProtocolError(
                "Google returned a document without a valid ID",
                operation=operation,
            )
        if not isinstance(title, str):
            raise GoogleWorkspaceProtocolError(
                "Google returned a document without a title",
                operation=operation,
            )
        if revision_id is not None and not isinstance(revision_id, str):
            raise GoogleWorkspaceProtocolError(
                "Google returned an invalid document revision",
                operation=operation,
            )
        body = cls._single_body(payload, operation=operation)
        return GoogleDocument(
            document_id=document_id,
            title=title,
            text=cls._plain_text(body),
            revision_id=revision_id,
        )

    @staticmethod
    def _single_body(payload: dict[str, Any], *, operation: str) -> dict[str, Any]:
        """Return the sole tab's body; reject multi-tab docs to avoid ambiguity."""

        tabs = payload.get("tabs")
        if isinstance(tabs, list) and tabs:
            flattened: list[dict[str, Any]] = []

            def add_tabs(items: list[Any]) -> None:
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    flattened.append(item)
                    child_tabs = item.get("childTabs")
                    if isinstance(child_tabs, list):
                        add_tabs(child_tabs)

            add_tabs(tabs)
            if len(flattened) != 1:
                raise GoogleWorkspaceUnsupportedDocumentError(
                    "Google document must have exactly one tab",
                    operation=operation,
                )
            document_tab = flattened[0].get("documentTab")
            if not isinstance(document_tab, dict):
                raise GoogleWorkspaceProtocolError(
                    "Google returned a tab without document content",
                    operation=operation,
                )
            body = document_tab.get("body")
        else:
            body = payload.get("body")
        if not isinstance(body, dict):
            raise GoogleWorkspaceProtocolError(
                "Google returned a document without body content",
                operation=operation,
            )
        return body

    @staticmethod
    def _plain_text(body: dict[str, Any]) -> str:
        content = body.get("content")
        if not isinstance(content, list):
            return ""

        pieces: list[str] = []
        for structural_element in content:
            if not isinstance(structural_element, dict):
                continue
            paragraph = structural_element.get("paragraph")
            if isinstance(paragraph, dict):
                elements = paragraph.get("elements")
                if isinstance(elements, list):
                    for element in elements:
                        if not isinstance(element, dict):
                            continue
                        text_run = element.get("textRun")
                        if isinstance(text_run, dict) and isinstance(text_run.get("content"), str):
                            pieces.append(text_run["content"])
                continue

            table = structural_element.get("table")
            if isinstance(table, dict):
                rows = table.get("tableRows")
                if isinstance(rows, list):
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        cells = row.get("tableCells")
                        if not isinstance(cells, list):
                            continue
                        cell_texts = [GoogleWorkspaceTransport._plain_text(cell) for cell in cells if isinstance(cell, dict)]
                        pieces.append("\t".join(cell_text.rstrip("\n") for cell_text in cell_texts) + "\n")
                continue

            table_of_contents = structural_element.get("tableOfContents")
            if isinstance(table_of_contents, dict):
                pieces.append(GoogleWorkspaceTransport._plain_text(table_of_contents))
        return "".join(pieces)

    @staticmethod
    def _body_end_index(body: dict[str, Any]) -> int:
        content = body.get("content")
        if not isinstance(content, list) or not content:
            return 1
        last = content[-1]
        if not isinstance(last, dict) or not isinstance(last.get("endIndex"), int):
            raise GoogleWorkspaceProtocolError(
                "Google returned body content without an end index",
                operation="replace_document_text",
            )
        return last["endIndex"]

    @staticmethod
    def _validate_id(value: str, name: str) -> str:
        if not isinstance(value, str) or not _ID_RE.fullmatch(value):
            raise ValueError(f"{name} must contain only letters, numbers, '_' or '-'")
        return value

    @staticmethod
    def _validate_email(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("self_email must be one valid email address")
        try:
            validated = validate_email(value, check_deliverability=False, allow_smtputf8=False)
        except EmailNotValidError:
            raise ValueError("self_email must be one valid email address") from None
        return validated.normalized

    @staticmethod
    def _raise_http_error(response: httpx.Response, *, operation: str) -> None:
        status = response.status_code
        reason: str | None = None
        try:
            error_payload = response.json()
            if isinstance(error_payload, dict):
                error = error_payload.get("error")
                if isinstance(error, dict) and isinstance(error.get("status"), str):
                    reason = error["status"]
        except ValueError:
            pass

        safe_message = "Google Workspace request failed"
        if status == 401:
            raise GoogleWorkspaceError(
                safe_message,
                operation=operation,
                status_code=status,
                unauthorized=True,
            )
        if status in (409, 412) or reason == "FAILED_PRECONDITION":
            raise GoogleWorkspaceConflictError(
                "Google document revision conflict",
                operation=operation,
                status_code=status,
                retryable=True,
            )
        raise GoogleWorkspaceError(
            safe_message,
            operation=operation,
            status_code=status,
            retryable=status in (408, 429) or status >= 500,
        )


__all__ = [
    "GoogleDocument",
    "GoogleWorkspaceConflictError",
    "GoogleWorkspaceError",
    "GoogleWorkspaceProtocolError",
    "GoogleWorkspaceTransport",
    "GoogleWorkspaceUnsupportedDocumentError",
]
