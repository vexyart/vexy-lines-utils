#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "toga",
# ]
# ///

import os
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class TogaFileList(toga.App):
    def startup(self):
        self._items_data = []
        self._image_filter = False

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        controls_box = toga.Box(style=Pack(direction=ROW, padding_bottom=10))

        btn_add = toga.Button("+", on_press=self.on_add, style=Pack(padding_right=5))
        btn_remove = toga.Button("−", on_press=self.on_remove, style=Pack(padding_right=5))
        btn_clear = toga.Button("✕", on_press=self.on_clear, style=Pack(padding_right=5))
        btn_print = toga.Button("✓", on_press=self.on_print, style=Pack(padding_right=15))

        self.chk_images = toga.Switch("Images", on_change=self.on_filter_toggle)

        controls_box.add(btn_add)
        controls_box.add(btn_remove)
        controls_box.add(btn_clear)
        controls_box.add(btn_print)
        controls_box.add(self.chk_images)

        main_box.add(controls_box)

        self.list_view = toga.DetailedList(on_select=self.on_select, style=Pack(flex=1))

        self.status_label = toga.Label("Files in list: 0", style=Pack(padding_top=10))

        main_box.add(self.list_view)
        main_box.add(self.status_label)

        self.main_window = toga.MainWindow(title=self.formal_name, size=(600, 400))
        self.main_window.content = main_box

        self.main_window.on_resize = self.on_resize

        self.main_window.show()

    def on_filter_toggle(self, widget):
        self._image_filter = widget.value

    def add_paths(self, paths):
        valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}

        for path in paths:
            path_str = str(path)
            if not os.path.exists(path_str):
                continue
            if self._image_filter:
                ext = os.path.splitext(path_str)[1].lower()
                if ext not in valid_extensions:
                    continue

            if path_str not in self._items_data:
                self._items_data.append(path_str)

        self.update_list_ui()

    async def on_add(self, widget):
        try:
            paths = await self.main_window.dialog(toga.OpenFileDialog("Select Files", multiple_select=True))
            if paths:
                self.add_paths(paths)
        except ValueError:
            pass

    def on_remove(self, widget):
        selection = self.list_view.selection
        if selection:
            if isinstance(selection, list):
                for item in selection:
                    if item.subtitle in self._items_data:
                        self._items_data.remove(item.subtitle)
            else:
                if selection.subtitle in self._items_data:
                    self._items_data.remove(selection.subtitle)
            self.update_list_ui()

    def on_clear(self, widget):
        self._items_data.clear()
        self.update_list_ui()

    def on_print(self, widget):
        print("--- Current List ---")
        for p in self._items_data:
            print(p)
        print("--------------------")

    def on_select(self, widget, row):
        pass

    def on_resize(self, window, **kwargs):
        self.update_list_ui()

    def truncate_middle(self, text, max_chars):
        if len(text) <= max_chars:
            return text
        side = max(1, (max_chars - 1) // 2)
        return f"{text[:side]}⋮{text[-side:]}"

    def update_list_ui(self):
        width = self.main_window.size[0]
        char_estimate = max(10, int(width / 8))

        formatted_data = []
        for path in self._items_data:
            display_text = self.truncate_middle(path, char_estimate)
            formatted_data.append({"title": display_text, "subtitle": path})

        self.list_view.data = formatted_data
        self.status_label.text = f"Files in list: {len(self._items_data)}"


def main():
    return TogaFileList("Toga File List", "org.beeware.toga.filelist")


if __name__ == "__main__":
    main().main_loop()
