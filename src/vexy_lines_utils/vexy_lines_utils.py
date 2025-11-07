#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/vexy_lines_utils.py
"""Automation helpers for exporting Vexy Lines documents to PDF."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import fire
from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

try:  # Optional dependency; we guard usage at runtime.
    import PyXA  # type: ignore
except ImportError:  # pragma: no cover - exercised on systems without PyXA
    PyXA = None  # type: ignore[assignment]

try:  # Optional dependency for UI automation.
    import pyautogui  # type: ignore
except ImportError:  # pragma: no cover - exercised on CI
    pyautogui = None  # type: ignore[assignment]

try:  # Clipboard helper.
    import pyperclip  # type: ignore
except ImportError:  # pragma: no cover - exercised on CI
    pyperclip = None  # type: ignore[assignment]


class AutomationError(RuntimeError):
    """Raised when the automation flow cannot continue."""

    def __init__(self, message: str, error_code: str = "UNKNOWN") -> None:
        super().__init__(message)
        self.error_code = error_code


class FileValidationError(AutomationError):
    """Raised when a .lines file is invalid or corrupted."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "FILE_INVALID")


@dataclass(frozen=True)
class AutomationConfig:
    """Tunables that describe how we talk to Vexy Lines."""

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
class ExportStats:
    """Outcome of a batch operation."""

    processed: int = 0
    success: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    dry_run: bool = False

    def record_success(self, path: Path) -> None:
        self.processed += 1
        self.success += 1
        logger.success("Exported %s", path.name)

    def record_failure(self, path: Path, reason: str) -> None:
        self.processed += 1
        self.failures.append((str(path), reason))
        logger.error("%s failed: %s", path.name, reason)

    def as_dict(self) -> dict[str, object]:
        return {
            "processed": self.processed,
            "success": self.success,
            "failed": len(self.failures),
            "failures": list(self.failures),
            "dry_run": self.dry_run,
        }

    def human_summary(self) -> str:
        state = "dry-run " if self.dry_run else ""
        return f"{state}{self.success}/{self.processed} exports succeeded"


def find_lines_files(path: Path) -> list[Path]:
    """Return sorted .lines files for the supplied target."""
    if path.is_file() and path.suffix.lower() == ".lines":
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.lines"))
    return []


def validate_lines_file(path: Path) -> None:
    """Validate that a .lines file is accessible and not corrupted."""
    if not path.exists():
        msg = f"File does not exist: {path}"
        raise FileValidationError(msg)

    if not path.is_file():
        msg = f"Not a file: {path}"
        raise FileValidationError(msg)

    if path.suffix.lower() != ".lines":
        msg = f"Not a .lines file: {path}"
        raise FileValidationError(msg)

    # Check file is readable and not empty
    try:
        size = path.stat().st_size
        if size == 0:
            msg = f"File is empty: {path}"
            raise FileValidationError(msg)
        # Very large files might indicate corruption
        if size > 500 * 1024 * 1024:  # 500MB
            logger.warning("Large file detected (%s MB): %s", size // (1024 * 1024), path)
    except OSError as e:
        msg = f"Cannot access file {path}: {e}"
        raise FileValidationError(msg)


class ApplicationBridge(Protocol):
    """Minimal interface used by the exporter."""

    def activate(self) -> None: ...

    def window_titles(self) -> list[str]: ...

    def click_menu_item(self, menu_name: str, item_name: str) -> bool: ...


class PyXABridge:
    """Concrete ApplicationBridge implemented with PyXA."""

    def __init__(self, config: AutomationConfig):
        if PyXA is None:  # pragma: no cover - requires macOS + PyXA
            msg = "PyXA is not available. Install mac-pyxa in a macOS environment."
            raise AutomationError(msg)
        self.config = config
        try:
            self.app = PyXA.Application(config.app_name)  # type: ignore
            self.app.launch()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - OS level
            msg = f"Failed to launch {config.app_name}"
            raise AutomationError(msg) from exc
        self._wait_for_ready()

    def activate(self) -> None:
        try:
            self.app.activate()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - OS level
            msg = "Unable to activate Vexy Lines"
            raise AutomationError(msg) from exc

    def window_titles(self) -> list[str]:
        titles: list[str] = []
        try:
            for window in self.app.windows():  # type: ignore[attr-defined]
                title = str(getattr(window, "title", "")).strip()
                if title:
                    titles.append(title)
        except Exception:  # pragma: no cover - OS level
            return []
        return titles

    def click_menu_item(self, menu_name: str, item_name: str) -> bool:
        try:
            menu_bar = self.app.menu_bars()[0]  # type: ignore[attr-defined]
            menu_bar_item = menu_bar.menu_bar_items().by_name(menu_name)
            if not menu_bar_item:
                return False
            menu = menu_bar_item.menus()[0]
            menu_item = menu.menu_items().by_name(item_name)
            if not menu_item:
                return False
            menu_item.click()
            return True
        except Exception:  # pragma: no cover - OS level
            return False

    def _wait_for_ready(self) -> None:
        watcher = WindowWatcher(
            title_provider=self.window_titles,
            poll_interval=self.config.poll_interval,
        )
        watcher.wait_for_any(timeout=self.config.wait_for_app)


@dataclass
class WindowWatcher:
    """Polls Vexy Lines windows until a condition is met."""

    title_provider: Callable[[], Sequence[str]]
    poll_interval: float = 0.2

    def wait_for_contains(self, needle: str, *, present: bool, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            titles = self.title_provider()
            has_title = any(needle in title for title in titles)
            if has_title == present:
                return
            time.sleep(self.poll_interval)
        state = "appear" if present else "disappear"
        msg = f"Timed out waiting for '{needle}' to {state}"
        raise AutomationError(msg, "TIMEOUT")

    def wait_for_any(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.title_provider():
                return
            time.sleep(self.poll_interval)
        msg = "Timed out waiting for the application window"
        raise AutomationError(msg, "APP_NOT_READY")


class UIActions:
    """Keyboard and clipboard automation helper."""

    def __init__(self, *, dry_run: bool = False):
        self.dry_run = dry_run
        self._pyautogui = pyautogui
        self._pyperclip = pyperclip
        self.recorded: list[str] = []
        if not dry_run:
            if self._pyautogui is None or self._pyperclip is None:
                msg = "pyautogui-ng and pyperclip are required for automation."
                raise AutomationError(msg)
            self._pyautogui.PAUSE = 0  # type: ignore[attr-defined]

    def press(self, key: str) -> None:
        self._record(f"press:{key}")
        if not self.dry_run:
            self._pyautogui.press(key)  # type: ignore[union-attr]

    def hotkey(self, *keys: str) -> None:
        combo = "+".join(keys)
        self._record(f"hotkey:{combo}")
        if not self.dry_run:
            self._pyautogui.hotkey(*keys)  # type: ignore[union-attr]

    def copy_text(self, text: str) -> None:
        self._record(f"copy:{text}")
        if not self.dry_run:
            self._pyperclip.copy(text)  # type: ignore[union-attr]

    def _record(self, action: str) -> None:
        self.recorded.append(action)


def speak(text: str) -> None:
    """Use macOS VoiceOver to announce status, ignoring failures."""
    try:
        subprocess.run(["say", text], check=False)
    except Exception:  # pragma: no cover - best effort
        logger.debug("say command unavailable")


class VexyLinesExporter:
    """Batch exports .lines documents to PDF using the Vexy Lines UI."""

    def __init__(
        self,
        *,
        config: AutomationConfig | None = None,
        bridge: ApplicationBridge | None = None,
        ui_actions: UIActions | None = None,
        dry_run: bool = False,
    ):
        self.config = config or AutomationConfig()
        self.dry_run = dry_run
        self._bridge = bridge
        self._ui = ui_actions or UIActions(dry_run=dry_run)
        self._watcher: WindowWatcher | None = None

    @property
    def bridge(self) -> ApplicationBridge:
        if self._bridge is None:
            if self.dry_run:
                msg = "Dry-run mode requires a test bridge"
                raise AutomationError(msg)
            self._bridge = PyXABridge(self.config)
        return self._bridge

    @property
    def watcher(self) -> WindowWatcher:
        if self._watcher is None:
            self._watcher = WindowWatcher(
                title_provider=self.bridge.window_titles,
                poll_interval=self.config.poll_interval,
            )
        return self._watcher

    def export(self, target: Path, *, verbose: bool = False) -> ExportStats:
        path = target.expanduser().resolve()
        logger.info("Scanning %s", path)
        files = find_lines_files(path)
        if not files:
            msg = f"No .lines files found at {path}"
            raise AutomationError(msg, "NO_FILES")
        stats = ExportStats(dry_run=self.dry_run)
        for file_path in files:
            try:
                if verbose:
                    logger.info("Processing %s", file_path)

                # Validate file before processing
                if not self.dry_run:
                    validate_lines_file(file_path)

                if self.dry_run:
                    stats.record_success(file_path)
                    continue

                # Try with retries for transient failures
                self._process_file_with_retry(file_path)
                stats.record_success(file_path)
            except FileValidationError as exc:
                stats.record_failure(file_path, f"Validation failed: {exc}")
            except Exception as exc:
                stats.record_failure(file_path, str(exc))
        return stats

    def _process_file_with_retry(self, file_path: Path) -> None:
        """Process file with retry logic for transient failures."""
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                if attempt > 0:
                    logger.info("Retry attempt %d/%d for %s", attempt + 1, self.config.max_retries, file_path.name)
                    # Exponential backoff: 2, 4, 8 seconds...
                    time.sleep(2**attempt)

                self._process_file(file_path)
                return  # Success!

            except AutomationError as e:
                last_error = e
                # Don't retry certain errors
                if e.error_code in ["FILE_INVALID", "NO_FILES"]:
                    raise
                logger.warning("Attempt %d failed: %s", attempt + 1, str(e))

        # All retries exhausted
        if last_error:
            raise last_error
        msg = f"Failed after {self.config.max_retries} attempts"
        raise AutomationError(msg, "MAX_RETRIES")

    def _process_file(self, file_path: Path) -> None:
        pdf_path = file_path.with_suffix(".pdf")
        if pdf_path.exists():
            pdf_path.unlink()
        self.bridge.activate()
        self._open_document(file_path)
        self._trigger_export()
        self._handle_save_dialog(file_path)
        self._verify_export(pdf_path)
        self._close_document()

    def _open_document(self, file_path: Path) -> None:
        result = subprocess.run(
            ["open", "-a", self.config.app_name, str(file_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            msg = f"Failed to open {file_path}: {result.stderr.strip()}"
            raise AutomationError(msg, "OPEN_FAILED")
        self.watcher.wait_for_contains(
            needle=file_path.stem,
            present=True,
            timeout=self.config.scale_timeout(self.config.wait_for_file),
        )
        time.sleep(self.config.post_action_delay)

    def _trigger_export(self) -> None:
        menu_name, item_name = self.config.export_menu
        if not self.bridge.click_menu_item(menu_name, item_name):
            msg = "Failed to open Export dialog"
            raise AutomationError(msg, "MENU_CLICK_FAILED")
        self.watcher.wait_for_contains(
            needle=self.config.export_window_title,
            present=True,
            timeout=self.config.scale_timeout(self.config.wait_for_dialog),
        )
        time.sleep(self.config.post_action_delay)
        self._ui.press("enter")
        time.sleep(self.config.post_action_delay)

    def _handle_save_dialog(self, file_path: Path) -> None:
        self.watcher.wait_for_contains(
            needle=self.config.save_window_title,
            present=True,
            timeout=self.config.wait_for_dialog,
        )
        folder_path = str(file_path.parent)
        pdf_name = file_path.with_suffix(".pdf").name
        # Navigate to folder.
        self._ui.hotkey("command", "shift", "g")
        time.sleep(self.config.post_action_delay)
        self._ui.copy_text(folder_path)
        self._ui.hotkey("command", "v")
        self._ui.press("enter")
        time.sleep(self.config.post_action_delay)
        # Set filename.
        self._ui.hotkey("command", "a")
        time.sleep(self.config.post_action_delay / 2)
        self._ui.copy_text(pdf_name)
        self._ui.hotkey("command", "v")
        time.sleep(self.config.post_action_delay / 2)
        self._ui.press("enter")
        time.sleep(self.config.post_action_delay)
        # Confirm overwrite dialog (if present).
        self._ui.press("enter")
        self.watcher.wait_for_contains(
            needle=self.config.save_window_title,
            present=False,
            timeout=self.config.wait_for_dialog,
        )

    def _verify_export(self, pdf_path: Path) -> None:
        deadline = time.monotonic() + self.config.wait_for_dialog
        while time.monotonic() < deadline:
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                return
            time.sleep(self.config.poll_interval)
        msg = f"Export did not finish for {pdf_path.name}"
        raise AutomationError(msg)

    def _close_document(self) -> None:
        menu_name, item_name = self.config.close_menu
        if not self.bridge.click_menu_item(menu_name, item_name):
            msg = "Failed to close the document"
            raise AutomationError(msg)
        time.sleep(self.config.post_action_delay)


class VexyLinesCLI:
    """Fire CLI surface."""

    def export(
        self,
        target: str,
        *,
        verbose: bool = False,
        dry_run: bool = False,
        say_summary: bool = False,
        timeout_multiplier: float = 1.0,
        max_retries: int = 3,
    ) -> dict[str, object]:
        """Export .lines documents found under *target* to PDF.

        Args:
            target: Path to .lines file or directory to search
            verbose: Show detailed progress messages
            dry_run: Preview files without processing
            say_summary: Announce completion via text-to-speech
            timeout_multiplier: Scale all timeouts (2.0 = double all timeouts)
            max_retries: Maximum retry attempts for transient failures (0-10)

        Returns:
            Dictionary with export statistics
        """
        # Validate arguments
        if timeout_multiplier < 0.1 or timeout_multiplier > 10:
            msg = "timeout_multiplier must be between 0.1 and 10"
            raise ValueError(msg)
        if max_retries < 0 or max_retries > 10:
            msg = "max_retries must be between 0 and 10"
            raise ValueError(msg)

        # Create custom config if needed
        config = AutomationConfig(timeout_multiplier=timeout_multiplier, max_retries=max_retries)

        exporter = VexyLinesExporter(config=config, dry_run=dry_run)
        stats = exporter.export(Path(target), verbose=verbose)
        if say_summary:
            speak(stats.human_summary())
        return stats.as_dict()


def main() -> None:
    """Entry-point so `python -m vexy_lines_utils.vexy_lines_utils` works."""

    fire.Fire(VexyLinesCLI)


if __name__ == "__main__":  # pragma: no cover
    main()
