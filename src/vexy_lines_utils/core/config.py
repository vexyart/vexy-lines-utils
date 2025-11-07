#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/core/config.py
"""Configuration classes for Vexy Lines automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MenuStrategy(Enum):
    """Different strategies for triggering the Export menu."""

    PYXA = "pyxa"
    APPLESCRIPT = "applescript"
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    ACCESSIBILITY_API = "accessibility_api"


class DialogStrategy(Enum):
    """Different strategies for handling save dialogs."""

    COMMAND_SHIFT_G = "cmd_shift_g"  # Standard macOS navigation
    DIRECT_PATH = "direct_path"  # Type full path
    FILENAME_ONLY = "filename_only"  # Just filename
    APPLESCRIPT_DIALOG = "applescript"  # Use AppleScript
    ACCESSIBILITY_API = "accessibility"  # Direct accessibility


@dataclass
class AutomationConfig:
    """Basic configuration for Vexy Lines automation."""

    app_name: str = "Vexy Lines"
    poll_interval: float = 0.2
    wait_for_app: float = 20.0
    wait_for_file: float = 20.0
    wait_for_dialog: float = 25.0
    post_action_delay: float = 0.4
    export_menu: tuple[str, str] = ("File", "Export...")
    close_menu: tuple[str, str] = ("File", "Close")
    export_window_title: str = "Export"
    save_window_title: str = "Save"
    timeout_multiplier: float = 1.0  # Scale all timeouts for slower systems
    max_retries: int = 3  # Maximum retry attempts for transient failures

    def scale_timeout(self, base_timeout: float) -> float:
        """Apply timeout multiplier to a base timeout value."""
        return base_timeout * self.timeout_multiplier


@dataclass
class EnhancedAutomationConfig(AutomationConfig):
    """Enhanced configuration with multiple strategy options."""

    # Menu strategies in order of preference
    menu_strategies: list[MenuStrategy] = field(
        default_factory=lambda: [
            MenuStrategy.KEYBOARD_SHORTCUT,  # Most reliable if shortcut exists
            MenuStrategy.APPLESCRIPT,  # Good macOS integration
            MenuStrategy.PYXA,  # Original approach
        ]
    )

    # Dialog strategies in order of preference
    dialog_strategies: list[DialogStrategy] = field(
        default_factory=lambda: [
            DialogStrategy.COMMAND_SHIFT_G,
            DialogStrategy.APPLESCRIPT_DIALOG,
            DialogStrategy.DIRECT_PATH,
            DialogStrategy.FILENAME_ONLY,
        ]
    )

    # Keyboard shortcuts (if known)
    export_shortcut: tuple[str, ...] | None = field(default_factory=lambda: ("command", "e"))  # Cmd+E for Export

    # Export menu paths for different strategies
    export_menu_index: tuple[int, int] | None = None  # (menu_index, item_index) if known

    # Window title patterns (more flexible matching)
    export_window_patterns: list[str] = field(default_factory=lambda: ["Export", "export", "Save As", "Save as"])
    save_window_patterns: list[str] = field(default_factory=lambda: ["Save", "save", "Export", "export"])

    # Retry configuration
    retry_backoff: float = 2.0  # Exponential backoff base
