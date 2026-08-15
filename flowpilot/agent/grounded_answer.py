from __future__ import annotations

import re


def generate_grounded_answer(
    query: str,
    context_text: str,
) -> str:

    query = query.strip()
    context_text = context_text or ""

    if not context_text.strip():
        return "FlowPilot could not find usable knowledge for this question."

    def get_value(label: str) -> str:
        match = re.search(
            rf"^{re.escape(label)}\s*:\s*(.+)$",
            context_text,
            re.MULTILINE,
        )
        return match.group(1).strip() if match else ""

    block_id = get_value("Block ID")
    block_found = get_value("Block Found")

    block_name = (
        block_id.split("/")[-1]
        if block_id
        else "requested component"
    )

    query_lower = query.lower()

    # ==================================================
    # PARAMETERS
    # ==================================================

    if "parameter" in query_lower:

        match = re.search(
            r"Parameters\s*:?\s*(\d+)",
            context_text,
            re.IGNORECASE,
        )

        raw_count = int(match.group(1)) if match else 0

        section = _extract_section(
            context_text,
            "## PARAMETERS",
        )

        parameters = []

        for line in section.splitlines():

            line = line.strip()

            line = re.sub(
                r"^\d+\.\s*",
                "",
                line,
            )

            if not line:
                continue

            if line not in parameters:
                parameters.append(line)

        answer = [
            f"`{block_name}` has {raw_count} parameter entries "
            f"in the retrieved knowledge."
        ]

        if parameters:

            answer.append(
                "\nUnique parameter definitions found:"
            )

            for parameter in parameters:
                answer.append(
                    f"- `{parameter}`"
                )

        return "\n".join(answer)

    # ==================================================
    # METHODS
    # ==================================================

    if "method" in query_lower:

        match = re.search(
            r"Methods\s*:?\s*(\d+)",
            context_text,
            re.IGNORECASE,
        )

        count = match.group(1) if match else "unknown"

        section = _extract_section(
            context_text,
            "## METHODS",
        )

        methods = []

        for line in section.splitlines():

            line = line.strip()

            line = re.sub(
                r"^\d+\.\s*",
                "",
                line,
            )

            if line and line not in methods:
                methods.append(line)

        answer = [
            f"`{block_name}` has {count} method entries "
            f"in the retrieved knowledge."
        ]

        if methods:

            answer.append(
                "\nUnique methods:"
            )

            for method in methods:
                answer.append(
                    f"- `{method}`"
                )

        return "\n".join(answer)

    # ==================================================
    # SOURCE FILES
    # ==================================================

    if "source" in query_lower or "file" in query_lower:

        match = re.search(
            r"Source files\s*:?\s*(\d+)",
            context_text,
            re.IGNORECASE,
        )

        count = match.group(1) if match else "unknown"

        section = _extract_section(
            context_text,
            "## SOURCE FILES",
        )

        return (
            f"`{block_name}` has {count} relevant source files "
            "in the retrieved knowledge.\n\n"
            + section
        )

    # ==================================================
    # GENERAL
    # ==================================================

    return (
        f"FlowPilot found `{block_name}` in the GNU Radio "
        "knowledge graph.\n\n"
        f"Block found: {block_found}\n"
        f"Block ID: `{block_id}`\n\n"
        "The response is grounded in the indexed GNU Radio "
        "source context."
    )


def _extract_section(
    text: str,
    heading: str,
) -> str:

    pattern = (
        rf"{re.escape(heading)}\s*\n"
        rf"(.*?)(?=\n## |\Z)"
    )

    match = re.search(
        pattern,
        text,
        re.DOTALL,
    )

    if not match:
        return ""

    return match.group(1).strip()


__all__ = [
    "generate_grounded_answer",
]