from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from flowpilot.agent.inference import (
    InferenceProvider,
    InferenceRequest,
    InferenceResult,
)


@dataclass
class ProviderConfig:
    name: str
    model: str = ""
    enabled: bool = True
    settings: Optional[Dict[str, object]] = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "model": self.model,
            "enabled": self.enabled,
            "settings": dict(self.settings or {}),
        }


class ConfiguredProvider(InferenceProvider):
    """
    Generic provider adapter.

    This class defines the provider boundary without
    depending on any specific AI vendor.
    """

    def __init__(
        self,
        config: ProviderConfig,
    ) -> None:
        self.config = config
        self.name = config.name

    def generate(
        self,
        request: InferenceRequest,
    ) -> InferenceResult:

        if not self.config.enabled:
            return InferenceResult(
                success=False,
                provider=self.name,
                model=(
                    request.model
                    or self.config.model
                    or "none"
                ),
                error=(
                    f"Provider '{self.name}' "
                    "is disabled."
                ),
            )

        return InferenceResult(
            success=False,
            provider=self.name,
            model=(
                request.model
                or self.config.model
                or "none"
            ),
            error=(
                f"Provider '{self.name}' has no "
                "inference implementation yet."
            ),
        )


class ProviderRegistry:
    """
    Registry for FlowPilot inference providers.
    """

    def __init__(self) -> None:
        self._providers: Dict[
            str,
            InferenceProvider,
        ] = {}

        self._configs: Dict[
            str,
            ProviderConfig,
        ] = {}

    def register(
        self,
        provider: InferenceProvider,
        config: Optional[
            ProviderConfig
        ] = None,
    ) -> None:

        name = provider.name.strip()

        if not name:
            raise ValueError(
                "Provider name cannot be empty."
            )

        self._providers[name] = provider

        if config is not None:
            self._configs[name] = config

    def get(
        self,
        name: str,
    ) -> Optional[InferenceProvider]:

        return self._providers.get(name)

    def require(
        self,
        name: str,
    ) -> InferenceProvider:

        provider = self.get(name)

        if provider is None:
            raise KeyError(
                f"Provider '{name}' is not registered."
            )

        return provider

    def has(
        self,
        name: str,
    ) -> bool:

        return name in self._providers

    def names(self) -> list[str]:
        return sorted(
            self._providers.keys()
        )

    def configs(self) -> Dict[
        str,
        ProviderConfig,
    ]:

        return dict(self._configs)


def create_default_registry() -> ProviderRegistry:
    """
    Create the default FlowPilot provider registry.

    No external AI service is enabled here.
    """

    registry = ProviderRegistry()

    null_config = ProviderConfig(
        name="null",
        model="none",
        enabled=True,
    )

    null_provider = ConfiguredProvider(
        null_config
    )

    registry.register(
        null_provider,
        null_config,
    )

    return registry


__all__ = [
    "ProviderConfig",
    "ConfiguredProvider",
    "ProviderRegistry",
    "create_default_registry",
]