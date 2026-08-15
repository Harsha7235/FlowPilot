from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDefinition:
    name: str
    description: str
    function: Callable[..., Any]

    def summary(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
        }


class ToolRegistry:
    """
    Central registry for tools available to the FlowPilot agent.

    The registry allows the agent layer to discover tools by name
    and execute them through a common interface.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        function: Callable[..., Any],
    ) -> ToolDefinition:
        """
        Register a tool.

        Raises:
            ValueError: if the tool name is empty or already registered.
        """

        if not name or not name.strip():
            raise ValueError("Tool name cannot be empty.")

        name = name.strip()

        if name in self._tools:
            raise ValueError(
                f"Tool already registered: {name}"
            )

        definition = ToolDefinition(
            name=name,
            description=description.strip(),
            function=function,
        )

        self._tools[name] = definition

        return definition

    def unregister(self, name: str) -> bool:
        """
        Remove a tool from the registry.

        Returns:
            True if the tool existed and was removed.
        """

        if name in self._tools:
            del self._tools[name]
            return True

        return False

    def has(self, name: str) -> bool:
        """Return True if a tool is registered."""

        return name in self._tools

    def get(self, name: str) -> ToolDefinition:
        """
        Get a registered tool.

        Raises:
            KeyError: if the tool does not exist.
        """

        if name not in self._tools:
            raise KeyError(
                f"Tool not found: {name}"
            )

        return self._tools[name]

    def call(
        self,
        name: str,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a registered tool.
        """

        tool = self.get(name)

        return tool.function(**kwargs)

    def list_tools(self) -> List[ToolDefinition]:
        """Return all registered tools."""

        return list(self._tools.values())

    def tool_names(self) -> List[str]:
        """Return registered tool names."""

        return list(self._tools.keys())

    def describe(self) -> List[dict]:
        """Return serializable tool descriptions."""

        return [
            tool.summary()
            for tool in self._tools.values()
        ]

    def clear(self) -> None:
        """Remove all registered tools."""

        self._tools.clear()

    def __len__(self) -> int:
        return len(self._tools)


def create_default_registry(
    filesystem_tool: Optional[Callable[..., Any]] = None,
    code_search_tool: Optional[Callable[..., Any]] = None,
    command_runner_tool: Optional[Callable[..., Any]] = None,
    git_tool: Optional[Callable[..., Any]] = None,
) -> ToolRegistry:
    """
    Create a registry and optionally register FlowPilot tools.

    Tool functions are passed in explicitly so the registry remains
    independent from the implementation of individual tools.
    """

    registry = ToolRegistry()

    if filesystem_tool is not None:
        registry.register(
            name="filesystem",
            description=(
                "Read, create, modify, and inspect files "
                "inside the FlowPilot workspace."
            ),
            function=filesystem_tool,
        )

    if code_search_tool is not None:
        registry.register(
            name="code_search",
            description=(
                "Search source code and return matching "
                "files, lines, and text."
            ),
            function=code_search_tool,
        )

    if command_runner_tool is not None:
        registry.register(
            name="command_runner",
            description=(
                "Execute approved commands inside the "
                "FlowPilot workspace."
            ),
            function=command_runner_tool,
        )

    if git_tool is not None:
        registry.register(
            name="git",
            description=(
                "Inspect Git status, diffs, branches, "
                "history, and changed files."
            ),
            function=git_tool,
        )

    return registry


__all__ = [
    "ToolDefinition",
    "ToolRegistry",
    "create_default_registry",
]