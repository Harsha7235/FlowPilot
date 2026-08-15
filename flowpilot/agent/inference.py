from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class InferenceRequest:
    prompt: str
    system_prompt: str = ""
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 8192
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def summary(self) -> dict:
        return {
            "prompt_length": len(self.prompt),
            "system_prompt_length": len(
                self.system_prompt
            ),
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "metadata": dict(self.metadata),
        }


@dataclass
class InferenceResult:
    success: bool
    text: str = ""
    provider: str = ""
    model: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def summary(self) -> dict:
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


class InferenceProvider:
    """
    Base interface for every FlowPilot inference provider.
    """

    name = "base"

    def generate(
        self,
        request: InferenceRequest,
    ) -> InferenceResult:

        raise NotImplementedError(
            "Inference providers must implement "
            "generate()."
        )


class NullInferenceProvider(
    InferenceProvider
):
    """
    Safe provider used when no real inference backend
    has been configured.
    """

    name = "null"

    def generate(
        self,
        request: InferenceRequest,
    ) -> InferenceResult:

        return InferenceResult(
            success=False,
            provider=self.name,
            model=request.model or "none",
            error=(
                "No inference provider is configured."
            ),
        )


class InferenceEngine:
    """
    Provider-independent inference engine.

    A provider can be supplied directly, or selected
    from a ProviderRegistry.

    When no provider or registry is supplied, FlowPilot
    uses the LLMInferenceProvider adapter, which connects
    the agent inference layer to the provider-independent
    LLMClient.
    """

    def __init__(
        self,
        provider: Optional[
            InferenceProvider
        ] = None,
        model: str = "",
        registry: Optional[Any] = None,
        provider_name: Optional[str] = None,
    ) -> None:

        self.model = model
        self.registry = registry

        if provider is not None:

            self.provider = provider

        elif (
            registry is not None
            and provider_name is not None
        ):

            self.provider = registry.require(
                provider_name
            )

        else:

            from flowpilot.agent.llm_inference_provider import (
                LLMInferenceProvider,
            )

            self.provider = (
                LLMInferenceProvider()
            )

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> InferenceResult:

        prompt = prompt.strip()

        if not prompt:

            return InferenceResult(
                success=False,
                provider=self.provider.name,
                model=(
                    model
                    or self.model
                    or "none"
                ),
                error="Prompt is empty.",
            )

        request = InferenceRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=(
                model
                or self.model
                or ""
            ),
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata or {},
        )

        try:

            return self.provider.generate(
                request
            )

        except Exception as exc:

            return InferenceResult(
                success=False,
                provider=self.provider.name,
                model=(
                    request.model
                    or "none"
                ),
                error=str(exc),
            )

    def provider_name(self) -> str:
        return self.provider.name

    def set_provider(
        self,
        provider: InferenceProvider,
    ) -> None:

        if provider is None:
            raise ValueError(
                "Provider cannot be None."
            )

        self.provider = provider

    def set_provider_from_registry(
        self,
        registry: Any,
        provider_name: str,
    ) -> None:

        self.provider = registry.require(
            provider_name
        )

        self.registry = registry


__all__ = [
    "InferenceRequest",
    "InferenceResult",
    "InferenceProvider",
    "NullInferenceProvider",
    "InferenceEngine",
]