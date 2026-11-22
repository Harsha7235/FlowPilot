"""
FlowPilot Research-to-GNU-Radio Bridge.

Connects extracted research-paper text to candidate GNU Radio designs.

This module uses deterministic Python rules only.
It does not use AI, machine learning, Ollama, or external APIs.

Design suggestions are candidates, not verified runnable flowgraphs.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BlockCandidate:
    """A candidate GNU Radio block and its verification requirements."""

    name: str
    purpose: str
    parameters_to_verify: list[str] = field(default_factory=list)


@dataclass
class ResearchDesign:
    """A proposed research-to-GNU-Radio design."""

    method: str
    description: str
    blocks: list[BlockCandidate]
    assumptions: list[str]
    questions: list[str]


class ResearchBridge:
    """
    Maps research-paper terminology to candidate GNU Radio blocks
    using deterministic text-matching rules.
    """

    METHOD_RULES = {
        "ofdm": {
            "description": (
                "Orthogonal Frequency Division Multiplexing (OFDM) "
                "transmits data using multiple orthogonal subcarriers."
            ),
            "blocks": [
                BlockCandidate(
                    "Constellation Modulator",
                    "Maps data symbols to modulation points.",
                    ["Constellation", "Symbol mapping"],
                ),
                BlockCandidate(
                    "OFDM Carrier Allocator",
                    "Maps data and pilot symbols onto OFDM subcarriers.",
                    ["FFT length", "Occupied carriers", "Pilot carriers"],
                ),
                BlockCandidate(
                    "IFFT",
                    "Transforms frequency-domain carriers into a time-domain signal.",
                    ["FFT length", "Normalization"],
                ),
                BlockCandidate(
                    "Cyclic Prefixer",
                    "Adds a cyclic prefix to help reduce inter-symbol interference.",
                    ["FFT length", "Cyclic-prefix length"],
                ),
                BlockCandidate(
                    "Channel Model",
                    "Simulates channel effects when required.",
                    ["Noise voltage", "Frequency offset", "Multipath settings"],
                ),
                BlockCandidate(
                    "OFDM Receiver",
                    "Performs synchronization and OFDM symbol recovery.",
                    ["Synchronization", "Equalization", "Carrier configuration"],
                ),
            ],
        },

        "qam": {
            "description": (
                "Quadrature Amplitude Modulation (QAM) represents "
                "digital symbols using amplitude and phase variations."
            ),
            "blocks": [
                BlockCandidate(
                    "Constellation Modulator",
                    "Maps input symbols to a QAM constellation.",
                    ["Constellation order", "Normalization"],
                ),
                BlockCandidate(
                    "Channel Model",
                    "Simulates channel impairments when required.",
                    ["Noise voltage", "Frequency offset"],
                ),
                BlockCandidate(
                    "Constellation Decoder",
                    "Recovers symbol decisions from received samples.",
                    ["Constellation definition", "Decision method"],
                ),
            ],
        },

        "fm": {
            "description": (
                "Frequency Modulation (FM) represents information "
                "through changes in instantaneous carrier frequency."
            ),
            "blocks": [
                BlockCandidate(
                    "Signal Source",
                    "Generates a test signal.",
                    ["Waveform", "Sample rate", "Amplitude"],
                ),
                BlockCandidate(
                    "Frequency Modulator",
                    "Converts the input signal into an FM signal.",
                    ["Sensitivity", "Sample rate"],
                ),
                BlockCandidate(
                    "Frequency Demodulator",
                    "Recovers the modulating signal.",
                    ["Sensitivity", "Sample rate"],
                ),
                BlockCandidate(
                    "QT GUI Sink",
                    "Displays the signal for inspection.",
                    ["Input type", "Sample rate"],
                ),
            ],
        },

        "psk": {
            "description": (
                "Phase Shift Keying (PSK) represents digital symbols "
                "through changes in carrier phase."
            ),
            "blocks": [
                BlockCandidate(
                    "Constellation Modulator",
                    "Maps symbols to a PSK constellation.",
                    ["Constellation order", "Differential encoding"],
                ),
                BlockCandidate(
                    "Channel Model",
                    "Simulates noise and channel impairments if required.",
                    ["Noise voltage", "Frequency offset"],
                ),
                BlockCandidate(
                    "Constellation Decoder",
                    "Recovers symbol decisions from received samples.",
                    ["Constellation definition", "Synchronization"],
                ),
            ],
        },

        "fft": {
            "description": (
                "The Fast Fourier Transform (FFT) converts sampled data "
                "between time-domain and frequency-domain representations."
            ),
            "blocks": [
                BlockCandidate(
                    "Stream to Vector",
                    "Groups incoming samples into vectors.",
                    ["Vector length", "Stream item type"],
                ),
                BlockCandidate(
                    "FFT",
                    "Computes the frequency-domain representation.",
                    ["FFT length", "Window", "Transform direction"],
                ),
                BlockCandidate(
                    "QT GUI Frequency Sink",
                    "Displays the frequency spectrum.",
                    ["Sample rate", "Input type"],
                ),
            ],
        },
    }

    def __init__(self):
        self.paper: Optional[dict] = None

    def set_paper(self, paper: dict) -> None:
        """
        Set the paper dictionary returned by PDFReader.

        Expected format:
            {
                "full_text": "...",
                "file_name": "...",
                ...
            }
        """
        if not isinstance(paper, dict):
            raise TypeError("paper must be a dictionary.")

        self.paper = paper

    def extract_parameters(self) -> list[dict]:
        """
        Extract explicit numerical parameter expressions from paper text.

        Results are candidates for manual verification, not guaranteed
        engineering parameters.
        """
        if not self.paper:
            return []

        text = self.paper.get("full_text", "")

        if not isinstance(text, str) or not text.strip():
            return []

        patterns = [
            (
                r"\b(sample rate|sampling frequency|sampling rate)\b"
                r"\s*(?:of|=|:)?\s*"
                r"([0-9]+(?:\.[0-9]+)?)\s*"
                r"(kHz|MHz|GHz|Hz)\b"
            ),
            (
                r"\b(FFT size|FFT length|number of subcarriers|"
                r"cyclic prefix length|carrier frequency|bandwidth)\b"
                r"\s*(?:of|=|:)?\s*"
                r"([0-9]+(?:\.[0-9]+)?)\s*"
                r"(kHz|MHz|GHz|Hz|samples|subcarriers)?\b"
            ),
            (
                r"\b(SNR|signal-to-noise ratio)\b"
                r"\s*(?:of|=|:)?\s*"
                r"(-?[0-9]+(?:\.[0-9]+)?)\s*(dB)\b"
            ),
        ]

        found = []
        seen = set()

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                parameter = match.group(1)
                value = match.group(2)
                unit = match.group(3) or ""

                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)

                item = {
                    "parameter": parameter,
                    "value": value,
                    "unit": unit,
                    "context": re.sub(
                        r"\s+",
                        " ",
                        text[context_start:context_end],
                    ).strip(),
                }

                key = (
                    parameter.lower(),
                    value,
                    unit.lower(),
                )

                if key not in seen:
                    seen.add(key)
                    found.append(item)

        return found

    def detect_methods(self) -> list[str]:
        """
        Detect supported research methods mentioned in the paper.

        Supported methods: OFDM, QAM, FM, PSK and FFT.
        """
        if not self.paper:
            return []

        text = self.paper.get("full_text", "")

        if not isinstance(text, str) or not text.strip():
            return []

        text = text.lower()
        detected = []

        for method in self.METHOD_RULES:
            if re.search(
                rf"\b{re.escape(method)}\b",
                text,
            ):
                detected.append(method)

        return detected

    def propose_design(self, method: str) -> ResearchDesign:
        """
        Create a candidate design for a supported research method.
        """
        if not isinstance(method, str) or not method.strip():
            raise ValueError("Please provide a research method.")

        key = method.strip().lower()

        if key not in self.METHOD_RULES:
            available = ", ".join(self.METHOD_RULES.keys())

            raise ValueError(
                f"Unsupported method '{method}'. "
                f"Available methods: {available}"
            )

        rule = self.METHOD_RULES[key]

        # Copy the block candidates so callers cannot accidentally
        # modify the shared method definitions.
        blocks = [
            BlockCandidate(
                name=block.name,
                purpose=block.purpose,
                parameters_to_verify=list(block.parameters_to_verify),
            )
            for block in rule["blocks"]
        ]

        assumptions = [
            "The method was selected explicitly by the user.",
            (
                "Block names are conceptual candidates. Actual block "
                "availability depends on the installed GNU Radio version."
            ),
            (
                "Stream types, vector lengths, sample rates and "
                "connections must be verified before execution."
            ),
            (
                "The suggested blocks have not been automatically "
                "validated as a complete runnable flowgraph."
            ),
        ]

        questions = [
            "What are the required input and output signal types?",
            "What sample rate does the experiment require?",
            "Which GNU Radio version and blocks are installed?",
            "What measurements will establish that the experiment works?",
        ]

        if key == "ofdm":
            questions.extend([
                "What FFT length and cyclic-prefix length does the paper specify?",
                "Which occupied carriers and pilot positions are required?",
                "Which synchronization and equalization methods are specified?",
            ])

        elif key in {"qam", "psk"}:
            questions.extend([
                "What constellation order does the paper use?",
                "Does the experiment require timing recovery?",
                "Does the experiment require carrier recovery?",
            ])

        elif key == "fm":
            questions.extend([
                "What frequency deviation does the experiment require?",
                "What audio bandwidth and sample rate are specified?",
            ])

        elif key == "fft":
            questions.extend([
                "What FFT length does the experiment require?",
                "Which window function should be used?",
                "Is the required transform forward or inverse?",
            ])

        return ResearchDesign(
            method=key,
            description=rule["description"],
            blocks=blocks,
            assumptions=assumptions,
            questions=questions,
        )

    def format_design(self, design: ResearchDesign) -> str:
        """
        Convert a ResearchDesign object into readable text.
        """
        lines = [
            f"RESEARCH DESIGN CANDIDATE: {design.method.upper()}",
            "",
            design.description,
            "",
            "CANDIDATE GNU RADIO BLOCKS",
            "--------------------------",
        ]

        for index, block in enumerate(design.blocks, start=1):
            lines.append(f"{index}. {block.name}")
            lines.append(f"   Purpose: {block.purpose}")
            lines.append(
                "   Verify: "
                + ", ".join(block.parameters_to_verify)
            )
            lines.append("")

        lines.extend([
            "ASSUMPTIONS AND LIMITATIONS",
            "---------------------------",
        ])

        lines.extend(
            f"- {item}"
            for item in design.assumptions
        )

        lines.extend([
            "",
            "QUESTIONS TO RESOLVE BEFORE IMPLEMENTATION",
            "------------------------------------------",
        ])

        lines.extend(
            f"- {item}"
            for item in design.questions
        )

        return "\n".join(lines)

    def get_design_text(self, method: str) -> str:
        """
        Convenience method: propose and format a design in one call.
        """
        design = self.propose_design(method)
        return self.format_design(design)