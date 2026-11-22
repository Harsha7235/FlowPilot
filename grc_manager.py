"""
FlowPilot GNU Radio Integration
--------------------------------

Responsibilities:
1. Detect GNU Radio Companion.
2. Launch GNU Radio Companion.
3. Find saved .grc files.
4. Open a selected flowgraph.
5. Keep flowgraphs inside the FlowPilot workspace.

This module does not automatically execute flowgraphs.
"""

import os
import shutil
import subprocess
import sys

from pathlib import Path


class GRCManager:

    def __init__(
        self,
        project_root: str | Path | None = None
    ):

        if project_root is None:

            project_root = (
                Path(__file__)
                .resolve()
                .parents[2]
            )

        self.project_root = Path(
            project_root
        ).resolve()

        self.flowgraph_dir = (
            self.project_root
            / "data"
            / "flowgraphs"
        )

        self.flowgraph_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # --------------------------------------------------
    # Locate GNU Radio Companion
    # --------------------------------------------------

    def find_executable(self) -> str | None:

        configured = os.environ.get(
            "GRC_EXECUTABLE"
        )

        if configured:

            configured_path = Path(
                configured
            ).expanduser()

            if configured_path.is_file():

                return str(
                    configured_path.resolve()
                )

            located = shutil.which(
                configured
            )

            if located:

                return located

        candidates = [
            "gnuradio-companion",
            "grc"
        ]

        for name in candidates:

            executable = shutil.which(
                name
            )

            if executable:

                return executable

        if sys.platform == "win32":

            windows_candidates = [

                Path(
                    r"C:\Program Files\GNURadio-3.10\bin"
                    r"\gnuradio-companion.exe"
                ),

                Path(
                    r"C:\Program Files\GNU Radio\bin"
                    r"\gnuradio-companion.exe"
                ),

            ]

            for candidate in windows_candidates:

                if candidate.is_file():

                    return str(candidate)

        return None

    # --------------------------------------------------
    # Check installation
    # --------------------------------------------------

    def check_installation(self) -> dict:

        executable = self.find_executable()

        return {

            "available": executable is not None,

            "executable": executable,

            "flowgraph_directory": str(
                self.flowgraph_dir
            ),

            "message": (
                f"GNU Radio Companion found:\n{executable}"
                if executable
                else
                "GNU Radio Companion was not found. "
                "Install GNU Radio or configure "
                "the GRC_EXECUTABLE environment variable."
            )

        }

    # --------------------------------------------------
    # Launch GNU Radio Companion
    # --------------------------------------------------

    def launch(self) -> str:

        executable = self.find_executable()

        if not executable:

            raise FileNotFoundError(
                self.check_installation()["message"]
            )

        subprocess.Popen(
            [executable],
            cwd=str(self.project_root)
        )

        return (
            "GNU Radio Companion launched successfully.\n"
            f"Executable: {executable}"
        )

    # --------------------------------------------------
    # Find flowgraphs
    # --------------------------------------------------

    def list_flowgraphs(self) -> list[Path]:

        return sorted(
            self.flowgraph_dir.glob("*.grc"),
            key=lambda path: path.name.lower()
        )

    # --------------------------------------------------
    # Open an existing flowgraph
    # --------------------------------------------------

    def open_flowgraph(
        self,
        flowgraph_path: str
    ) -> str:

        candidate = Path(
            flowgraph_path
        ).expanduser().resolve()

        allowed_directory = (
            self.flowgraph_dir.resolve()
        )

        if candidate.suffix.lower() != ".grc":

            raise ValueError(
                "Only .grc flowgraph files are supported."
            )

        if allowed_directory not in candidate.parents:

            raise ValueError(
                "Open flowgraphs from the FlowPilot "
                "data/flowgraphs directory."
            )

        if not candidate.is_file():

            raise FileNotFoundError(
                f"Flowgraph not found: {candidate}"
            )

        executable = self.find_executable()

        if not executable:

            raise FileNotFoundError(
                self.check_installation()["message"]
            )

        subprocess.Popen(
            [
                executable,
                str(candidate)
            ],
            cwd=str(self.project_root)
        )

        return (
            f"Opened flowgraph:\n"
            f"{candidate.name}"
        )