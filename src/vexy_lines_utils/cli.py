#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/cli.py
"""Command-line interface for Vexy Lines utils."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import fire
from loguru import logger

from vexy_lines_utils.core.config import AutomationConfig, EnhancedAutomationConfig
from vexy_lines_utils.exporters.enhanced import EnhancedVexyLinesExporter
from vexy_lines_utils.exporters.standard import VexyLinesExporter
from vexy_lines_utils.utils.system import speak


class VexyLinesCLI:
    """Fire CLI surface."""

    # Validation constants
    MIN_TIMEOUT_MULTIPLIER = 0.1
    MAX_TIMEOUT_MULTIPLIER = 10
    MAX_RETRY_LIMIT = 10

    def export(
        self,
        target: str,
        *,
        verbose: bool = False,
        dry_run: bool = False,
        say_summary: bool = False,
        timeout_multiplier: float = 1.0,
        max_retries: int = 3,
        enhanced: bool = True,  # Default to True for better reliability
    ) -> dict[str, object]:
        """Export .lines documents found under *target* to PDF.

        Args:
            target: Path to .lines file or directory to search
            verbose: Show detailed progress messages
            dry_run: Preview files without processing
            say_summary: Announce completion via text-to-speech
            timeout_multiplier: Scale all timeouts (2.0 = double all timeouts)
            max_retries: Maximum retry attempts for transient failures (0-10)
            enhanced: Use enhanced exporter with multiple fallback strategies (default: True)

        Returns:
            Dictionary with export statistics
        """
        # Validate arguments
        if timeout_multiplier < self.MIN_TIMEOUT_MULTIPLIER or timeout_multiplier > self.MAX_TIMEOUT_MULTIPLIER:
            msg = f"timeout_multiplier must be between {self.MIN_TIMEOUT_MULTIPLIER} and {self.MAX_TIMEOUT_MULTIPLIER}"
            raise ValueError(msg)
        if max_retries < 0 or max_retries > self.MAX_RETRY_LIMIT:
            msg = f"max_retries must be between 0 and {self.MAX_RETRY_LIMIT}"
            raise ValueError(msg)

        # Create config based on mode
        if enhanced:
            config = EnhancedAutomationConfig(timeout_multiplier=timeout_multiplier, max_retries=max_retries)
            exporter = EnhancedVexyLinesExporter(config=config, dry_run=dry_run)
        else:
            config = AutomationConfig(timeout_multiplier=timeout_multiplier, max_retries=max_retries)
            exporter = VexyLinesExporter(config=config, dry_run=dry_run)

        stats = exporter.export(Path(target), verbose=verbose)
        if say_summary:
            speak(stats.human_summary())

        # Close any remaining open document after batch completes
        if not dry_run:
            exporter.close_final_document()

        return stats.as_dict()

    def test_strategies(self) -> None:
        """Test which automation strategies work on this system."""
        logger.info("Testing available automation strategies...")

        # Test PyXA
        try:
            if importlib.util.find_spec("PyXA") is not None:
                logger.success("✅ PyXA available")
            else:
                logger.warning("❌ PyXA not available")
        except (ImportError, ValueError):
            logger.warning("❌ PyXA not available")

        # Test AppleScript
        try:
            result = subprocess.run(["osascript", "-e", 'return "test"'], check=False, capture_output=True)  # noqa: S607
            if result.returncode == 0:
                logger.success("✅ AppleScript available")
            else:
                logger.warning("❌ AppleScript failed")
        except Exception:
            logger.warning("❌ AppleScript not available")

        # Test keyboard libraries
        if importlib.util.find_spec("pyautogui") is not None:
            logger.success("✅ pyautogui available")
        else:
            logger.warning("❌ pyautogui not available")

        if importlib.util.find_spec("pyperclip") is not None:
            logger.success("✅ pyperclip available")
        else:
            logger.warning("❌ pyperclip not available")

        if importlib.util.find_spec("keyboard") is not None:
            logger.success("✅ keyboard library available")
        else:
            logger.warning("⚠️  keyboard library not available (better than pyautogui for keyboard input)")

        # Test accessibility permissions
        logger.info("\nChecking accessibility permissions...")
        logger.info("Ensure Terminal/IDE has accessibility permissions in:")
        logger.info("System Settings > Privacy & Security > Accessibility")


def main() -> None:
    """Entry-point for the CLI."""
    fire.Fire(VexyLinesCLI)


if __name__ == "__main__":
    main()
