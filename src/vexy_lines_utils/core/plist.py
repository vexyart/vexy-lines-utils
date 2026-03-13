#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/core/plist.py
"""PlistManager — context manager for safe plist modification with backup/restore."""

from __future__ import annotations

import plistlib
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Self

from loguru import logger

from vexy_lines_utils.core.errors import AutomationError

_MISSING = object()

FORMAT_CODES: dict[str, str] = {
    "pdf": "pdf",
    "svg": "svg",
}

EXPORT_PREFERENCES: dict[str, Any] = {
    "export·dlg·checkLayers": True,
    "export·dlg·checkMergeColor": False,
    "export·dlg·exportMode": 1,
    "export·dlg·imageFormat": 0,
    "export·dlg·radioColor": False,
    "export·dlg·radioTransparent": True,
    "export·dlg·scale": 1.0,
    "first_start": False,
}


class PlistManager:
    """Context manager for safe plist modification with backup/restore.

    Usage::

        with PlistManager(plist_path, "pdf") as pm:
            # plist has been written with export preferences
            # app was quit before writing
            ...
        # original values restored on exit (even on exception)
    """

    def __init__(self, plist_path: Path, fmt: str, app_name: str = "Vexy Lines") -> None:
        self.plist_path = Path(plist_path).expanduser()
        self.fmt = fmt
        self.app_name = app_name
        self._originals: dict[str, Any] = {}
        self._plist_existed = False

    def __enter__(self) -> Self:
        self._quit_app()
        self._plist_existed = self.plist_path.exists()
        data = self._read_plist()
        self._store_originals(data)
        self._apply_export_prefs(data)
        self._write_plist(data)
        return self

    def __exit__(self, *exc_info: object) -> None:
        try:
            self._restore_originals()
        except Exception:
            logger.warning("Failed to restore plist — manual cleanup may be needed")

    def _quit_app(self) -> None:
        script = f'tell application "{self.app_name}" to quit'
        try:
            subprocess.run(  # noqa: S603
                ["osascript", "-e", script],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout quitting {self.app_name} (may not be running)")

    def _read_plist(self) -> dict[str, Any]:
        if not self.plist_path.exists():
            return {}
        try:
            with self.plist_path.open("rb") as f:
                return plistlib.load(f)
        except Exception as exc:
            msg = f"Cannot read plist at {self.plist_path}: {exc}"
            raise AutomationError(msg, "PLIST_ERROR") from exc

    def _store_originals(self, data: dict[str, Any]) -> None:
        all_keys = set(EXPORT_PREFERENCES) | {"export·dlg·format"}
        for key in all_keys:
            self._originals[key] = data.get(key, _MISSING)

    def _apply_export_prefs(self, data: dict[str, Any]) -> None:
        data.update(EXPORT_PREFERENCES)
        data["export·dlg·format"] = FORMAT_CODES.get(self.fmt, self.fmt)

    def _write_plist(self, data: dict[str, Any]) -> None:
        try:
            self.plist_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=self.plist_path.parent,
                suffix=".plist",
            )
            try:
                with open(fd, "wb") as f:
                    plistlib.dump(data, f, fmt=plistlib.FMT_BINARY)
                Path(tmp).replace(self.plist_path)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        except AutomationError:
            raise
        except Exception as exc:
            msg = f"Cannot write plist at {self.plist_path}: {exc}"
            raise AutomationError(msg, "PLIST_ERROR") from exc

    def _restore_originals(self) -> None:
        if not self._plist_existed and self.plist_path.exists():
            self.plist_path.unlink()
            logger.debug("Removed plist that did not exist before export")
            return

        if not self.plist_path.exists():
            return

        data = self._read_plist()
        for key, original in self._originals.items():
            if original is _MISSING:
                data.pop(key, None)
            else:
                data[key] = original
        self._write_plist(data)
        logger.debug("Restored original plist values")
