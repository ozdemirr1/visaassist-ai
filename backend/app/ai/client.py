"""One interface for reading a document with a model, whatever the provider (ADR 0007).

The rest of the system calls `ModelClient.read`; `OpenAIClient` implements it with the OpenAI
Responses API over plain HTTP. An open model on the project's own server can replace it later by
implementing the same method. Tests use a fake client, so they never call a provider.
"""

import base64
import json
import time
from dataclasses import dataclass
from typing import Protocol

import httpx


class ModelError(Exception):
    """The model could not be reached or gave no usable answer; the message is safe to show."""


@dataclass(frozen=True)
class ModelReply:
    data: dict
    model: str
    input_tokens: int
    output_tokens: int
    seconds: float


class ModelClient(Protocol):
    def read(
        self,
        *,
        instructions: str,
        prompt: str,
        content: bytes,
        mime_type: str,
        schema: dict,
        name: str,
    ) -> ModelReply: ...


class OpenAIClient:
    """Calls POST /v1/responses with the document as an image or PDF and a strict JSON schema."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 90.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    @staticmethod
    def _document_part(content: bytes, mime_type: str) -> dict:
        encoded = base64.b64encode(content).decode()
        if mime_type == "application/pdf":
            return {
                "type": "input_file",
                "filename": "document.pdf",
                "file_data": f"data:application/pdf;base64,{encoded}",
            }
        return {
            "type": "input_image",
            "image_url": f"data:{mime_type};base64,{encoded}",
            "detail": "auto",
        }

    def request_body(
        self,
        instructions: str,
        prompt: str,
        content: bytes,
        mime_type: str,
        schema: dict,
        name: str,
    ) -> dict:
        return {
            "model": self.model,
            "instructions": instructions,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        self._document_part(content, mime_type),
                    ],
                }
            ],
            "text": {
                "format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}
            },
            "store": False,
        }

    def read(
        self,
        *,
        instructions: str,
        prompt: str,
        content: bytes,
        mime_type: str,
        schema: dict,
        name: str,
    ) -> ModelReply:
        started = time.monotonic()
        try:
            response = self._http.post(
                "/responses",
                json=self.request_body(instructions, prompt, content, mime_type, schema, name),
            )
        except httpx.HTTPError as error:
            raise ModelError("The model could not be reached.") from error
        seconds = time.monotonic() - started
        if response.status_code != 200:
            raise ModelError(f"The model service answered {response.status_code}.")
        body = response.json()
        if body.get("status") != "completed":
            raise ModelError("The model did not finish its answer.")
        texts = [
            part.get("text", "")
            for item in body.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        ]
        if not texts:
            raise ModelError("The model declined to read the document.")
        try:
            data = json.loads(texts[0])
        except json.JSONDecodeError as error:
            raise ModelError("The model's answer was not valid JSON.") from error
        usage = body.get("usage") or {}
        return ModelReply(
            data=data,
            model=body.get("model", self.model),
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            seconds=seconds,
        )
