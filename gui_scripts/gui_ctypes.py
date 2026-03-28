#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
# ]
# ///

import os
import sys
import ctypes
import ctypes.wintypes as w

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
gdi32 = ctypes.windll.gdi32

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000
WS_BORDER = 0x00800000
BS_PUSHBUTTON = 0x00000000
BS_AUTOCHECKBOX = 0x00000003
WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_COMMAND = 0x0111
WM_SETFONT = 0x0030
WM_DROPFILES = 0x0233
DEFAULT_GUI_FONT = 17


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", w.UINT),
        ("lpfnWndProc", ctypes.WINFUNCTYPE(w.LPARAM, w.HWND, w.UINT, w.WPARAM, w.LPARAM)),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", w.HINSTANCE),
        ("hIcon", w.HICON),
        ("hCursor", w.HANDLE),
        ("hbrBackground", w.HBRUSH),
        ("lpszMenuName", w.LPCWSTR),
        ("lpszClassName", w.LPCWSTR),
    ]


class CtypesApp:
    def __init__(self):
        self.items_data = []
        self.image_filter = False

        self.wnd_proc_type = ctypes.WINFUNCTYPE(w.LPARAM, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        self.wnd_proc_func = self.wnd_proc_type(self.wnd_proc)

        wc = WNDCLASS()
        wc.lpfnWndProc = self.wnd_proc_func
        wc.lpszClassName = "CtypesFileList"
        wc.hCursor = user32.LoadCursorW(0, 32512)
        wc.hbrBackground = 16

        user32.RegisterClassW(ctypes.byref(wc))

        self.hwnd = user32.CreateWindowExW(
            0,
            "CtypesFileList",
            "ctypes File List",
            WS_OVERLAPPEDWINDOW | WS_VISIBLE,
            w.CW_USEDEFAULT,
            w.CW_USEDEFAULT,
            600,
            400,
            0,
            0,
            0,
            None,
        )

        shell32.DragAcceptFiles(self.hwnd, True)

        self.font = gdi32.GetStockObject(DEFAULT_GUI_FONT)

        self.btn_add = user32.CreateWindowExW(
            0, "BUTTON", "+", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 10, 10, 30, 25, self.hwnd, 1, 0, None
        )
        self.btn_remove = user32.CreateWindowExW(
            0, "BUTTON", "−", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 45, 10, 30, 25, self.hwnd, 2, 0, None
        )
        self.btn_clear = user32.CreateWindowExW(
            0, "BUTTON", "✕", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 80, 10, 30, 25, self.hwnd, 3, 0, None
        )
        self.btn_print = user32.CreateWindowExW(
            0, "BUTTON", "✓", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 115, 10, 30, 25, self.hwnd, 4, 0, None
        )
        self.chk_images = user32.CreateWindowExW(
            0, "BUTTON", "Images", WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX, 155, 12, 70, 20, self.hwnd, 5, 0, None
        )

        user32.SendMessageW(self.btn_add, WM_SETFONT, self.font, True)
        user32.SendMessageW(self.btn_remove, WM_SETFONT, self.font, True)
        user32.SendMessageW(self.btn_clear, WM_SETFONT, self.font, True)
        user32.SendMessageW(self.btn_print, WM_SETFONT, self.font, True)
        user32.SendMessageW(self.chk_images, WM_SETFONT, self.font, True)

        self.h_list = user32.CreateWindowExW(
            0,
            "LISTBOX",
            "",
            WS_CHILD | WS_VISIBLE | WS_BORDER | 0x0002 | 0x0800,
            10,
            45,
            560,
            290,
            self.hwnd,
            100,
            0,
            None,
        )
        user32.SendMessageW(self.h_list, WM_SETFONT, self.font, True)

        self.h_status = user32.CreateWindowExW(
            0, "STATIC", "Files in list: 0", WS_CHILD | WS_VISIBLE, 10, 340, 580, 20, self.hwnd, 200, 0, None
        )
        user32.SendMessageW(self.h_status, WM_SETFONT, self.font, True)

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0

        elif msg == WM_SIZE:
            width = lparam & 0xFFFF
            height = (lparam >> 16) & 0xFFFF
            user32.MoveWindow(self.h_list, 10, 45, width - 20, height - 80, True)
            user32.MoveWindow(self.h_status, 10, height - 25, width - 20, 20, True)
            self.update_list_display(width - 20)
            return 0

        elif msg == WM_COMMAND:
            ctrl_id = wparam & 0xFFFF
            if ctrl_id == 1:
                pass
            elif ctrl_id == 2:
                self.on_remove()
            elif ctrl_id == 3:
                self.on_clear()
            elif ctrl_id == 4:
                self.on_print()
            elif ctrl_id == 5:
                state = user32.SendMessageW(self.chk_images, 0x00F0, 0, 0)
                self.image_filter = state == 1
            return 0

        elif msg == WM_DROPFILES:
            hdrop = wparam
            count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            paths = []
            buf = ctypes.create_unicode_buffer(260)
            for i in range(count):
                shell32.DragQueryFileW(hdrop, i, buf, 260)
                paths.append(buf.value)
            shell32.DragFinish(hdrop)
            self.add_paths(paths)
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def add_paths(self, paths):
        valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
        for path in paths:
            if not os.path.exists(path):
                continue
            if self.image_filter:
                ext = os.path.splitext(path)[1].lower()
                if ext not in valid_extensions:
                    continue
            if path not in self.items_data:
                self.items_data.append(path)

        rect = w.RECT()
        user32.GetClientRect(self.h_list, ctypes.byref(rect))
        self.update_list_display(rect.right)
        self.update_status()

    def on_remove(self):
        LB_GETSELCOUNT = 0x0190
        LB_GETSELITEMS = 0x0191

        count = user32.SendMessageW(self.h_list, LB_GETSELCOUNT, 0, 0)
        if count > 0:
            buf = (ctypes.c_int * count)()
            user32.SendMessageW(self.h_list, LB_GETSELITEMS, count, ctypes.cast(buf, w.LPARAM))

            for i in reversed(list(buf)):
                del self.items_data[i]

            rect = w.RECT()
            user32.GetClientRect(self.h_list, ctypes.byref(rect))
            self.update_list_display(rect.right)
            self.update_status()

    def on_clear(self):
        self.items_data.clear()
        rect = w.RECT()
        user32.GetClientRect(self.h_list, ctypes.byref(rect))
        self.update_list_display(rect.right)
        self.update_status()

    def on_print(self):
        print("--- Current List ---")
        for p in self.items_data:
            print(p)
        print("--------------------")

    def update_status(self):
        user32.SetWindowTextW(self.h_status, f"Files in list: {len(self.items_data)}")

    def truncate_middle(self, text, max_pixels):
        class SIZE(ctypes.Structure):
            _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]

        hdc = user32.GetDC(self.h_list)
        old_font = gdi32.SelectObject(hdc, self.font)

        def get_width(s):
            size = SIZE()
            gdi32.GetTextExtentPoint32W(hdc, s, len(s), ctypes.byref(size))
            return size.cx

        if get_width(text) <= max_pixels:
            gdi32.SelectObject(hdc, old_font)
            user32.ReleaseDC(self.h_list, hdc)
            return text

        ellipsis = "⋮"

        low = 0
        high = len(text) // 2
        best_text = ellipsis

        while low <= high:
            mid = (low + high) // 2
            test_text = f"{text[:mid]}{ellipsis}{text[-mid:]}" if mid > 0 else ellipsis
            if get_width(test_text) <= max_pixels:
                best_text = test_text
                low = mid + 1
            else:
                high = mid - 1

        gdi32.SelectObject(hdc, old_font)
        user32.ReleaseDC(self.h_list, hdc)
        return best_text

    def update_list_display(self, list_width):
        user32.SendMessageW(self.h_list, 0x0184, 0, 0)

        for path in self.items_data:
            display_text = self.truncate_middle(path, max(10, list_width - 25))
            user32.SendMessageW(self.h_list, 0x0180, 0, ctypes.c_wchar_p(display_text))


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This script is intended for Windows only.")
        sys.exit(0)

    app = CtypesApp()

    msg = w.MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
