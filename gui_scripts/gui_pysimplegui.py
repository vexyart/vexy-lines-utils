#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "PySimpleGUI",
# ]
# ///

import os
import PySimpleGUI as sg
import tkinter.font as tkfont

sg.theme("LightGrey1")

layout = [
    [
        sg.Button("+", key="-ADD-"),
        sg.Button("−", key="-REMOVE-"),
        sg.Button("✕", key="-CLEAR-"),
        sg.Button("✓", key="-PRINT-"),
        sg.Checkbox("Images", key="-IMAGES-"),
    ],
    [
        sg.Listbox(
            values=[],
            select_mode=sg.LISTBOX_SELECT_MODE_EXTENDED,
            size=(60, 20),
            key="-LIST-",
            enable_events=True,
            expand_x=True,
            expand_y=True,
        )
    ],
    [sg.StatusBar("Files in list: 0", key="-STATUS-")],
]

window = sg.Window("PySimpleGUI File List", layout, resizable=True, finalize=True)
window["-LIST-"].Widget.master.dnd_accept = True

items_data = []


def get_font():
    return tkfont.nametofont(window["-LIST-"].Widget.cget("font"))


def truncate_middle(text, max_pixels, font):
    if font.measure(text) <= max_pixels:
        return text

    ellipsis = "⋮"

    low = 0
    high = len(text) // 2
    best_text = ellipsis

    while low <= high:
        mid = (low + high) // 2
        test_text = f"{text[:mid]}{ellipsis}{text[-mid:]}" if mid > 0 else ellipsis
        if font.measure(test_text) <= max_pixels:
            best_text = test_text
            low = mid + 1
        else:
            high = mid - 1

    return best_text


def update_list(window_inst, items, font):
    listbox = window_inst["-LIST-"].Widget
    listbox.update_idletasks()
    list_width_pixels = listbox.winfo_width()

    padding = 10
    target_width = max(10, list_width_pixels - padding)

    display_items = [truncate_middle(p, target_width, font) for p in items]
    window_inst["-LIST-"].update(values=display_items)
    window_inst["-STATUS-"].update(f"Files in list: {len(items)}")


def add_paths(paths, image_filter):
    valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
    for path in paths:
        if not os.path.exists(path):
            continue
        if image_filter:
            ext = os.path.splitext(path)[1].lower()
            if ext not in valid_extensions:
                continue
        if path not in items_data:
            items_data.append(path)


window.bind("<Configure>", "-RESIZE-")
last_width = 0
font = get_font()

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break

    if event == "-ADD-":
        paths = sg.popup_get_file("Select files", multiple_files=True, no_window=True)
        if paths:
            if isinstance(paths, str):
                paths = paths.split(";")
            add_paths(paths, values["-IMAGES-"])
            update_list(window, items_data, font)

    elif event == "-REMOVE-":
        selected = window["-LIST-"].Widget.curselection()
        for i in reversed(selected):
            del items_data[i]
        update_list(window, items_data, font)

    elif event == "-CLEAR-":
        items_data.clear()
        update_list(window, items_data, font)

    elif event == "-PRINT-":
        print("--- Current List ---")
        for p in items_data:
            print(p)
        print("--------------------")

    elif event == "-RESIZE-":
        current_width = window.size[0]
        if abs(current_width - last_width) > 5:
            last_width = current_width
            update_list(window, items_data, font)

window.close()
