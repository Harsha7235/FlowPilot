"""
FlowPilot Tool Registry
-----------------------

A deterministic Python tool-calling system.

This module does not use:
- Large language models
- Machine learning
- Cloud APIs
- Ollama

Only explicitly registered Python functions can be called.
"""

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any]
    ) -> None:

        if not name or not name.replace("_", "").isalnum():
            raise ValueError("Invalid tool name.")

        if name in self._tools:
            raise ValueError(
                f"Tool '{name}' is already registered."
            )

        if not callable(handler):
            raise TypeError("Tool handler must be callable.")

        self._tools[name] = Tool(
            name=name,
            description=description,
            handler=handler
        )

    def unregister(self, name: str) -> None:

        if name not in self._tools:
            raise ValueError(
                f"Tool '{name}' is not registered."
            )

        del self._tools[name]

    def exists(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def descriptions(self) -> list[str]:

        return [
            f"{tool.name}: {tool.description}"
            for tool in self._tools.values()
        ]

    def get_tool(self, name: str) -> Tool:

        if name not in self._tools:
            available = ", ".join(self.names())

            raise ValueError(
                f"Unknown tool: {name}\n"
                f"Available tools: {available}"
            )

        return self._tools[name]

    def call(
        self,
        name: str,
        **kwargs
    ) -> Any:

        tool = self.get_tool(name)

        return tool.handler(**kwargs)

    def call_safely(
        self,
        name: str,
        **kwargs
    ) -> dict:

        try:

            result = self.call(
                name,
                **kwargs
            )

            return {
                "success": True,
                "tool": name,
                "result": result,
                "error": None
            }

        except Exception as exc:

            return {
                "success": False,
                "tool": name,
                "result": None,
                "error": str(exc)
            }