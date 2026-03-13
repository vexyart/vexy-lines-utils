#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/core/config.py
"""Configuration for Vexy Lines dialog-less export."""

from __future__ import annotations

from dataclasses import dataclass

MIN_TIMEOUT_MULTIPLIER = 0.1
MAX_TIMEOUT_MULTIPLIER = 10.0
MIN_RETRIES = 0
MAX_RETRIES = 10
VALID_FORMATS = ("pdf", "svg")

MENU_ITEMS: dict[str, str] = {
    "pdf": "Export PDF File",
    "svg": "Export SVG File",
}


@dataclass
class ExportConfig:
    """Configuration for plist-driven export."""

    app_name: str = "Vexy Lines"
    format: str = "pdf"
    poll_interval: float = 0.2
    wait_for_app: float = 20.0
    wait_for_file: float = 20.0
    post_action_delay: float = 0.4
    timeout_multiplier: float = 1.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        self.format = self.format.lower()
        if self.format not in VALID_FORMATS:
            msg = f"format must be one of {VALID_FORMATS}, got {self.format!r}"
            raise ValueError(msg)
        if not MIN_TIMEOUT_MULTIPLIER <= self.timeout_multiplier <= MAX_TIMEOUT_MULTIPLIER:
            msg = (
                f"timeout_multiplier must be between {MIN_TIMEOUT_MULTIPLIER} "
                f"and {MAX_TIMEOUT_MULTIPLIER}, got {self.timeout_multiplier}"
            )
            raise ValueError(msg)
        if not MIN_RETRIES <= self.max_retries <= MAX_RETRIES:
            msg = f"max_retries must be between {MIN_RETRIES} and {MAX_RETRIES}, got {self.max_retries}"
            raise ValueError(msg)
        if not self.app_name.strip():
            msg = "app_name cannot be empty"
            raise ValueError(msg)

    def scale_timeout(self, base_timeout: float) -> float:
        return base_timeout * self.timeout_multiplier

    @property
    def export_menu_item(self) -> str:
        return MENU_ITEMS[self.format]

    @property
    def export_extension(self) -> str:
        return f".{self.format}"
