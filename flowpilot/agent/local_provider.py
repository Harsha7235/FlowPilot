from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flowpilot.agent.inference import (
    InferenceProvider,
    InferenceRequest,
    InferenceResult,
)


@dataclass
class LocalProviderConfig:
    name: str = "local"
    endpoint: str = ""
    model: str = ""
    api_key: str = ""
    timeout: int = 120

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "model": self.model,
            "api_key": "***" if self.api_key else "",
            "timeout": self.timeout,
        }


class LocalHTTPProvider(InferenceProvider):
    """
    Generic HTTP inference provider.

    Uses an OpenAI-compatible chat-completion
    request format without depending on a specific
    vendor.
    """

    def __init__(
        self,
        config: Optional[LocalProviderConfig] = None,
    ) -> None:

        self.config = (
            config
            or LocalProviderConfig()
        )

        self.name = self.config.name

    def generate(
        self,
        request: InferenceRequest,
    ) -> InferenceResult:

        model = (
            request.model
            or self.config.model
        )

        if not self.config.endpoint:

            return InferenceResult(
                success=False,
                provider=self.name,
                model=model or "none",
                error=(
                    "Local provider endpoint "
                    "is not configured."
                ),
            )

        if not model:

            return InferenceResult(
                success=False,
                provider=self.name,
                model="none",
                error=(
                    "Local provider model "
                    "is not configured."
                ),
            )

        payload = {
            "model": model,
            "messages": self._build_messages(
                request
            ),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        body = json.dumps(
            payload
        ).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:

            headers["Authorization"] = (
                f"Bearer {self.config.api_key}"
            )

        http_request = Request(
            self.config.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:

            with urlopen(
                http_request,
                timeout=self.config.timeout,
            ) as response:

                raw = response.read()

            data = json.loads(
                raw.decode("utf-8")
            )

            return self._parse_response(
                data,
                model,
            )

        except HTTPError as exc:

            return InferenceResult(
                success=False,
                provider=self.name,
                model=model,
                error=(
                    f"HTTP {exc.code}: "
                    f"{exc.reason}"
                ),
            )

        except URLError as exc:

            return InferenceResult(
                success=False,
                provider=self.name,
                model=model,
                error=(
                    "Unable to connect to local "
                    f"inference server: {exc.reason}"
                ),
            )

        except TimeoutError:

            return InferenceResult(
                success=False,
                provider=self.name,
                model=model,
                error=(
                    "Local inference request timed out."
                ),
            )

        except json.JSONDecodeError:

            return InferenceResult(
                success=False,
                provider=self.name,
                model=model,
                error=(
                    "Inference server returned "
                    "invalid JSON."
                ),
            )

        except Exception as exc:

            return InferenceResult(
                success=False,
                provider=self.name,
                model=model,
                error=str(exc),
            )

    @staticmethod
    def _build_messages(
        request: InferenceRequest,
    ) -> list:

        messages = []

        if request.system_prompt.strip():

            messages.append(
                {
                    "role": "system",
                    "content": request.system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": request.prompt,
            }
        )

        return messages

    def _parse_response(
        self,
        data: Dict[str, Any],
        model: str,
    ) -> InferenceResult:

        choices = data.get("choices")

        if not isinstance(
            choices,
            list,
        ) or not choices:

            return InferenceResult(
                success=False,
                provider=self.name,
                model=model,
                error=(
                    "Inference response did not "
                    "contain any choices."
                ),
            )

        first = choices[0]

        if not isinstance(
            first,
            dict,
        ):

            return InferenceResult(
                success=False,
                provider=self.name,
                model=model,
                error=(
                    "Invalid inference choice."
                ),
            )

        message = first.get(
            "message",
            {},
        )

        if not isinstance(
            message,
            dict,
        ):

            message = {}

        text = message.get(
            "content",
            "",
        )

        if text is None:
            text = ""

        usage = data.get(
            "usage",
            {},
        )

        if not isinstance(
            usage,
            dict,
        ):

            usage = {}

        return InferenceResult(
            success=True,
            text=str(text),
            provider=self.name,
            model=data.get(
                "model",
                model,
            ),
            prompt_tokens=usage.get(
                "prompt_tokens"
            ),
            completion_tokens=usage.get(
                "completion_tokens"
            ),
            total_tokens=usage.get(
                "total_tokens"
            ),
            metadata={
                "finish_reason": first.get(
                    "finish_reason"
                ),
            },
        )


__all__ = [
    "LocalProviderConfig",
    "LocalHTTPProvider",
]