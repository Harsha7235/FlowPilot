from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE = ROOT / "flowpilot" / "knowledge"

BLOCKS = KNOWLEDGE / "blocks"
IMPLEMENTATIONS = KNOWLEDGE / "implementations"
GRAPH_FILE = KNOWLEDGE / "graph" / "knowledge_graph.json"

OUTPUT = ROOT / "flowpilot" / "training" / "dataset_v4"

RANDOM_SEED = 42


# ============================================================
# BASIC HELPERS
# ============================================================

def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        print(
            f"[WARN] Could not read {path}: {exc}"
        )
        return None


def stringify(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
    )


def clean_name(value: str) -> str:
    """
    Convert names such as:

    gnuradio-main__gr-analog__analog_agc_xx.json

    to:

    analog_agc_xx
    """

    name = Path(value).stem

    if name.endswith(".sources"):
        name = name[:-8]

    parts = name.split("__")

    if len(parts) >= 3:
        return parts[-1]

    return name


def friendly_node_name(
    node: dict[str, Any],
) -> str:

    for key in (
        "name",
        "block_id",
        "id",
    ):

        value = node.get(key)

        if not value:
            continue

        value = str(value)

        # Never put absolute Windows paths
        # into the user-facing training text.
        if "\\" in value:

            return Path(value).name

        return value

    return "unknown"


def make_example(
    instruction: str,
    context: str,
    response: str,
    source: str,
    kind: str,
) -> dict[str, Any]:

    instruction = instruction.strip()
    context = context.strip()
    response = response.strip()

    if not instruction:
        return {}

    if not response:
        return {}

    return {
        "instruction": instruction,
        "context": context,
        "response": response,
        "metadata": {
            "source": source,
            "type": kind,
        },
    }


# ============================================================
# BLOCK KNOWLEDGE
# ============================================================

def build_block_examples() -> list[dict]:

    examples = []

    files = sorted(
        BLOCKS.glob("*.json")
    )

    print(
        f"Block files: {len(files)}"
    )

    for path in files:

        data = load_json(path)

        if not isinstance(data, dict):
            continue

        block_name = (
            data.get("name")
            or data.get("block_id")
            or clean_name(path.name)
        )

        description = (
            data.get("description")
            or data.get("documentation")
            or data.get("summary")
        )

        parameters = data.get(
            "parameters"
        )

        inputs = data.get(
            "inputs"
        )

        outputs = data.get(
            "outputs"
        )

        context = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

        if description:

            examples.append(
                make_example(
                    instruction=(
                        f"What is the GNU Radio "
                        f"block {block_name}?"
                    ),
                    context=context,
                    response=stringify(
                        description
                    ),
                    source=path.name,
                    kind="block_description",
                )
            )

        if parameters:

            examples.append(
                make_example(
                    instruction=(
                        f"What parameters does "
                        f"{block_name} have?"
                    ),
                    context=context,
                    response=(
                        "The parameters defined "
                        "for this block are:\n"
                        + stringify(parameters)
                    ),
                    source=path.name,
                    kind="block_parameters",
                )
            )

        if inputs or outputs:

            examples.append(
                make_example(
                    instruction=(
                        f"Explain the input and "
                        f"output interfaces of "
                        f"{block_name}."
                    ),
                    context=context,
                    response=(
                        "Inputs:\n"
                        + stringify(inputs)
                        + "\n\nOutputs:\n"
                        + stringify(outputs)
                    ),
                    source=path.name,
                    kind="block_io",
                )
            )

    return [
        x for x in examples if x
    ]


# ============================================================
# IMPLEMENTATION KNOWLEDGE
# ============================================================

def extract_code(data: dict[str, Any]) -> str:

    possible_keys = (
        "source_code",
        "source",
        "code",
        "implementation",
        "cpp",
        "python",
        "body",
    )

    for key in possible_keys:

        value = data.get(key)

        if isinstance(value, str) and value.strip():

            return value.strip()

    return ""


def build_implementation_examples() -> list[dict]:

    examples = []

    files = sorted(
        IMPLEMENTATIONS.glob("*.json")
    )

    print(
        f"Implementation files: {len(files)}"
    )

    for path in files:

        data = load_json(path)

        if not isinstance(data, dict):
            continue

        name = (
            data.get("name")
            or data.get("block_id")
            or clean_name(path.name)
        )

        context = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

        code = extract_code(data)

        # -----------------------------------------
        # Implementation explanation
        # -----------------------------------------

        implementation = (
            data.get("implementation")
            or data.get("description")
            or data.get("documentation")
        )

        if implementation:

            examples.append(
                make_example(
                    instruction=(
                        f"How is {name} implemented?"
                    ),
                    context=context,
                    response=stringify(
                        implementation
                    ),
                    source=path.name,
                    kind="implementation",
                )
            )

        # -----------------------------------------
        # Actual source-code example
        # -----------------------------------------

        if code:

            examples.append(
                make_example(
                    instruction=(
                        f"Show and explain the "
                        f"implementation code for {name}."
                    ),
                    context=context,
                    response=code,
                    source=path.name,
                    kind="implementation_code",
                )
            )

            examples.append(
                make_example(
                    instruction=(
                        f"What can be learned from "
                        f"the source implementation of {name}?"
                    ),
                    context=context,
                    response=code,
                    source=path.name,
                    kind="implementation_source",
                )
            )

        # -----------------------------------------
        # General structured implementation data
        # -----------------------------------------

        if not implementation and not code:

            examples.append(
                make_example(
                    instruction=(
                        f"Explain the available "
                        f"implementation information "
                        f"for {name}."
                    ),
                    context=context,
                    response=context,
                    source=path.name,
                    kind="implementation_metadata",
                )
            )

    return [
        x for x in examples if x
    ]


# ============================================================
# GRAPH
# ============================================================

RELATIONSHIP_TEMPLATES = {

    "contains": (
        "What does {source} contain?",
        "{source} contains {target}.",
    ),

    "implemented_by": (
        "What implements {source}?",
        "{source} is implemented by {target}.",
    ),

    "has_function": (
        "What function is associated with {source}?",
        "{source} has the function {target}.",
    ),

    "has_parameter": (
        "What parameter is associated with {source}?",
        "{source} has the parameter {target}.",
    ),

    "references": (
        "What does {source} reference?",
        "{source} references {target}.",
    ),

    "part_of": (
        "What is {source} part of?",
        "{source} is part of {target}.",
    ),

    "defines": (
        "What does {source} define?",
        "{source} defines {target}.",
    ),

    "belongs_to": (
        "What does {source} belong to?",
        "{source} belongs to {target}.",
    ),
}


# Maximum number of graph examples
# for heavily populated relationship types.
RELATIONSHIP_LIMITS = {
    "has_parameter": 3500,
    "has_function": 2500,
    "references": 2500,
    "contains": 2500,
    "implemented_by": 2000,
    "part_of": 1000,
    "defines": 1000,
    "belongs_to": 1000,
}


def build_graph_examples() -> list[dict]:

    data = load_json(
        GRAPH_FILE
    )

    if not isinstance(data, dict):
        return []

    nodes = data.get(
        "nodes",
        []
    )

    edges = data.get(
        "edges",
        []
    )

    print(
        f"Graph nodes: {len(nodes)}"
    )

    print(
        f"Graph edges: {len(edges)}"
    )

    node_map = {}

    for node in nodes:

        if not isinstance(
            node,
            dict,
        ):
            continue

        node_id = node.get(
            "id"
        )

        if node_id:
            node_map[node_id] = node

    grouped = defaultdict(list)

    for edge in edges:

        if not isinstance(
            edge,
            dict,
        ):
            continue

        relationship = edge.get(
            "relationship"
        )

        if relationship:
            grouped[
                relationship
            ].append(edge)

    examples = []

    for relationship, relationship_edges in grouped.items():

        random.shuffle(
            relationship_edges
        )

        limit = RELATIONSHIP_LIMITS.get(
            relationship,
            500,
        )

        selected = relationship_edges[
            :limit
        ]

        print(
            f"  {relationship}: "
            f"{len(selected)} / "
            f"{len(relationship_edges)}"
        )

        for edge in selected:

            source_id = edge.get(
                "source"
            )

            target_id = edge.get(
                "target"
            )

            if not source_id or not target_id:
                continue

            source_node = node_map.get(
                source_id,
                {},
            )

            target_node = node_map.get(
                target_id,
                {},
            )

            source = friendly_node_name(
                source_node
            )

            target = friendly_node_name(
                target_node
            )

            if (
                source == "unknown"
                or target == "unknown"
            ):
                continue

            template = (
                RELATIONSHIP_TEMPLATES.get(
                    relationship
                )
            )

            if template:

                question = template[
                    0
                ].format(
                    source=source,
                    target=target,
                )

                answer = template[
                    1
                ].format(
                    source=source,
                    target=target,
                )

            else:

                question = (
                    f"How is {source} "
                    f"related to {target}?"
                )

                answer = (
                    f"{source} has a "
                    f"'{relationship}' "
                    f"relationship with "
                    f"{target}."
                )

            context = json.dumps(
                {
                    "source_node": source_node,
                    "relationship": relationship,
                    "target_node": target_node,
                    "edge": edge,
                },
                indent=2,
                ensure_ascii=False,
            )

            examples.append(
                make_example(
                    instruction=question,
                    context=context,
                    response=answer,
                    source=GRAPH_FILE.name,
                    kind=(
                        "graph_"
                        + str(relationship)
                    ),
                )
            )

    return [
        x for x in examples if x
    ]


# ============================================================
# CODING TASKS
# ============================================================

def build_coding_examples() -> list[dict]:

    examples = []

    files = sorted(
        IMPLEMENTATIONS.glob("*.json")
    )

    print(
        f"Coding-task source files: "
        f"{len(files)}"
    )

    for path in files:

        data = load_json(path)

        if not isinstance(data, dict):
            continue

        name = (
            data.get("name")
            or data.get("block_id")
            or clean_name(path.name)
        )

        code = extract_code(data)

        if not code:
            continue

        context = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

        # -----------------------------------------
        # Explain existing implementation
        # -----------------------------------------

        examples.append(
            make_example(
                instruction=(
                    f"Analyze the GNU Radio "
                    f"implementation of {name}."
                ),
                context=context,
                response=code,
                source=path.name,
                kind="coding_analysis",
            )
        )

        # -----------------------------------------
        # Modification task
        # -----------------------------------------

        examples.append(
            make_example(
                instruction=(
                    f"How would you modify the "
                    f"implementation of {name}? "
                    f"Use the existing source as "
                    f"the reference."
                ),
                context=context,
                response=(
                    "The existing implementation "
                    "to use as the reference is:\n\n"
                    + code
                ),
                source=path.name,
                kind="coding_modification",
            )
        )

        # -----------------------------------------
        # Testing task
        # -----------------------------------------

        examples.append(
            make_example(
                instruction=(
                    f"How should {name} be tested "
                    f"based on its implementation?"
                ),
                context=context,
                response=(
                    "The implementation that should "
                    "be covered by tests is:\n\n"
                    + code
                ),
                source=path.name,
                kind="coding_testing",
            )
        )

    return [
        x for x in examples if x
    ]


# ============================================================
# QUALITY
# ============================================================

def quality_filter(
    examples: list[dict],
) -> list[dict]:

    result = []

    for example in examples:

        instruction = example.get(
            "instruction",
            "",
        ).strip()

        response = example.get(
            "response",
            "",
        ).strip()

        context = example.get(
            "context",
            "",
        ).strip()

        if len(instruction) < 8:
            continue

        if len(response) < 3:
            continue

        if not context:
            continue

        # Avoid training on obvious empty placeholders.
        if response.lower() in {
            "none",
            "null",
            "unknown",
            "n/a",
        }:
            continue

        result.append(
            example
        )

    return result


def deduplicate(
    examples: list[dict],
) -> list[dict]:

    seen = set()
    result = []

    for example in examples:

        key = (
            example[
                "instruction"
            ].strip().lower(),

            example[
                "response"
            ].strip().lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        result.append(
            example
        )

    return result


# ============================================================
# BALANCING
# ============================================================

def balance_examples(
    examples: list[dict],
) -> list[dict]:

    groups = defaultdict(list)

    for example in examples:

        kind = example[
            "metadata"
        ][
            "type"
        ]

        groups[
            kind
        ].append(
            example
        )

    # Maximum counts per major category.
    limits = {
        "block_description": 1200,
        "block_parameters": 1200,
        "block_io": 1200,

        "implementation": 1200,
        "implementation_code": 1200,
        "implementation_source": 1200,
        "implementation_metadata": 800,

        "coding_analysis": 1000,
        "coding_modification": 800,
        "coding_testing": 800,

        "graph_contains": 1500,
        "graph_implemented_by": 1500,
        "graph_has_function": 1800,
        "graph_has_parameter": 2500,
        "graph_references": 1800,
        "graph_part_of": 800,
        "graph_defines": 800,
        "graph_belongs_to": 800,
    }

    balanced = []

    print()
    print(
        "BALANCING DATASET"
    )

    for kind, items in sorted(
        groups.items()
    ):

        random.shuffle(
            items
        )

        limit = limits.get(
            kind,
            1000,
        )

        selected = items[
            :limit
        ]

        balanced.extend(
            selected
        )

        print(
            f"{kind}: "
            f"{len(selected)} / "
            f"{len(items)}"
        )

    return balanced


# ============================================================
# WRITE
# ============================================================

def write_jsonl(
    path: Path,
    records: list[dict],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        for record in records:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    random.seed(
        RANDOM_SEED
    )

    print()
    print(
        "========================================"
    )
    print(
        "FLOWPILOT DATASET V4 BUILDER"
    )
    print(
        "========================================"
    )

    examples = []

    # -----------------------------------------
    # 1. Blocks
    # -----------------------------------------

    print()
    print(
        "[1/4] BLOCK KNOWLEDGE"
    )

    examples.extend(
        build_block_examples()
    )

    # -----------------------------------------
    # 2. Implementations
    # -----------------------------------------

    print()
    print(
        "[2/4] IMPLEMENTATION KNOWLEDGE"
    )

    examples.extend(
        build_implementation_examples()
    )

    # -----------------------------------------
    # 3. Graph
    # -----------------------------------------

    print()
    print(
        "[3/4] GRAPH KNOWLEDGE"
    )

    examples.extend(
        build_graph_examples()
    )

    # -----------------------------------------
    # 4. Coding
    # -----------------------------------------

    print()
    print(
        "[4/4] CODING TASKS"
    )

    examples.extend(
        build_coding_examples()
    )

    print()
    print(
        f"Raw examples: {len(examples)}"
    )

    examples = quality_filter(
        examples
    )

    print(
        f"After quality filter: "
        f"{len(examples)}"
    )

    examples = deduplicate(
        examples
    )

    print(
        f"After deduplication: "
        f"{len(examples)}"
    )

    examples = balance_examples(
        examples
    )

    print()
    print(
        f"After balancing: "
        f"{len(examples)}"
    )

    # -----------------------------------------
    # Final shuffle
    # -----------------------------------------

    random.shuffle(
        examples
    )

    total = len(
        examples
    )

    if total < 100:
        raise RuntimeError(
            "V4 dataset is unexpectedly small."
        )

    train_end = int(
        total * 0.80
    )

    validation_end = int(
        total * 0.90
    )

    train = examples[
        :train_end
    ]

    validation = examples[
        train_end:validation_end
    ]

    test = examples[
        validation_end:
    ]

    # -----------------------------------------
    # Write
    # -----------------------------------------

    write_jsonl(
        OUTPUT / "train.jsonl",
        train,
    )

    write_jsonl(
        OUTPUT / "validation.jsonl",
        validation,
    )

    write_jsonl(
        OUTPUT / "test.jsonl",
        test,
    )

    # -----------------------------------------
    # Statistics
    # -----------------------------------------

    type_counts = Counter(
        example[
            "metadata"
        ][
            "type"
        ]
        for example in examples
    )

    manifest = {
        "version": "v4",
        "seed": RANDOM_SEED,

        "total": total,

        "train": len(train),
        "validation": len(validation),
        "test": len(test),

        "source_counts": {
            "blocks": len(
                list(
                    BLOCKS.glob("*.json")
                )
            ),
            "implementations": len(
                list(
                    IMPLEMENTATIONS.glob(
                        "*.json"
                    )
                )
            ),
        },

        "graph": {
            "path": str(
                GRAPH_FILE
            ),
        },

        "example_types": dict(
            sorted(
                type_counts.items()
            )
        ),
    }

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        OUTPUT / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "========================================"
    )
    print(
        "FLOWPILOT DATASET V4 COMPLETE"
    )
    print(
        "========================================"
    )

    print(
        f"Total:      {total}"
    )

    print(
        f"Train:      {len(train)}"
    )

    print(
        f"Validation: {len(validation)}"
    )

    print(
        f"Test:       {len(test)}"
    )

    print()
    print(
        "Output:"
    )

    print(
        OUTPUT
    )

    print()
    print(
        "Manifest:"
    )

    print(
        OUTPUT / "manifest.json"
    )


if __name__ == "__main__":
    main()