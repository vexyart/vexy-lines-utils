#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["mac-pyxa", "pyautogui-ng", "pyperclip", "fire", "loguru", "tenacity"]
# ///
# this_file: vlb.py

import subprocess
import time
from pathlib import Path
import pyautogui
import pyperclip
import PyXA
import fire
from loguru import logger
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_result

APP_NAME = "Vexy Lines"
POLL_INTERVAL = 0.1
MAX_WAIT_TIME = 10.0
FILE_OPEN_WAIT_TIME = 20.0
SAVE_DIALOG_WAIT_TIME = 20.0
EXTRA_WAIT = 1.0


def say(text: str):
    subprocess.run(["say", text], check=True)


def get_app_windows(app: PyXA.Application) -> list:
    try:
        return list(app.windows())  # type: ignore
    except Exception:
        return []


def get_window_titles(app: PyXA.Application) -> list[str]:
    try:
        titles = []
        for window in get_app_windows(app):
            try:
                title = str(window.title).strip()
                if title:
                    titles.append(title)
            except Exception:
                pass
        return titles
    except Exception:
        return []


@retry(
    stop=stop_after_delay(MAX_WAIT_TIME),
    wait=wait_fixed(POLL_INTERVAL),
    retry=retry_if_result(lambda x: not x),
)
def wait_for_window_with_title(app: PyXA.Application, title: str) -> bool:
    return title in get_window_titles(app)


@retry(
    stop=stop_after_delay(MAX_WAIT_TIME),
    wait=wait_fixed(POLL_INTERVAL),
    retry=retry_if_result(lambda x: not x),
)
def wait_for_window_title_gone(app: PyXA.Application, title: str) -> bool:
    return title not in get_window_titles(app)


@retry(
    stop=stop_after_delay(15.0),
    wait=wait_fixed(POLL_INTERVAL),
    retry=retry_if_result(lambda x: not x),
)
def wait_for_app_ready(app: PyXA.Application) -> bool:
    return len(get_app_windows(app)) > 0


@retry(
    stop=stop_after_delay(FILE_OPEN_WAIT_TIME),
    wait=wait_fixed(POLL_INTERVAL),
    retry=retry_if_result(lambda x: not x),
)
def wait_for_file_to_open(app: PyXA.Application, file_name: str) -> bool:
    try:
        titles = get_window_titles(app)
        basename = Path(file_name).stem
        return any(file_name in title or basename in title for title in titles)
    except Exception:
        return False


@retry(
    stop=stop_after_delay(SAVE_DIALOG_WAIT_TIME),
    wait=wait_fixed(POLL_INTERVAL),
    retry=retry_if_result(lambda x: not x),
)
def wait_for_save_dialog(app: PyXA.Application) -> bool:
    return "Save" in get_window_titles(app)


@retry(
    stop=stop_after_delay(5.0),
    wait=wait_fixed(0.2),
    retry=retry_if_result(lambda x: not x),
)
def click_menu_item(app: PyXA.Application, menu_name: str, item_name: str) -> bool:
    try:
        menu_bar = app.menu_bars()[0]  # type: ignore
        menu_bar_item = menu_bar.menu_bar_items().by_name(menu_name)
        if menu_bar_item:
            menu = menu_bar_item.menus()[0]
            menu_item = menu.menu_items().by_name(item_name)
            if menu_item:
                menu_item.click()
                return True
        return False
    except Exception:
        return False


def open_file_in_app(app: PyXA.Application, file_path: Path) -> bool:
    try:
        result = subprocess.run(
            ["open", "-a", APP_NAME, str(file_path.absolute())],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False
        return wait_for_file_to_open(app, file_path.name)
    except Exception:
        return False


@retry(
    stop=stop_after_delay(2.0),
    wait=wait_fixed(0.1),
    retry=retry_if_result(lambda x: not x),
)
def verify_exported_file(pdf_path: Path) -> bool:
    return pdf_path.exists() and pdf_path.stat().st_size > 0


def export_file(app: PyXA.Application, file_path: Path) -> bool:
    logger.info(f"Processing: {file_path}")
    pdf_path = file_path.with_suffix(".pdf")

    # Remove existing PDF
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception:
            return False

    # Open file
    if not open_file_in_app(app, file_path):
        return False

    time.sleep(EXTRA_WAIT + 0.5)

    # Export
    if not click_menu_item(app, "File", "Export..."):
        return False

    try:
        wait_for_window_with_title(app, "Export")
    except Exception:
        return False

    pyautogui.press("enter")

    try:
        wait_for_save_dialog(app)
    except Exception:
        return False

    # Navigate to folder
    folder_path = str(file_path.parent.absolute())
    time.sleep(EXTRA_WAIT + 0.3)
    pyautogui.hotkey("command", "shift", "g")
    time.sleep(EXTRA_WAIT + 0.3)
    pyperclip.copy(folder_path)
    pyautogui.hotkey("command", "v")
    time.sleep(EXTRA_WAIT + 0.2)
    pyautogui.press("enter")
    time.sleep(EXTRA_WAIT + 0.5)

    # Enter filename
    pdf_filename = file_path.stem + ".pdf"
    pyperclip.copy(pdf_filename)
    pyautogui.hotkey("command", "a")
    time.sleep(EXTRA_WAIT + 0.1)
    pyautogui.hotkey("command", "v")
    time.sleep(EXTRA_WAIT + 0.2)

    # Save
    pyautogui.press("enter")
    time.sleep(EXTRA_WAIT + 0.5)
    pyautogui.press("enter")  # Handle overwrite dialog

    # Wait for save completion
    try:
        wait_for_window_title_gone(app, "Save")
    except Exception:
        return False

    # Verify file
    try:
        verify_exported_file(pdf_path)
    except Exception:
        return False

    # Close file
    time.sleep(EXTRA_WAIT + 0.5)
    click_menu_item(app, "File", "Close")
    time.sleep(EXTRA_WAIT + 0.3)

    logger.success(f"Exported: {pdf_path.name}")
    return True


def find_lines_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix == ".lines":
        return [path]
    elif path.is_dir():
        return sorted(path.rglob("*.lines"))
    else:
        return []


def main(path: str, verbose: bool = False):
    logger.remove()
    if verbose:
        logger.add(lambda msg: print(msg, end=""), level="DEBUG", colorize=True)
    else:
        logger.add(lambda msg: print(msg, end=""), level="INFO", colorize=True)

    path_obj = Path(path).expanduser().resolve()

    if not path_obj.exists():
        logger.error(f"Path does not exist: {path}")
        return

    lines_files = find_lines_files(path_obj)

    if not lines_files:
        logger.warning(f"No .lines files found in: {path}")
        return

    logger.info(f"Found {len(lines_files)} .lines file(s)")

    try:
        app = PyXA.Application(APP_NAME)
        app.launch()  # type: ignore
        logger.info(f"Launched {APP_NAME}")
    except Exception as e:
        logger.error(f"Failed to launch {APP_NAME}: {e}")
        return

    try:
        wait_for_app_ready(app)
    except Exception:
        logger.error(f"{APP_NAME} did not start properly")
        return

    success_count = 0
    total = len(lines_files)

    for i, file_path in enumerate(lines_files):
        logger.info(f"Processing file {i + 1}/{total}")
        try:
            app.activate()  # type: ignore
            time.sleep(EXTRA_WAIT + 0.5)

            if export_file(app, file_path):
                success_count += 1
            else:
                logger.error(f"Failed to export: {file_path}")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    msg = f"Exported {success_count}/{total} files successfully"
    say(msg)
    logger.success(f"\n{msg}")


if __name__ == "__main__":
    fire.Fire(main)
