#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tkinterdnd2",
# ]
# ///

import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import font as tkfont
from tkinterdnd2 import TkinterDnD, DND_FILES


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tkinter File List")
        self.geometry("600x400")

        self.items_data = []

        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(controls_frame, text="+", width=3, command=self.on_add).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="−", width=3, command=self.on_remove).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="✕", width=3, command=self.on_clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="✓", width=3, command=self.on_print).pack(side=tk.LEFT, padx=2)

        self.chk_images_var = tk.BooleanVar()
        ttk.Checkbutton(controls_frame, text="Images", variable=self.chk_images_var).pack(side=tk.LEFT, padx=10)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.status_var = tk.StringVar()
        self.status_var.set("Files in list: 0")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind("<<Drop>>", self.on_drop)
        self.bind("<Configure>", self.on_resize)

        self.font = tkfont.nametofont(self.listbox.cget("font"))
        self._last_width = 0

    def add_paths(self, paths):
        valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
        image_filter = self.chk_images_var.get()

        for path in paths:
            if not os.path.exists(path):
                continue
            if image_filter:
                ext = os.path.splitext(path)[1].lower()
                if ext not in valid_extensions:
                    continue

            if path not in self.items_data:
                self.items_data.append(path)

        self.update_listbox()

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        self.listbox.update_idletasks()
        list_width_pixels = self.listbox.winfo_width()

        if list_width_pixels <= 10:
            for p in self.items_data:
                self.listbox.insert(tk.END, p)
        else:
            padding = 10
            target_width = max(10, list_width_pixels - padding)
            for path in self.items_data:
                self.listbox.insert(tk.END, self.truncate_middle(path, target_width))

        self.status_var.set(f"Files in list: {len(self.items_data)}")

    def truncate_middle(self, text, max_pixels):
        if self.font.measure(text) <= max_pixels:
            return text

        ellipsis = "⋮"
        ellipsis_width = self.font.measure(ellipsis)

        low = 0
        high = len(text) // 2
        best_text = ellipsis

        while low <= high:
            mid = (low + high) // 2
            test_text = f"{text[:mid]}{ellipsis}{text[-mid:]}" if mid > 0 else ellipsis
            if self.font.measure(test_text) <= max_pixels:
                best_text = test_text
                low = mid + 1
            else:
                high = mid - 1

        return best_text

    def on_resize(self, event):
        if event.widget == self:
            current_width = self.winfo_width()
            if abs(current_width - self._last_width) > 5:
                self._last_width = current_width
                self.update_listbox()

    def on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        self.add_paths(paths)

    def on_add(self):
        paths = filedialog.askopenfilenames(title="Select Files")
        if paths:
            self.add_paths(paths)

    def on_remove(self):
        selection = self.listbox.curselection()
        for i in reversed(selection):
            del self.items_data[i]
        self.update_listbox()

    def on_clear(self):
        self.items_data.clear()
        self.update_listbox()

    def on_print(self):
        print("--- Current List ---")
        for p in self.items_data:
            print(p)
        print("--------------------")


if __name__ == "__main__":
    app = App()
    app.mainloop()
