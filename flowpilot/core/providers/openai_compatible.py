from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from flowpilot.core.llm import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
)


@dataclass
class OpenAICompatibleProvider(LLMProvider):
    """
    Generic provider for an OpenAI-compatible HTTP API.

    FlowPilot does not depend on a particular model vendor.
    The endpoint and model are configuration values.
    """

    base_url: str
    model: str
    api_key: Optional[str] = None
    timeout: int = 120

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def default_model(self) -> str:
        return self.model

    def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:

        model = request.model or self.default_model

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

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        body = json.dumps(payload).encode("utf-8")

        endpoint = (
            self.base_url.rstrip("/")
            + "/chat/completions"
        )

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        http_request = urllib_request.Request(
            endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib_request.urlopen(
                http_request,
                timeout=self.timeout,
            ) as response:

                raw = response.read().decode(
                    "utf-8"
                )

            data = json.loads(raw)

            choices = data.get(
                "choices",
                [],
            )

            if not choices:
                return LLMResponse(
                    success=False,
                    provider=self.provider_name,
                    model=model,
                    error=(
                        "Provider returned no choices."
                    ),
                    metadata=data,
                )

            message = choices[0].get(
                "message",
                {},
            )

            text = message.get(
                "content",
                "",
            )

            usage = data.get(
                "usage",
                {},
            )

            return LLMResponse(
                success=True,
                text=text or "",
                provider=self.provider_name,
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
                    "endpoint": endpoint,
                },
            )

        except HTTPError as exc:

            try:
                error_body = (
                    exc.read()
                    .decode("utf-8")
                )
            except Exception:
                error_body = ""

            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=model,
                error=(
                    f"HTTP {exc.code}: "
                    f"{error_body or exc.reason}"
                ),
            )

        except URLError as exc:

            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=model,
                error=(
                    f"Connection failed: {exc.reason}"
                ),
            )

        except TimeoutError:

            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=model,
                error="Provider request timed out.",
            )

        except json.JSONDecodeError:

            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=model,
                error=(
                    "Provider returned invalid JSON."
                ),
            )

        except Exception as exc:

            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=model,
                error=str(exc),
            )