from __future__ import annotations

from typing import Any

from flowpilot.agent.inference import (
    InferenceProvider,
    InferenceRequest,
    InferenceResult,
)

from flowpilot.core.llm import (
    LLMClient,
    LLMRequest,
    create_default_llm_client,
)


class LLMInferenceProvider(InferenceProvider):
    """
    Adapter between FlowPilot's agent inference interface
    and the provider-independent LLMClient.
    """

    name = "flowpilot_llm"

    def __init__(
        self,
        client: LLMClient | None = None,
    ) -> None:

        self.client = (
            client
            or create_default_llm_client()
        )

    def generate(
        self,
        request: InferenceRequest,
    ) -> InferenceResult:

        llm_request = LLMRequest(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            model=request.model or None,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            metadata=request.metadata,
        )

        response = self.client.generate(
            llm_request
        )

        return InferenceResult(
            success=response.success,
            text=response.text,
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            error=response.error,
            metadata=response.metadata,
        )