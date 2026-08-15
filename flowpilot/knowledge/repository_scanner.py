"""Command-line entry point for the FlowPilot Repository Scanner.
 
Usage:
 
    python -m flowpilot.repository_scanner \\
        --third-party-dir third_party \\
        --output repository_inventory.json
"""
 
from __future__ import annotations
 
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence
 
from flowpilot.core.exceptions import FlowPilotError
from flowpilot.core.models import ScanStatus
from flowpilot.core.utils import configure_logger
from flowpilot.knowledge.scanner import ScannerEngine
 
__all__ = ["main"]
 
_DEFAULT_THIRD_PARTY_DIR = Path("third_party")
_DEFAULT_OUTPUT_PATH = Path("repository_inventory.json")
 
 
def _build_arg_parser() -> argparse.ArgumentParser:
    """Builds the command-line argument parser for the scanner CLI.
 
    Returns:
        A configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="repository-scanner",
        description=(
            "Scans third-party GNU Radio, OOT module, and hardware SDK "
            "repositories and produces a consolidated repository inventory report."
        ),
    )
    parser.add_argument(
        "--third-party-dir",
        type=Path,
        default=_DEFAULT_THIRD_PARTY_DIR,
        help="Directory containing third-party repository clones to scan "
        f"(default: {_DEFAULT_THIRD_PARTY_DIR}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT_PATH,
        help="Path the inventory report JSON will be written to "
        f"(default: {_DEFAULT_OUTPUT_PATH}).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser
 
 
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Runs the FlowPilot Repository Scanner as a command-line tool.
 
    Args:
        argv: The command-line arguments to parse, excluding the
            program name. Defaults to ``sys.argv[1:]`` when omitted.
 
    Returns:
        An exit code: ``0`` on a fully successful scan, ``1`` if the
        scan completed with failures or could not run, and ``2`` on an
        unexpected error.
    """
    args = _build_arg_parser().parse_args(argv)
    level = logging.DEBUG if args.verbose else logging.INFO
    logger = configure_logger("flowpilot.repository_scanner", level=level)
 
    logger.info(
        "Starting repository scan (third_party_dir=%s, output=%s)",
        args.third_party_dir,
        args.output,
    )
 
    try:
        engine = ScannerEngine(
            third_party_dir=args.third_party_dir,
            output_path=args.output,
            logger=logger,
        )
        report = engine.scan()
    except FlowPilotError as exc:
        logger.error("Repository scan failed: %s", exc)
        return 1
    except Exception:  # noqa: BLE001 - top-level CLI guard.
        logger.exception("Unexpected error during repository scan")
        return 2
 
    if report.overall_status == ScanStatus.FAILED:
        logger.error(
            "Repository scan completed with FAILED status (%d errors)", len(report.errors)
        )
        return 1
 
    logger.info(
        "Repository scan finished: %d repositories scanned, %d errors",
        report.total_repositories,
        len(report.errors),
    )
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())