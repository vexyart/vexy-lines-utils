#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/automation/__init__.py
"""Automation modules for Vexy Lines."""

from vexy_lines_utils.automation.bridges import AppleScriptBridge, ApplicationBridge
from vexy_lines_utils.automation.window_watcher import WindowWatcher

__all__ = [
    "AppleScriptBridge",
    "ApplicationBridge",
    "WindowWatcher",
]
