#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "dearpygui",
# ]
# ///

import os
import dearpygui.dearpygui as dpg

items_data = []
image_filter_enabled = False


def update_status():
    dpg.set_value("status_text", f"Files in list: {len(items_data)}")


def truncate_middle(text, max_chars):
    if len(text) <= max_chars:
        return text
    side = max(1, (max_chars - 1) // 2)
    return f"{text[:side]}⋮{text[-side:]}"


def redraw_list():
    dpg.delete_item("listbox_container", children_only=True)

    window_width = dpg.get_item_width("main_window")
    if window_width <= 0:
        window_width = dpg.get_viewport_width()

    char_estimate = max(10, int(window_width / 8))

    for idx, path in enumerate(items_data):
        display_text = truncate_middle(path, char_estimate)
        dpg.add_selectable(label=display_text, user_data=path, parent="listbox_container")

    update_status()


def on_resize():
    redraw_list()


def add_paths(paths):
    valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
    global image_filter_enabled

    for path in paths:
        if not os.path.exists(path):
            continue
        if image_filter_enabled:
            ext = os.path.splitext(path)[1].lower()
            if ext not in valid_extensions:
                continue

        if path not in items_data:
            items_data.append(path)

    redraw_list()


def drop_callback(sender, app_data):
    if "selections" in app_data:
        paths = list(app_data["selections"].values())
        add_paths(paths)


def on_add_btn(sender, app_data):
    dpg.show_item("file_dialog_id")


def file_dialog_callback(sender, app_data):
    if "selections" in app_data:
        paths = list(app_data["selections"].values())
        add_paths(paths)


def on_remove_btn(sender, app_data):
    selected = []
    children = dpg.get_item_children("listbox_container", 1)
    if children:
        for child in children:
            if dpg.get_value(child):
                path = dpg.get_item_user_data(child)
                selected.append(path)

    for path in selected:
        if path in items_data:
            items_data.remove(path)

    redraw_list()


def on_clear_btn(sender, app_data):
    items_data.clear()
    redraw_list()


def on_print_btn(sender, app_data):
    print("--- Current List ---")
    for p in items_data:
        print(p)
    print("--------------------")


def on_filter_change(sender, app_data):
    global image_filter_enabled
    image_filter_enabled = app_data


dpg.create_context()
dpg.create_viewport(title="Dear PyGui File List", width=600, height=400)

dpg.add_file_dialog(
    directory_selector=False, show=False, callback=file_dialog_callback, id="file_dialog_id", width=500, height=400
)

with dpg.window(tag="main_window"):
    with dpg.group(horizontal=True):
        dpg.add_button(label="+", callback=on_add_btn)
        dpg.add_button(label="−", callback=on_remove_btn)
        dpg.add_button(label="✕", callback=on_clear_btn)
        dpg.add_button(label="✓", callback=on_print_btn)
        dpg.add_checkbox(label="Images", callback=on_filter_change)

    with dpg.child_window(tag="listbox_container", height=-30):
        pass

    dpg.add_text("Files in list: 0", tag="status_text")

dpg.set_viewport_resize_callback(on_resize)
dpg.set_primary_window("main_window", True)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
