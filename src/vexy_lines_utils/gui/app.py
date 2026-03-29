# this_file: src/vexy_lines_utils/gui/app.py
"""Main GUI application for Vexy Lines style transfer."""

from __future__ import annotations

import base64
import io
import tkinter as tk
import tkinter.font as tkfont
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import filedialog

_CTK_MISSING = "customtkinter is required for the GUI. Install with: pip install customtkinter"
_MENUBAR_MISSING = "CTkMenuBarPlus is required for the GUI. Install with: pip install CTkMenuBarPlus"
_PIL_MISSING = "Pillow is required for the GUI. Install with: pip install Pillow"

try:
    import customtkinter
except ImportError as exc:
    raise ImportError(_CTK_MISSING) from exc

try:
    from CTkMenuBarPlus import CTkMenuBar, CustomDropdownMenu
except ImportError as exc:
    raise ImportError(_MENUBAR_MISSING) from exc

try:
    from PIL import Image
except ImportError as exc:
    raise ImportError(_PIL_MISSING) from exc

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    # tkinterdnd2 is optional -- drag-drop will be disabled if missing
    TkinterDnD = None  # type: ignore[assignment,misc]
    DND_FILES = None

import contextlib

from vexy_lines_utils.gui.widgets import CTkRangeSlider

# ── Constants ──────────────────────────────────────────────────────────

IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
VIDEO_EXTENSIONS: set[str] = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
LINES_EXTENSIONS: set[str] = {".lines"}

# ── Utility helpers ────────────────────────────────────────────────────


def truncate_middle(text: str, max_width: int) -> str:
    """Shorten *text* by replacing the middle with a single ellipsis character."""
    if max_width <= 0:
        return ""
    if len(text) <= max_width:
        return text
    if max_width == 1:
        return "\u22ee"
    keep = max_width - 1
    left = keep // 2
    right = keep - left
    return f"{text[:left]}\u22ee{text[-right:]}" if right else f"{text[:left]}\u22ee"


def truncate_start(text: str, max_chars: int = 20) -> str:
    """Trim leading characters, keeping only the last *max_chars*."""
    if len(text) <= max_chars:
        return text
    return f"\u2026{text[-max_chars:]}"


def extract_preview_from_lines(filepath: str) -> Image.Image | None:
    """Read the base64-encoded preview image from a .lines XML document."""
    try:
        tree = ET.parse(filepath)  # noqa: S314
        root = tree.getroot()
        pd = root.find("PreviewDoc")
        if pd is None:
            return None
        preview_text = pd.text
        if preview_text is None or not preview_text.strip():
            return None
        data = base64.b64decode(preview_text.strip())
        return Image.open(io.BytesIO(data))
    except (ET.ParseError, OSError, ValueError):
        return None


def extract_frame(video_path: str, frame_number: int) -> Image.Image | None:
    """Extract a single frame from *video_path* (1-indexed) via OpenCV."""
    try:
        import cv2  # noqa: PLC0415
    except ImportError:
        return None
    try:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number - 1)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    except Exception:
        return None


def create_placeholder_image(width: int, height: int, text: str) -> Image.Image:
    """Return a plain dark-grey image used as a placeholder."""
    return Image.new("RGB", (width, height), "#1d1f22")


def fit_image_to_box(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale *image* to fit inside *width* x *height*, pasting onto a dark canvas."""
    fitted = image.copy()
    fitted.thumbnail((max(1, width), max(1, height)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (max(1, width), max(1, height)), "#1d1f22")
    canvas.paste(fitted, (0, 0))
    return canvas


# ── App ────────────────────────────────────────────────────────────────

_BASE_CLASSES: tuple[type, ...] = (customtkinter.CTk,)
if TkinterDnD is not None:
    _BASE_CLASSES = (customtkinter.CTk, TkinterDnD.DnDWrapper)


class _AppMeta(type(customtkinter.CTk)):
    """Metaclass that dynamically includes TkinterDnD.DnDWrapper when available."""


class App(*_BASE_CLASSES, metaclass=_AppMeta):  # type: ignore[misc]
    """Style-with-Vexy-Lines GUI application window."""

    def __init__(self) -> None:
        super().__init__()
        if TkinterDnD is not None:
            self.TkdndVersion = TkinterDnD._require(self)

        self.title("Style with Vexy Lines")
        self.geometry("900x700")
        self.minsize(960, 480)

        # -- State: styles ------------------------------------------------
        self._style_paths: dict[str, str | None] = {"start": None, "end": None}
        self._style_labels: dict[str, customtkinter.CTkLabel] = {}
        self._style_previews: dict[str, customtkinter.CTkLabel] = {}
        self._style_default_text: dict[str, str] = {"start": "Style", "end": "End Style"}

        # -- State: images ------------------------------------------------
        self._image_paths: list[str] = []
        self._image_rows: list[customtkinter.CTkLabel] = []
        self._selected_image_index: int | None = None

        # -- State: lines -------------------------------------------------
        self._lines_paths: list[str] = []
        self._lines_rows: list[customtkinter.CTkLabel] = []
        self._selected_lines_index: int | None = None

        # -- State: video -------------------------------------------------
        self._video_path: str = ""
        self._video_total_frames: int = 0
        self._video_has_audio: bool = False
        self._video_range: tuple[int, int] = (1, 1)
        self._syncing_video_controls: bool = False

        # -- State: output ------------------------------------------------
        self._output_path: str = ""
        self.format_var = tk.StringVar(value="SVG")
        self.size_var = tk.StringVar(value="\u2014")
        self.audio_var = tk.BooleanVar(value=True)

        # -- Font metrics for truncation ----------------------------------
        sample_label = customtkinter.CTkLabel(self, text="")
        sample_font = sample_label.cget("font")
        sample_label.destroy()
        if isinstance(sample_font, str):
            self._font = tkfont.nametofont(sample_font)
        else:
            self._font = tkfont.Font(font=sample_font)
        self._last_width: int = 0
        self._resize_job: str | None = None

        self._build_layout()
        self._register_drop_targets()
        self._update_size_dropdown_state()
        self._update_audio_toggle_visibility()
        self._update_styles_panel_state()
        self.bind("<Configure>", self._on_resize)

    # ── Layout construction ────────────────────────────────────────────

    def _build_layout(self) -> None:
        self._build_menu_bar()

        root = customtkinter.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=12, pady=12)
        root.grid_columnconfigure(0, weight=3)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=0)

        self._build_inputs_panel(root)
        self._build_styles_panel(root)
        self._build_outputs_section(root)

    # ── Menu bar ───────────────────────────────────────────────────────

    def _build_menu_bar(self) -> None:
        menu_bar = CTkMenuBar(self)

        # File
        file_btn = menu_bar.add_cascade("File")
        file_menu = CustomDropdownMenu(widget=file_btn)
        file_menu.add_option("Add Lines\u2026", command=self._menu_add_lines)
        file_menu.add_separator()
        file_menu.add_option("Export \u25b6", command=self._do_export)
        file_menu.add_separator()
        file_menu.add_option("Quit", command=self.destroy, accelerator="CmdOrCtrl+Q")

        # Lines
        lines_btn = menu_bar.add_cascade("Lines")
        lines_menu = CustomDropdownMenu(widget=lines_btn)
        lines_menu.add_option("Add Lines\u2026", command=self._menu_add_lines)
        lines_menu.add_option("Remove Selected", command=self._remove_selected_lines)
        lines_menu.add_option("Remove All Lines", command=self._clear_all_lines)

        # Image
        image_btn = menu_bar.add_cascade("Image")
        image_menu = CustomDropdownMenu(widget=image_btn)
        image_menu.add_option("Add Images\u2026", command=self._menu_add_images)
        image_menu.add_option("Remove Selected", command=self._remove_selected_image)
        image_menu.add_option("Remove All Images", command=self._clear_all_images)

        # Video
        video_btn = menu_bar.add_cascade("Video")
        video_menu = CustomDropdownMenu(widget=video_btn)
        video_menu.add_option("Add Video\u2026", command=self._menu_add_video)
        video_menu.add_option("Reset Range", command=self._reset_video_range)
        video_menu.add_option("Remove Video", command=self._clear_video)

        # Style
        style_btn = menu_bar.add_cascade("Style")
        style_menu = CustomDropdownMenu(widget=style_btn)
        style_menu.add_option("Open Style\u2026", command=lambda: self._choose_style_file("start"))
        style_menu.add_option("Open End Style\u2026", command=lambda: self._choose_style_file("end"))
        style_menu.add_option("Reset Styles", command=self._clear_all_styles)

        # Export
        export_btn = menu_bar.add_cascade("Export")
        export_menu = CustomDropdownMenu(widget=export_btn)
        export_menu.add_option("Export \u25b6", command=self._do_export)
        export_menu.add_option("Location\u2026", command=self._choose_output_path)

        fmt_sub = export_menu.add_submenu("Format")
        for fmt in ("SVG", "PNG", "JPG", "MP4", "LINES"):
            fmt_sub.add_option(fmt, command=lambda f=fmt: self._set_format(f))

        size_sub = export_menu.add_submenu("Size")
        for sz in ("1x", "2x", "3x", "4x"):
            size_sub.add_option(sz, command=lambda s=sz: self._set_size(s))

        audio_sub = export_menu.add_submenu("Audio")
        audio_sub.add_option("On", command=lambda: self.audio_var.set(True))
        audio_sub.add_option("Off", command=lambda: self.audio_var.set(False))

    # ── Menu shortcut actions (switch tab then open dialog) ────────────

    def _menu_add_lines(self) -> None:
        """Menu: File > Add Lines / Lines > Add Lines -- switch to Lines tab and open picker."""
        self.inputs_tabview.set("Lines")
        self._on_inputs_tab_changed("Lines")
        self._choose_lines()

    def _menu_add_images(self) -> None:
        """Menu: Image > Add Images -- switch to Images tab and open picker."""
        self.inputs_tabview.set("Image")
        self._on_inputs_tab_changed("Image")
        self._choose_images()

    def _menu_add_video(self) -> None:
        """Menu: Video > Add Video -- switch to Video tab and open picker."""
        self.inputs_tabview.set("Video")
        self._on_inputs_tab_changed("Video")
        self._choose_video()

    # ── Helpers for menu ───────────────────────────────────────────────

    def _reset_video_range(self) -> None:
        if self._video_total_frames > 0:
            self._set_video_range(1, self._video_total_frames)

    def _clear_all_styles(self) -> None:
        self._clear_style_file("start")
        self._clear_style_file("end")

    def _set_format(self, fmt: str) -> None:
        self.format_var.set(fmt)
        self._on_format_change(fmt)

    def _set_size(self, size: str) -> None:
        self.size_var.set(size)

    # ── Left panel: inputs tabview ─────────────────────────────────────

    def _build_inputs_panel(self, parent: customtkinter.CTkFrame) -> None:
        self.inputs_tabview = customtkinter.CTkTabview(parent)
        self.inputs_tabview.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))

        lines_tab = self.inputs_tabview.add("Lines")
        images_tab = self.inputs_tabview.add("Image")
        video_tab = self.inputs_tabview.add("Video")

        self._build_lines_tab(lines_tab)
        self._build_images_tab(images_tab)
        self._build_video_tab(video_tab)
        self._install_tab_change_hook()

    # ── Lines tab ──────────────────────────────────────────────────────

    def _build_lines_tab(self, tab: customtkinter.CTkFrame) -> None:
        """Build the Lines input tab -- file list + preview, mirrors Images tab layout."""
        content = customtkinter.CTkFrame(tab)
        content.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        content.grid_columnconfigure(0, weight=1, uniform="half")
        content.grid_columnconfigure(1, weight=1, uniform="half")
        content.grid_rowconfigure(0, weight=1)

        self.lines_list_frame = customtkinter.CTkScrollableFrame(content)
        self.lines_list_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=(10, 8))

        self.lines_preview_label = customtkinter.CTkLabel(content, text="")
        self.lines_preview_label.grid(row=0, column=1, sticky="nw", padx=(5, 10), pady=(10, 8))
        self._set_label_image(self.lines_preview_label, create_placeholder_image(300, 240, "Lines"), 300, 240)

        # Bottom controls: +/- /clear
        controls = customtkinter.CTkFrame(tab)
        controls.pack(fill="x", expand=False, side="bottom", padx=8, pady=(0, 8))

        customtkinter.CTkButton(controls, text="+", width=36, command=self._choose_lines).pack(
            side="left",
            padx=(8, 0),
            pady=8,
        )
        customtkinter.CTkButton(controls, text="\u2212", width=36, command=self._remove_selected_lines).pack(
            side="left",
            padx=6,
            pady=8,
        )
        customtkinter.CTkButton(controls, text="\u2715", width=36, command=self._clear_all_lines).pack(
            side="right",
            padx=(0, 8),
            pady=8,
        )

    # ── Images tab ─────────────────────────────────────────────────────

    def _build_images_tab(self, tab: customtkinter.CTkFrame) -> None:
        content = customtkinter.CTkFrame(tab)
        content.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        content.grid_columnconfigure(0, weight=1, uniform="half")
        content.grid_columnconfigure(1, weight=1, uniform="half")
        content.grid_rowconfigure(0, weight=1)

        self.images_list_frame = customtkinter.CTkScrollableFrame(content)
        self.images_list_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=(10, 8))

        self.images_preview_label = customtkinter.CTkLabel(content, text="")
        self.images_preview_label.grid(row=0, column=1, sticky="nw", padx=(5, 10), pady=(10, 8))
        self._set_label_image(self.images_preview_label, create_placeholder_image(300, 240, "Images"), 300, 240)

        controls = customtkinter.CTkFrame(tab)
        controls.pack(fill="x", expand=False, side="bottom", padx=8, pady=(0, 8))

        customtkinter.CTkButton(controls, text="+", width=36, command=self._choose_images).pack(
            side="left",
            padx=(8, 0),
            pady=8,
        )
        customtkinter.CTkButton(controls, text="\u2212", width=36, command=self._remove_selected_image).pack(
            side="left",
            padx=6,
            pady=8,
        )
        customtkinter.CTkButton(controls, text="\u2715", width=36, command=self._clear_all_images).pack(
            side="right",
            padx=(0, 8),
            pady=8,
        )

    # ── Video tab ──────────────────────────────────────────────────────

    def _build_video_tab(self, tab: customtkinter.CTkFrame) -> None:
        previews = customtkinter.CTkFrame(tab)
        previews.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        previews.grid_columnconfigure(0, weight=1, uniform="half")
        previews.grid_columnconfigure(1, weight=1, uniform="half")
        previews.grid_rowconfigure(0, weight=1)

        self.video_first_preview = customtkinter.CTkLabel(previews, text="")
        self.video_first_preview.grid(row=0, column=0, sticky="nw", padx=(10, 5), pady=(10, 8))
        self._set_label_image(self.video_first_preview, create_placeholder_image(300, 240, "First"), 300, 240)

        self.video_last_preview = customtkinter.CTkLabel(previews, text="")
        self.video_last_preview.grid(row=0, column=1, sticky="nw", padx=(5, 10), pady=(10, 8))
        self._set_label_image(self.video_last_preview, create_placeholder_image(300, 240, "Last"), 300, 240)

        controls = customtkinter.CTkFrame(tab)
        controls.pack(fill="x", expand=False, side="bottom", padx=8, pady=(0, 8))

        # Range row: [start_entry] <slider> (count_label) [end_entry]
        range_row = customtkinter.CTkFrame(controls, fg_color="transparent")
        range_row.pack(fill="x", padx=8, pady=(8, 4))

        self.video_start_entry = customtkinter.CTkEntry(range_row, width=60)
        self.video_start_entry.pack(side="left")
        self.video_start_entry.insert(0, "1")
        self.video_start_entry.bind("<Return>", self._on_video_entries_submit)
        self.video_start_entry.bind("<FocusOut>", self._on_video_entries_submit)

        self.video_range_slider = CTkRangeSlider(range_row, from_=0, to=1, command=self._on_video_slider_change)
        self.video_range_slider.pack(side="left", fill="x", expand=True, padx=8)
        self.video_range_slider.set([0, 1])

        self.video_count_label = customtkinter.CTkLabel(range_row, text="0 frames")
        self.video_count_label.pack(side="left", padx=(0, 8))

        self.video_end_entry = customtkinter.CTkEntry(range_row, width=60)
        self.video_end_entry.pack(side="left")
        self.video_end_entry.insert(0, "1")
        self.video_end_entry.bind("<Return>", self._on_video_entries_submit)
        self.video_end_entry.bind("<FocusOut>", self._on_video_entries_submit)

        # Video path row: [+] <label> [clear]
        path_row = customtkinter.CTkFrame(controls, fg_color="transparent")
        path_row.pack(fill="x", padx=8, pady=(0, 8))

        customtkinter.CTkButton(path_row, text="+", width=36, command=self._choose_video).pack(side="left")
        self.video_path_label = customtkinter.CTkLabel(path_row, text="Video", anchor="w")
        self.video_path_label.pack(side="left", fill="x", expand=True, padx=8)
        customtkinter.CTkButton(path_row, text="\u2715", width=36, command=self._clear_video).pack(side="right")

    # ── Right panel: styles tabview ────────────────────────────────────

    def _build_styles_panel(self, parent: customtkinter.CTkFrame) -> None:
        self._styles_panel_parent = parent
        self.styles_tabview = customtkinter.CTkTabview(parent)
        self.styles_tabview.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))

        style_tab = self.styles_tabview.add("Style")
        end_style_tab = self.styles_tabview.add("End Style")

        self._build_style_picker(style_tab, "start")
        self._build_style_picker(end_style_tab, "end")

    def _build_style_picker(self, tab: customtkinter.CTkFrame, key: str) -> None:
        content = customtkinter.CTkFrame(tab)
        content.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        preview = customtkinter.CTkLabel(content, text="")
        preview.grid(row=0, column=0, sticky="nw", padx=10, pady=(10, 8))
        self._set_label_image(preview, create_placeholder_image(300, 240, self._style_default_text[key]), 300, 240)
        self._style_previews[key] = preview

        controls = customtkinter.CTkFrame(tab)
        controls.pack(fill="x", expand=False, side="bottom", padx=8, pady=(0, 8))

        customtkinter.CTkButton(
            controls,
            text="+",
            width=36,
            command=lambda k=key: self._choose_style_file(k),
        ).pack(side="left", padx=(8, 0), pady=8)

        path_label = customtkinter.CTkLabel(controls, text=self._style_default_text[key], anchor="w")
        path_label.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        self._style_labels[key] = path_label

        customtkinter.CTkButton(
            controls,
            text="\u2715",
            width=36,
            command=lambda k=key: self._clear_style_file(k),
        ).pack(side="right", padx=(0, 8), pady=8)

    # ── Bottom bar: outputs + export ───────────────────────────────────

    def _build_outputs_section(self, parent: customtkinter.CTkFrame) -> None:
        outputs = customtkinter.CTkFrame(parent)
        outputs.grid(row=1, column=0, columnspan=2, sticky="ew")

        customtkinter.CTkLabel(outputs, text="Export as").pack(side="left", padx=(10, 4), pady=10)

        self.format_menu = customtkinter.CTkOptionMenu(
            outputs,
            values=["SVG", "PNG", "JPG", "MP4", "LINES"],
            variable=self.format_var,
            command=self._on_format_change,
            width=90,
        )
        self.format_menu.pack(side="left", padx=(0, 8), pady=10)

        self.size_menu = customtkinter.CTkOptionMenu(outputs, values=["\u2014"], variable=self.size_var, width=80)
        self.size_menu.pack(side="left", padx=(0, 8), pady=10)

        self.audio_toggle = customtkinter.CTkSwitch(
            outputs,
            text="\u266a",
            variable=self.audio_var,
            onvalue=True,
            offvalue=False,
        )
        self.audio_toggle.pack(side="left", padx=(0, 8), pady=10)

        self.convert_button = customtkinter.CTkButton(
            outputs,
            text="Export \u25b6",
            command=self._do_export,
            width=120,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
        )
        self.convert_button.pack(side="right", padx=(0, 10), pady=10)

    # ── Tab change hook + drop targets ─────────────────────────────────

    def _install_tab_change_hook(self) -> None:
        segmented = getattr(self.inputs_tabview, "_segmented_button", None)
        if segmented is not None:
            original_cmd = segmented.cget("command")

            def _chained_tab_switch(tab_name: str) -> None:
                if callable(original_cmd):
                    original_cmd(tab_name)
                self._on_inputs_tab_changed(tab_name)

            segmented.configure(command=_chained_tab_switch)
        self.after(150, self._poll_active_tab)

    def _poll_active_tab(self) -> None:
        self._update_audio_toggle_visibility()
        self.after(300, self._poll_active_tab)

    def _register_drop_targets(self) -> None:
        if TkinterDnD is None or DND_FILES is None:
            return

        # Lines tab drop targets
        lines_tab = self.inputs_tabview.tab("Lines")
        lines_targets = [lines_tab, self.lines_list_frame, self.lines_preview_label]
        interior = getattr(self.lines_list_frame, "_scrollable_frame", None)
        if interior is not None:
            lines_targets.append(interior)
        for target in lines_targets:
            drop_register = getattr(target, "drop_target_register", None)
            if callable(drop_register):
                drop_register(DND_FILES)
            dnd_bind = getattr(target, "dnd_bind", None)
            if callable(dnd_bind):
                dnd_bind("<<Drop>>", self._on_lines_drop)

        # Images tab drop targets
        images_tab = self.inputs_tabview.tab("Image")
        image_targets = [images_tab, self.images_list_frame, self.images_preview_label]
        interior = getattr(self.images_list_frame, "_scrollable_frame", None)
        if interior is not None:
            image_targets.append(interior)
        for target in image_targets:
            drop_register = getattr(target, "drop_target_register", None)
            if callable(drop_register):
                drop_register(DND_FILES)
            dnd_bind = getattr(target, "dnd_bind", None)
            if callable(dnd_bind):
                dnd_bind("<<Drop>>", self._on_images_drop)

        # Video tab drop targets
        video_tab = self.inputs_tabview.tab("Video")
        for vt in [video_tab, self.video_first_preview, self.video_last_preview, self.video_path_label]:
            drop_register = getattr(vt, "drop_target_register", None)
            if callable(drop_register):
                drop_register(DND_FILES)
            dnd_bind = getattr(vt, "dnd_bind", None)
            if callable(dnd_bind):
                dnd_bind("<<Drop>>", self._on_video_drop)

    # ── Shared helpers ─────────────────────────────────────────────────

    def _set_label_image(self, label: customtkinter.CTkLabel, image: Image.Image, width: int, height: int) -> None:
        fitted = fit_image_to_box(image, width, height)
        ctk_img = customtkinter.CTkImage(light_image=fitted, dark_image=fitted, size=(width, height))
        label.configure(image=ctk_img, text="")
        label._ctk_image = ctk_img

    def _truncate_start_for_width(self, path: str, width_px: int) -> str:
        if self._font.measure(path) <= width_px:
            return path
        avg_char_px = self._font.measure("x") or 7
        max_chars = max(5, width_px // avg_char_px)
        return truncate_start(path, max_chars)

    # ── Resize handling ────────────────────────────────────────────────

    def _on_resize(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        width = self.winfo_width()
        if abs(width - self._last_width) <= 5:
            return
        self._last_width = width
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(70, self._resize_refresh)

    def _resize_refresh(self) -> None:
        self._resize_job = None
        self._refresh_image_list()
        self._refresh_lines_list()
        self._retruncate_labels()

    def _retruncate_labels(self) -> None:
        # Video path label
        if self._video_path:
            width_px = max(10, self.video_path_label.winfo_width() - 10)
            self.video_path_label.configure(text=self._truncate_start_for_width(self._video_path, width_px))
        # Style labels
        for key in ("start", "end"):
            path = self._style_paths.get(key)
            if path:
                label = self._style_labels[key]
                width_px = max(10, label.winfo_width() - 10)
                label.configure(text=self._truncate_start_for_width(path, width_px))

    # ── Styles panel enable/disable ────────────────────────────────────

    def _update_styles_panel_state(self) -> None:
        """Disable (gray out) the styles panel when Lines tab is active."""
        active_tab = self.inputs_tabview.get()
        is_lines_active = active_tab == "Lines"

        # We set the state of the segmented button on the styles tabview
        # and the child widgets to visually disable interaction
        state = "disabled" if is_lines_active else "normal"

        # Disable/enable the styles tabview segmented button
        seg_btn = getattr(self.styles_tabview, "_segmented_button", None)
        if seg_btn is not None:
            with contextlib.suppress(Exception):
                seg_btn.configure(state=state)

        # Disable/enable all child buttons and labels in style tabs
        for key in ("start", "end"):
            tab_name = "Style" if key == "start" else "End Style"
            try:
                tab_widget = self.styles_tabview.tab(tab_name)
            except Exception:
                continue
            self._set_children_state(tab_widget, state)

    def _set_children_state(self, widget: tk.Widget, state: str) -> None:
        """Recursively set the state of child widgets that support it."""
        for child in widget.winfo_children():
            with contextlib.suppress(tk.TclError, ValueError):
                child.configure(state=state)
            self._set_children_state(child, state)

    # ── Style file management ──────────────────────────────────────────

    def _choose_style_file(self, key: str) -> None:
        path = filedialog.askopenfilename(
            title="Choose style",
            filetypes=[("Vexy Lines", "*.lines"), ("All files", "*.*")],
        )
        if not path:
            return
        self._set_style_file(key, path)

    def _set_style_file(self, key: str, path: str) -> None:
        self._style_paths[key] = path
        label = self._style_labels[key]
        width_px = max(10, label.winfo_width() - 10)
        label.configure(text=self._truncate_start_for_width(path, width_px))
        preview = extract_preview_from_lines(path)
        if preview is None:
            preview = create_placeholder_image(300, 240, self._style_default_text[key])
        self._set_label_image(self._style_previews[key], preview, 300, 240)

    def _clear_style_file(self, key: str) -> None:
        self._style_paths[key] = None
        self._style_labels[key].configure(text=self._style_default_text[key])
        self._set_label_image(
            self._style_previews[key],
            create_placeholder_image(300, 240, self._style_default_text[key]),
            300,
            240,
        )

    # ── Lines file management ──────────────────────────────────────────

    def _choose_lines(self) -> None:
        files = filedialog.askopenfilenames(
            title="Choose .lines files",
            filetypes=[("Vexy Lines", "*.lines"), ("All files", "*.*")],
        )
        if files:
            self._add_lines(list(files))

    def _add_lines(self, paths: list[str]) -> None:
        changed = False
        for path in paths:
            ext = Path(path).suffix.lower()
            if ext not in LINES_EXTENSIONS:
                continue
            if path not in self._lines_paths:
                self._lines_paths.append(path)
                changed = True
        if not changed:
            return

        if self._selected_lines_index is None and self._lines_paths:
            self._selected_lines_index = 0
        self._refresh_lines_list()
        self._update_lines_preview()

    def _remove_selected_lines(self) -> None:
        if self._selected_lines_index is None:
            return
        if not (0 <= self._selected_lines_index < len(self._lines_paths)):
            return
        del self._lines_paths[self._selected_lines_index]
        if not self._lines_paths:
            self._selected_lines_index = None
        elif self._selected_lines_index >= len(self._lines_paths):
            self._selected_lines_index = len(self._lines_paths) - 1
        self._refresh_lines_list()
        self._update_lines_preview()

    def _clear_all_lines(self) -> None:
        self._lines_paths.clear()
        self._selected_lines_index = None
        self._refresh_lines_list()
        self._update_lines_preview()

    def _refresh_lines_list(self) -> None:
        for row in self._lines_rows:
            row.destroy()
        self._lines_rows.clear()

        width_px = max(10, self.lines_list_frame.winfo_width() - 24)
        for index, path in enumerate(self._lines_paths):
            row = customtkinter.CTkLabel(
                self.lines_list_frame,
                text=self._truncate_start_for_width(path, width_px),
                anchor="w",
                padx=8,
                corner_radius=6,
                fg_color=("#e9e9e9", "#2a2a2a"),
            )
            row.pack(fill="x", padx=2, pady=2)
            row.bind("<Button-1>", lambda _event, idx=index: self._select_lines_row(idx))
            self._lines_rows.append(row)

        self._update_lines_row_styles()

    def _select_lines_row(self, index: int) -> None:
        if not (0 <= index < len(self._lines_paths)):
            return
        self._selected_lines_index = index
        self._update_lines_row_styles()
        self._update_lines_preview()

    def _update_lines_row_styles(self) -> None:
        for idx, row in enumerate(self._lines_rows):
            if idx == self._selected_lines_index:
                row.configure(fg_color=("#3B8ED0", "#1F6AA5"))
            else:
                row.configure(fg_color=("#e9e9e9", "#2a2a2a"))

    def _update_lines_preview(self) -> None:
        if not self._lines_paths:
            self._set_label_image(self.lines_preview_label, create_placeholder_image(300, 240, "Lines"), 300, 240)
            return

        index = self._selected_lines_index if self._selected_lines_index is not None else 0
        if not (0 <= index < len(self._lines_paths)):
            index = 0
            self._selected_lines_index = 0

        preview = extract_preview_from_lines(self._lines_paths[index])
        if preview is None:
            preview = create_placeholder_image(300, 240, "No preview")
        self._set_label_image(self.lines_preview_label, preview, 300, 240)

    def _on_lines_drop(self, event: tk.Event) -> None:
        data = getattr(event, "data", "")
        if not isinstance(data, str):
            return
        dropped = list(self.tk.splitlist(data))
        self._add_lines(dropped)

    # ── Image file management ──────────────────────────────────────────

    def _choose_images(self) -> None:
        files = filedialog.askopenfilenames(
            title="Choose images",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        if files:
            self._add_images(list(files))

    def _add_images(self, paths: list[str]) -> None:
        changed = False
        for path in paths:
            ext = Path(path).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            if path not in self._image_paths:
                self._image_paths.append(path)
                changed = True
        if not changed:
            return

        if self._selected_image_index is None and self._image_paths:
            self._selected_image_index = 0
        self._refresh_image_list()
        self._update_images_preview()

    def _remove_selected_image(self) -> None:
        if self._selected_image_index is None:
            return
        if not (0 <= self._selected_image_index < len(self._image_paths)):
            return
        del self._image_paths[self._selected_image_index]
        if not self._image_paths:
            self._selected_image_index = None
        elif self._selected_image_index >= len(self._image_paths):
            self._selected_image_index = len(self._image_paths) - 1
        self._refresh_image_list()
        self._update_images_preview()

    def _clear_all_images(self) -> None:
        self._image_paths.clear()
        self._selected_image_index = None
        self._refresh_image_list()
        self._update_images_preview()

    def _refresh_image_list(self) -> None:
        for row in self._image_rows:
            row.destroy()
        self._image_rows.clear()

        width_px = max(10, self.images_list_frame.winfo_width() - 24)
        for index, path in enumerate(self._image_paths):
            row = customtkinter.CTkLabel(
                self.images_list_frame,
                text=self._truncate_start_for_width(path, width_px),
                anchor="w",
                padx=8,
                corner_radius=6,
                fg_color=("#e9e9e9", "#2a2a2a"),
            )
            row.pack(fill="x", padx=2, pady=2)
            row.bind("<Button-1>", lambda _event, idx=index: self._select_image_row(idx))
            self._image_rows.append(row)

        self._update_image_row_styles()

    def _select_image_row(self, index: int) -> None:
        if not (0 <= index < len(self._image_paths)):
            return
        self._selected_image_index = index
        self._update_image_row_styles()
        self._update_images_preview()

    def _update_image_row_styles(self) -> None:
        for idx, row in enumerate(self._image_rows):
            if idx == self._selected_image_index:
                row.configure(fg_color=("#3B8ED0", "#1F6AA5"))
            else:
                row.configure(fg_color=("#e9e9e9", "#2a2a2a"))

    def _update_images_preview(self) -> None:
        if not self._image_paths:
            self._set_label_image(self.images_preview_label, create_placeholder_image(300, 240, "Images"), 300, 240)
            return

        index = self._selected_image_index if self._selected_image_index is not None else 0
        if not (0 <= index < len(self._image_paths)):
            index = 0
            self._selected_image_index = 0

        try:
            image = Image.open(self._image_paths[index]).convert("RGB")
        except (OSError, ValueError):
            image = create_placeholder_image(300, 240, "Unreadable image")
        self._set_label_image(self.images_preview_label, image, 300, 240)

    def _on_images_drop(self, event: tk.Event) -> None:
        data = getattr(event, "data", "")
        if not isinstance(data, str):
            return
        dropped = list(self.tk.splitlist(data))
        self._add_images(dropped)

    # ── Video management ───────────────────────────────────────────────

    def _choose_video(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose video",
            filetypes=[("Videos", "*.mp4 *.mov *.avi *.mkv *.webm"), ("All files", "*.*")],
        )
        if not path:
            return
        self._apply_video_path(path)

    def _on_video_drop(self, event: tk.Event) -> None:
        data = getattr(event, "data", "")
        if not isinstance(data, str):
            return
        dropped = list(self.tk.splitlist(data))
        if not dropped:
            return
        self._apply_video_path(dropped[0])

    def _apply_video_path(self, path: str) -> None:
        ext = Path(path).suffix.lower()
        if ext not in VIDEO_EXTENSIONS:
            return

        total_frames = self._get_video_frame_count(path)
        if total_frames <= 0:
            return

        self._video_path = path
        width_px = max(10, self.video_path_label.winfo_width() - 10)
        self.video_path_label.configure(text=self._truncate_start_for_width(path, width_px))

        self._video_total_frames = total_frames
        self._video_has_audio = True
        self._set_video_range(1, total_frames)
        self._update_audio_toggle_visibility()

    def _get_video_frame_count(self, path: str) -> int:
        try:
            import cv2  # noqa: PLC0415
        except ImportError:
            return 0
        cap = cv2.VideoCapture(path)
        try:
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        finally:
            cap.release()
        return max(0, total)

    def _clear_video(self) -> None:
        self._video_path = ""
        self._video_total_frames = 0
        self._video_has_audio = False
        self._video_range = (1, 1)

        self.video_path_label.configure(text="Video")
        self.video_start_entry.delete(0, "end")
        self.video_start_entry.insert(0, "1")
        self.video_end_entry.delete(0, "end")
        self.video_end_entry.insert(0, "1")
        self.video_count_label.configure(text="0 frames")

        self._syncing_video_controls = True
        self.video_range_slider.configure(from_=0, to=1)
        self.video_range_slider.set([0, 1])
        self._syncing_video_controls = False

        self._set_label_image(self.video_first_preview, create_placeholder_image(300, 240, "First"), 300, 240)
        self._set_label_image(self.video_last_preview, create_placeholder_image(300, 240, "Last"), 300, 240)
        self._update_audio_toggle_visibility()

    def _on_video_slider_change(self, values: tuple[float, float] | list[float] | None) -> None:
        if self._syncing_video_controls or values is None or self._video_total_frames <= 0:
            return
        low = round(values[0])
        high = round(values[1])
        self._set_video_range(low, high)

    def _on_video_entries_submit(self, _event: tk.Event | None) -> None:
        if self._video_total_frames <= 0:
            return
        try:
            low = int(self.video_start_entry.get().strip())
            high = int(self.video_end_entry.get().strip())
        except ValueError:
            low, high = self._video_range
        self._set_video_range(low, high)

    def _set_video_range(self, low: int, high: int) -> None:
        if self._video_total_frames <= 0:
            return

        low = max(1, min(low, self._video_total_frames))
        high = max(1, min(high, self._video_total_frames))
        if low > high:
            low, high = high, low

        self._video_range = (low, high)
        self._syncing_video_controls = True
        self.video_range_slider.configure(from_=1, to=self._video_total_frames)
        self.video_range_slider.set([low, high])
        self._syncing_video_controls = False

        self.video_start_entry.delete(0, "end")
        self.video_start_entry.insert(0, str(low))
        self.video_end_entry.delete(0, "end")
        self.video_end_entry.insert(0, str(high))

        count = high - low + 1
        self.video_count_label.configure(text=f"{count} frames")
        self._update_video_previews()
        self._update_audio_toggle_visibility()

    def _update_video_previews(self) -> None:
        if not self._video_path or self._video_total_frames <= 0:
            self._set_label_image(self.video_first_preview, create_placeholder_image(300, 240, "First"), 300, 240)
            self._set_label_image(self.video_last_preview, create_placeholder_image(300, 240, "Last"), 300, 240)
            return

        low, high = self._video_range
        first_frame = extract_frame(self._video_path, low)
        last_frame = extract_frame(self._video_path, high)
        if first_frame is None:
            first_frame = create_placeholder_image(300, 240, "First")
        if last_frame is None:
            last_frame = create_placeholder_image(300, 240, "Last")

        self._set_label_image(self.video_first_preview, first_frame, 300, 240)
        self._set_label_image(self.video_last_preview, last_frame, 300, 240)

    # ── Format / size / audio state ────────────────────────────────────

    def _on_format_change(self, _value: str) -> None:
        self._update_size_dropdown_state()
        self._update_audio_toggle_visibility()

    def _update_size_dropdown_state(self) -> None:
        format_value = self.format_var.get()
        if format_value in ("SVG", "LINES"):
            self.size_var.set("\u2014")
            self.size_menu.configure(values=["\u2014"], state="disabled")
            return

        valid = ["1x", "2x", "3x", "4x"]
        current = self.size_var.get()
        self.size_menu.configure(values=valid, state="normal")
        if current in valid:
            self.size_var.set(current)
        else:
            self.size_var.set("1x")

    def _update_audio_toggle_visibility(self) -> None:
        active_video_tab = self.inputs_tabview.get() == "Video"
        video_loaded = bool(self._video_path and self._video_total_frames > 0)
        format_ok = self.format_var.get() == "MP4"
        full_video = self._video_total_frames > 0 and self._video_range == (1, self._video_total_frames)
        should_show = active_video_tab and video_loaded and self._video_has_audio and format_ok and full_video

        if should_show:
            self.audio_toggle.grid()
            return
        self.audio_toggle.grid_remove()

    # ── Export ─────────────────────────────────────────────────────────

    def _do_export(self) -> None:
        fmt = self.format_var.get()
        if fmt == "MP4":
            selected = filedialog.asksaveasfilename(
                title="Export as MP4",
                defaultextension=".mp4",
                filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")],
            )
        else:
            selected = filedialog.askdirectory(title=f"Export {fmt} to folder")
        if not selected:
            return
        self._output_path = selected
        # TODO: trigger actual export pipeline here

    def _choose_output_path(self) -> None:
        self._do_export()

    # ── Tab change callback ────────────────────────────────────────────

    def _on_inputs_tab_changed(self, _tab_name: str) -> None:
        self._update_audio_toggle_visibility()
        self._update_styles_panel_state()


# ── Launch function ────────────────────────────────────────────────────


def launch() -> None:
    """Launch the Vexy Lines style transfer GUI."""
    customtkinter.set_appearance_mode("dark")
    app = App()
    app.lift()
    app.attributes("-topmost", True)
    app.after(100, lambda: app.attributes("-topmost", False))
    app.mainloop()
