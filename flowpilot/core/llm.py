"""
FlowPilot LLM abstraction.

This module defines a provider-independent interface for answer
generation.

The knowledge pipeline produces a prompt.
An LLM provider consumes that prompt.

Architecture:

KnowledgePromptBuilder
        |
        v
      LLM
        |
        v
   Final Answer
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LLMRequest:
    """Request sent to an LLM provider."""

    prompt: str
    system_prompt: str = ""
    model: Optional[str] = None
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class LLMResponse:
    """Response returned by an LLM provider."""

    success: bool = False
    text: str = ""
    model: str = ""
    provider: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def summary(self) -> Dict[str, Any]:
        """Return a compact response summary."""

        return {
            "success": self.success,
            "provider": self.provider,
            "model": self.model,
            "text_length": len(self.text),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "error": self.error,
        }


class LLMError(RuntimeError):
    """Base exception for LLM-related failures."""


class LLMProvider(ABC):
    """
    Abstract interface implemented by LLM providers.

    Providers can implement this interface without changing
    the rest of FlowPilot.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""

        raise NotImplementedError

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the provider's default model."""

        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Generate an answer for an LLM request.
        """

        raise NotImplementedError

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Convenience wrapper around generate().
        """

        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata or {},
        )

        return self.generate(
            request
        )


class NullLLMProvider(LLMProvider):
    """
    Safe placeholder provider.

    This provider intentionally does not call a model.
    It is used when no real provider is configured.
    """

    @property
    def provider_name(self) -> str:
        return "null"

    @property
    def default_model(self) -> str:
        return "none"

    def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:

        if not request.prompt.strip():
            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=(
                    request.model
                    or self.default_model
                ),
                error="Prompt is empty.",
            )

        return LLMResponse(
            success=True,
            text="",
            provider=self.provider_name,
            model=(
                request.model
                or self.default_model
            ),
            metadata={
                "mode": "dry_run",
                "generated": False,
            },
        )


class LLMClient:
    """
    Provider-independent FlowPilot LLM client.

    The client delegates generation to the configured provider.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
    ) -> None:

        self.provider = (
            provider
            if provider is not None
            else NullLLMProvider()
        )

    @property
    def provider_name(self) -> str:
        return self.provider.provider_name

    @property
    def default_model(self) -> str:
        return self.provider.default_model

    def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:

        if request is None:
            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=self.default_model,
                error="LLM request is missing.",
            )

        if not request.prompt.strip():
            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=(
                    request.model
                    or self.default_model
                ),
                error="Prompt is empty.",
            )

        try:
            response = self.provider.generate(
                request
            )

        except Exception as exc:
            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=(
                    request.model
                    or self.default_model
                ),
                error=str(exc),
            )

        if response is None:
            return LLMResponse(
                success=False,
                provider=self.provider_name,
                model=(
                    request.model
                    or self.default_model
                ),
                error=(
                    "LLM provider returned "
                    "no response."
                ),
            )

        return response

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:

        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata or {},
        )

        return self.generate(
            request
        )


def create_default_llm_client() -> LLMClient:
    """
    Create the default FlowPilot LLM client.

    If a real OpenAI-compatible provider is configured
    through environment variables, use it.

    Otherwise, safely fall back to NullLLMProvider.

    Environment variables:

        FLOWPILOT_LLM_BASE_URL
        FLOWPILOT_LLM_MODEL
        FLOWPILOT_LLM_API_KEY
    """

    import os

    base_url = os.getenv(
        "FLOWPILOT_LLM_BASE_URL",
        "",
    ).strip()

    model = os.getenv(
        "FLOWPILOT_LLM_MODEL",
        "",
    ).strip()

    api_key = os.getenv(
        "FLOWPILOT_LLM_API_KEY",
        "",
    ).strip()

    if base_url and model:

        from flowpilot.core.providers.openai_compatible import (
            OpenAICompatibleProvider,
        )

        provider = OpenAICompatibleProvider(
            base_url=base_url,
            model=model,
            api_key=api_key or None,
        )

        return LLMClient(
            provider=provider
        )

    return LLMClient(
        provider=NullLLMProvider()
    )


__all__ = [
    "LLMRequest",
    "LLMResponse",
    "LLMError",
    "LLMProvider",
    "NullLLMProvider",
    "LLMClient",
    "create_default_llm_client",
]