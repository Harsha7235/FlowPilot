from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

SOURCE_ROOT = (
    ROOT
    / "third_party"
    / "gnuradio-main"
    / "gnuradio-main"
)

OUTPUT = (
    ROOT
    / "flowpilot"
    / "training"
    / "source_code_dataset_v2"
)

RANDOM_SEED = 42

SOURCE_EXTENSIONS = {
    ".cc",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".py",
}

SKIP_PARTS = {
    ".git",
    "build",
    "_build",
    "__pycache__",
    "generated",
    "doxygen",
}

MAX_FILE_CONTEXT = 10000
MAX_ENTITY_CONTEXT = 8000
MAX_ENTITY_RESPONSE = 6000


# ============================================================
# HELPERS
# ============================================================

def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return ""


def relative_path(path: Path) -> str:
    try:
        return str(
            path.relative_to(ROOT)
        ).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def truncate(
    text: str,
    limit: int,
) -> str:
    text = text.strip()

    if len(text) <= limit:
        return text

    return (
        text[:limit]
        + "\n\n[TRUNCATED]"
    )


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

    if not context:
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
# FILE DISCOVERY
# ============================================================

def discover_files() -> list[Path]:

    files = []

    for path in SOURCE_ROOT.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue

        if any(
            part in SKIP_PARTS
            for part in path.parts
        ):
            continue

        files.append(path)

    return sorted(files)


# ============================================================
# C++ PARSING
# ============================================================

CPP_CONTROL_WORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "sizeof",
    "decltype",
}


def looks_like_cpp_function(
    name: str,
) -> bool:

    if not name:
        return False

    if name in CPP_CONTROL_WORDS:
        return False

    if name.isupper():
        # Reject macros such as SOAPY_API.
        return False

    if name.startswith("__"):
        return False

    if not re.search(
        r"[A-Za-z_]",
        name,
    ):
        return False

    return True


def find_matching_brace(
    source: str,
    opening: int,
) -> int | None:

    depth = 0

    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False

    escape = False

    i = opening

    while i < len(source):

        ch = source[i]

        nxt = (
            source[i + 1]
            if i + 1 < len(source)
            else ""
        )

        if in_line_comment:

            if ch == "\n":
                in_line_comment = False

            i += 1
            continue

        if in_block_comment:

            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue

            i += 1
            continue

        if in_string:

            if escape:
                escape = False

            elif ch == "\\":
                escape = True

            elif ch == '"':
                in_string = False

            i += 1
            continue

        if in_char:

            if escape:
                escape = False

            elif ch == "\\":
                escape = True

            elif ch == "'":
                in_char = False

            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch == '"':
            in_string = True
            i += 1
            continue

        if ch == "'":
            in_char = True
            i += 1
            continue

        if ch == "{":
            depth += 1

        elif ch == "}":

            depth -= 1

            if depth == 0:
                return i

        i += 1

    return None


def extract_cpp_functions(
    source: str,
) -> list[dict[str, Any]]:

    entities = []

    pattern = re.compile(
        r"""
        (?P<name>
            [A-Za-z_~]\w*
            (?:
                ::
                [A-Za-z_~]\w*
            )*
        )
        \s*
        \(
            (?P<params>
                [^(){};]* 
            )
        \)
        \s*
        (?:
            const
            \s*
        )?
        (?:
            noexcept
            \s*
        )?
        \{
        """,
        re.VERBOSE,
    )

    for match in pattern.finditer(
        source
    ):

        name = match.group(
            "name"
        )

        if not looks_like_cpp_function(
            name
        ):
            continue

        opening = source.find(
            "{",
            match.start(),
            match.end(),
        )

        if opening < 0:
            continue

        closing = find_matching_brace(
            source,
            opening,
        )

        if closing is None:
            continue

        body = source[
            match.start():closing + 1
        ]

        if len(body) < 15:
            continue

        # Avoid accidentally treating ordinary
        # macro/function-like expressions as definitions.
        line_start = source.rfind(
            "\n",
            0,
            match.start(),
        ) + 1

        prefix = source[
            line_start:match.start()
        ].strip()

        if prefix.startswith("#"):
            continue

        entities.append(
            {
                "type": "function",
                "name": name,
                "parameters": (
                    match.group("params")
                    .strip()
                ),
                "start": match.start(),
                "end": closing + 1,
                "code": body,
            }
        )

    return entities


def extract_cpp_classes(
    source: str,
) -> list[dict[str, Any]]:

    entities = []

    pattern = re.compile(
        r"""
        \b
        (class|struct)
        \s+
        ([A-Za-z_]\w*)
        (?:\s*:\s*[^{]+)?
        \s*
        \{
        """,
        re.VERBOSE,
    )

    for match in pattern.finditer(
        source
    ):

        name = match.group(
            2
        )

        # Reject obvious macros / generated garbage.
        if name.isupper():
            continue

        opening = source.find(
            "{",
            match.start(),
            match.end(),
        )

        if opening < 0:
            continue

        closing = find_matching_brace(
            source,
            opening,
        )

        if closing is None:
            continue

        code = source[
            match.start():closing + 1
        ]

        if len(code) < 30:
            continue

        entities.append(
            {
                "type": match.group(1),
                "name": name,
                "start": match.start(),
                "end": closing + 1,
                "code": code,
            }
        )

    return entities


# ============================================================
# PYTHON PARSING
# ============================================================

def extract_python_entities(
    source: str,
) -> list[dict[str, Any]]:

    entities = []

    lines = source.splitlines(
        keepends=True
    )

    offsets = []

    current = 0

    for line in lines:
        offsets.append(current)
        current += len(line)

    class_pattern = re.compile(
        r"^(\s*)class\s+([A-Za-z_]\w*)",
        re.MULTILINE,
    )

    function_pattern = re.compile(
        r"^(\s*)(?:async\s+)?def\s+([A-Za-z_]\w*)",
        re.MULTILINE,
    )

    matches = []

    for match in class_pattern.finditer(
        source
    ):

        matches.append(
            (
                match.start(),
                "class",
                match.group(2),
                len(match.group(1)),
            )
        )

    for match in function_pattern.finditer(
        source
    ):

        matches.append(
            (
                match.start(),
                "function",
                match.group(2),
                len(match.group(1)),
            )
        )

    matches.sort(
        key=lambda x: x[0]
    )

    for index, item in enumerate(
        matches
    ):

        start = item[0]
        entity_type = item[1]
        name = item[2]
        indent = item[3]

        end = (
            matches[index + 1][0]
            if index + 1 < len(matches)
            else len(source)
        )

        code = source[
            start:end
        ].strip()

        if len(code) < 15:
            continue

        entities.append(
            {
                "type": entity_type,
                "name": name,
                "start": start,
                "end": end,
                "code": code,
                "indent": indent,
            }
        )

    return entities


# ============================================================
# ENTITY EXTRACTION
# ============================================================

def extract_entities(
    path: Path,
    source: str,
) -> list[dict[str, Any]]:

    if path.suffix.lower() == ".py":

        return extract_python_entities(
            source
        )

    return (
        extract_cpp_classes(source)
        + extract_cpp_functions(source)
    )


# ============================================================
# FILE-LEVEL EXAMPLES
# ============================================================

def build_file_examples(
    path: Path,
    source: str,
) -> list[dict]:

    rel = relative_path(
        path
    )

    context = truncate(
        source,
        MAX_FILE_CONTEXT,
    )

    language = (
        "Python"
        if path.suffix.lower() == ".py"
        else "C/C++"
    )

    examples = []

    examples.append(
        make_example(
            instruction=(
                f"Analyze this GNU Radio "
                f"{language} source file."
            ),
            context=context,
            response=(
                "Analyze the supplied source directly. "
                "Identify its purpose, important "
                "definitions, classes, functions, "
                "interfaces, and implementation "
                "behavior that can be established "
                "from the code."
            ),
            source=rel,
            kind="source_file_analysis",
        )
    )

    return [
        x for x in examples if x
    ]


# ============================================================
# FUNCTION EXAMPLES
# ============================================================

def build_function_examples(
    path: Path,
    source: str,
    entities: list[dict[str, Any]],
) -> list[dict]:

    examples = []

    rel = relative_path(
        path
    )

    functions = [
        e
        for e in entities
        if e["type"] == "function"
    ]

    # Avoid enormous numbers from utility files.
    functions = functions[:100]

    for entity in functions:

        name = entity["name"]
        params = entity.get(
            "parameters",
            "",
        )

        code = entity["code"]

        if not code:
            continue

        # The response is actual extracted code,
        # not a fabricated explanation.
        examples.append(
            make_example(
                instruction=(
                    f"What is the implementation "
                    f"of {name}?"
                ),
                context=truncate(
                    code,
                    MAX_ENTITY_CONTEXT,
                ),
                response=truncate(
                    code,
                    MAX_ENTITY_RESPONSE,
                ),
                source=rel,
                kind="function_implementation",
            )
        )

        if params:

            examples.append(
                make_example(
                    instruction=(
                        f"What parameters does "
                        f"{name} accept?"
                    ),
                    context=truncate(
                        code,
                        MAX_ENTITY_CONTEXT,
                    ),
                    response=(
                        f"{name} accepts: "
                        f"{params}"
                    ),
                    source=rel,
                    kind="function_parameters",
                )
            )

        examples.append(
            make_example(
                instruction=(
                    f"Which GNU Radio function "
                    f"is implemented by this code?"
                ),
                context=truncate(
                    code,
                    MAX_ENTITY_CONTEXT,
                ),
                response=name,
                source=rel,
                kind="function_identification",
            )
        )

    return examples


# ============================================================
# CLASS EXAMPLES
# ============================================================

def build_class_examples(
    path: Path,
    entities: list[dict[str, Any]],
) -> list[dict]:

    examples = []

    rel = relative_path(
        path
    )

    classes = [
        e
        for e in entities
        if e["type"] in {
            "class",
            "struct",
        }
    ]

    classes = classes[:50]

    for entity in classes:

        name = entity["name"]
        code = entity["code"]

        if not code:
            continue

        examples.append(
            make_example(
                instruction=(
                    f"What class or struct is "
                    f"defined by this GNU Radio code?"
                ),
                context=truncate(
                    code,
                    MAX_ENTITY_CONTEXT,
                ),
                response=name,
                source=rel,
                kind="class_identification",
            )
        )

        examples.append(
            make_example(
                instruction=(
                    f"Show the implementation "
                    f"of {name}."
                ),
                context=truncate(
                    code,
                    MAX_ENTITY_CONTEXT,
                ),
                response=truncate(
                    code,
                    MAX_ENTITY_RESPONSE,
                ),
                source=rel,
                kind="class_implementation",
            )
        )

    return examples


# ============================================================
# BLOCK-IMPLEMENTATION DETECTION
# ============================================================

def is_probable_gnuradio_block_file(
    path: Path,
) -> bool:

    text = str(path).replace(
        "\\",
        "/",
    )

    block_modules = (
        "/gr-analog/",
        "/gr-blocks/",
        "/gr-digital/",
        "/gr-filter/",
        "/gr-fft/",
        "/gr-fec/",
        "/gr-qtgui/",
        "/gr-channels/",
        "/gr-vocoder/",
        "/gr-dtv/",
        "/gr-uhd/",
        "/gr-soapy/",
        "/gr-trellis/",
        "/gr-wavelet/",
        "/gr-video-sdl/",
    )

    if not any(
        x in text
        for x in block_modules
    ):
        return False

    return (
        "/lib/" in text
        or "/include/" in text
        or "/python/" in text
    )


def build_block_code_examples(
    path: Path,
    source: str,
    entities: list[dict[str, Any]],
) -> list[dict]:

    if not is_probable_gnuradio_block_file(
        path
    ):
        return []

    rel = relative_path(
        path
    )

    examples = []

    functions = [
        e
        for e in entities
        if e["type"] == "function"
    ]

    for entity in functions[:30]:

        name = entity["name"]
        code = entity["code"]

        # GNU Radio implementation names often
        # contain _impl.
        if (
            "_impl" not in name
            and "::make" not in name
        ):
            continue

        examples.append(
            make_example(
                instruction=(
                    f"How is the GNU Radio "
                    f"implementation {name} "
                    f"implemented?"
                ),
                context=truncate(
                    code,
                    MAX_ENTITY_CONTEXT,
                ),
                response=truncate(
                    code,
                    MAX_ENTITY_RESPONSE,
                ),
                source=rel,
                kind="gnuradio_block_implementation",
            )
        )

    return examples


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

        context = example.get(
            "context",
            "",
        ).strip()

        response = example.get(
            "response",
            "",
        ).strip()

        if len(instruction) < 10:
            continue

        if len(context) < 20:
            continue

        if len(response) < 2:
            continue

        # Reject obvious parser artifacts.
        if response in {
            "defined",
            "if",
            "for",
            "while",
            "switch",
            "SOAPY_API",
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
            example["instruction"]
            .strip()
            .lower(),

            example["response"]
            .strip()
            .lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        result.append(
            example
        )

    return result


# ============================================================
# BALANCE
# ============================================================

TYPE_LIMITS = {
    "source_file_analysis": 1500,

    "function_implementation": 12000,
    "function_parameters": 6000,
    "function_identification": 6000,

    "class_identification": 2500,
    "class_implementation": 2500,

    "gnuradio_block_implementation": 4000,
}


def balance(
    examples: list[dict],
) -> list[dict]:

    grouped = {}

    for example in examples:

        kind = example[
            "metadata"
        ][
            "type"
        ]

        grouped.setdefault(
            kind,
            [],
        ).append(
            example
        )

    result = []

    print()
    print(
        "SOURCE DATASET BALANCING"
    )

    for kind, items in sorted(
        grouped.items()
    ):

        random.shuffle(
            items
        )

        limit = TYPE_LIMITS.get(
            kind,
            3000,
        )

        selected = items[
            :limit
        ]

        result.extend(
            selected
        )

        print(
            f"{kind}: "
            f"{len(selected)} / "
            f"{len(items)}"
        )

    return result


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
        "FLOWPILOT SOURCE CODE DATASET V2"
    )
    print(
        "========================================"
    )

    files = discover_files()

    print(
        f"Source files: {len(files)}"
    )

    examples = []

    for index, path in enumerate(
        files,
        start=1,
    ):

        source = read_text(
            path
        )

        if not source.strip():
            continue

        entities = extract_entities(
            path,
            source,
        )

        examples.extend(
            build_file_examples(
                path,
                source,
            )
        )

        examples.extend(
            build_function_examples(
                path,
                source,
                entities,
            )
        )

        examples.extend(
            build_class_examples(
                path,
                entities,
            )
        )

        examples.extend(
            build_block_code_examples(
                path,
                source,
                entities,
            )
        )

        if index % 250 == 0:

            print(
                f"Processed: "
                f"{index}/{len(files)}"
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

    examples = balance(
        examples
    )

    print()
    print(
        f"After balancing: "
        f"{len(examples)}"
    )

    random.shuffle(
        examples
    )

    total = len(
        examples
    )

    if total < 100:
        raise RuntimeError(
            "Source dataset is unexpectedly small."
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

    type_counts = Counter(
        e["metadata"]["type"]
        for e in examples
    )

    manifest = {
        "version": "source_code_v2",
        "seed": RANDOM_SEED,
        "source_files": len(files),
        "total": total,
        "train": len(train),
        "validation": len(validation),
        "test": len(test),
        "types": dict(
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
        "SOURCE CODE DATASET V2 COMPLETE"
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


if __name__ == "__main__":
    main()