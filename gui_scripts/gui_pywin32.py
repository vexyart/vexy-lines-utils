#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pywin32",
# ]
# ///

import os
import sys
import win32gui
import win32con
import win32api
import commctrl
import shell32

WS_CHILD = win32con.WS_CHILD
WS_VISIBLE = win32con.WS_VISIBLE
WS_BORDER = win32con.WS_BORDER
LVS_REPORT = commctrl.LVS_REPORT
LVS_NOCOLUMNHEADER = commctrl.LVS_NOCOLUMNHEADER
LVS_SHOWSELALWAYS = commctrl.LVS_SHOWSELALWAYS

BS_PUSHBUTTON = win32con.BS_PUSHBUTTON
BS_AUTOCHECKBOX = win32con.BS_AUTOCHECKBOX


class PyWin32App:
    def __init__(self):
        self.items_data = []
        self.image_filter = False
        self.hwnd = None
        self.h_list = None
        self.h_status = None

        win32gui.InitCommonControls()

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.wnd_proc
        wc.lpszClassName = "PyWin32FileList"
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_BTNFACE + 1

        try:
            class_atom = win32gui.RegisterClass(wc)
        except win32gui.error:
            pass

        style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE
        self.hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            "pywin32 File List",
            style,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            600,
            400,
            0,
            0,
            0,
            None,
        )

        win32gui.DragAcceptFiles(self.hwnd, True)

        self.font = win32gui.GetStockObject(win32con.DEFAULT_GUI_FONT)

        self.btn_add = win32gui.CreateWindow(
            "BUTTON", "+", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 10, 10, 30, 25, self.hwnd, 1, 0, None
        )
        self.btn_remove = win32gui.CreateWindow(
            "BUTTON", "−", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 45, 10, 30, 25, self.hwnd, 2, 0, None
        )
        self.btn_clear = win32gui.CreateWindow(
            "BUTTON", "✕", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 80, 10, 30, 25, self.hwnd, 3, 0, None
        )
        self.btn_print = win32gui.CreateWindow(
            "BUTTON", "✓", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 115, 10, 30, 25, self.hwnd, 4, 0, None
        )
        self.chk_images = win32gui.CreateWindow(
            "BUTTON", "Images", WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX, 155, 12, 70, 20, self.hwnd, 5, 0, None
        )

        win32gui.SendMessage(self.btn_add, win32con.WM_SETFONT, self.font, True)
        win32gui.SendMessage(self.btn_remove, win32con.WM_SETFONT, self.font, True)
        win32gui.SendMessage(self.btn_clear, win32con.WM_SETFONT, self.font, True)
        win32gui.SendMessage(self.btn_print, win32con.WM_SETFONT, self.font, True)
        win32gui.SendMessage(self.chk_images, win32con.WM_SETFONT, self.font, True)

        self.h_list = win32gui.CreateWindow(
            "SysListView32",
            "",
            WS_CHILD | WS_VISIBLE | WS_BORDER | LVS_REPORT | LVS_NOCOLUMNHEADER | LVS_SHOWSELALWAYS,
            10,
            45,
            560,
            290,
            self.hwnd,
            100,
            0,
            None,
        )

        lvcolumn = win32gui.LVCOLUMN()
        lvcolumn.mask = commctrl.LVCF_WIDTH | commctrl.LVCF_TEXT
        lvcolumn.cx = 550
        lvcolumn.text = "Files"
        win32gui.SendMessage(self.h_list, commctrl.LVM_INSERTCOLUMN, 0, lvcolumn)

        win32gui.SendMessage(self.h_list, win32con.WM_SETFONT, self.font, True)

        self.h_status = win32gui.CreateWindow(
            "msctls_statusbar32", "", WS_CHILD | WS_VISIBLE, 0, 0, 0, 0, self.hwnd, 200, 0, None
        )
        win32gui.SendMessage(self.h_status, win32con.WM_SETFONT, self.font, True)
        self.update_status()

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0

        elif msg == win32con.WM_SIZE:
            width = win32api.LOWORD(lparam)
            height = win32api.HIWORD(lparam)

            win32gui.MoveWindow(self.h_list, 10, 45, width - 20, height - 80, True)
            win32gui.SendMessage(self.h_status, win32con.WM_SIZE, 0, 0)

            self.update_list_display(width - 20)
            return 0

        elif msg == win32con.WM_COMMAND:
            if lparam == self.btn_add:
                self.on_add()
            elif lparam == self.btn_remove:
                self.on_remove()
            elif lparam == self.btn_clear:
                self.on_clear()
            elif lparam == self.btn_print:
                self.on_print()
            elif lparam == self.chk_images:
                state = win32gui.SendMessage(self.chk_images, win32con.BM_GETCHECK, 0, 0)
                self.image_filter = state == win32con.BST_CHECKED
            return 0

        elif msg == win32con.WM_DROPFILES:
            hdrop = wparam
            count = shell32.DragQueryFile(hdrop, 0xFFFFFFFF)
            paths = []
            for i in range(count):
                path = shell32.DragQueryFile(hdrop, i)
                paths.append(path)
            shell32.DragFinish(hdrop)
            self.add_paths(paths)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

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

        rect = win32gui.GetClientRect(self.h_list)
        self.update_list_display(rect[2])
        self.update_status()

    def on_add(self):
        try:
            import win32ui

            dlg = win32ui.CreateFileDialog(
                1, None, None, win32con.OFN_ALLOWMULTISELECT | win32con.OFN_EXPLORER, "All Files (*.*)|*.*||"
            )
            if dlg.DoModal() == win32con.IDOK:
                paths = dlg.GetPathNames()
                self.add_paths(paths)
        except Exception:
            pass

    def on_remove(self):
        count = win32gui.SendMessage(self.h_list, commctrl.LVM_GETITEMCOUNT, 0, 0)
        selected_indices = []
        for i in range(count):
            state = win32gui.SendMessage(self.h_list, commctrl.LVM_GETITEMSTATE, i, commctrl.LVIS_SELECTED)
            if state & commctrl.LVIS_SELECTED:
                selected_indices.append(i)

        for i in reversed(selected_indices):
            del self.items_data[i]

        rect = win32gui.GetClientRect(self.h_list)
        self.update_list_display(rect[2])
        self.update_status()

    def on_clear(self):
        self.items_data.clear()
        rect = win32gui.GetClientRect(self.h_list)
        self.update_list_display(rect[2])
        self.update_status()

    def on_print(self):
        print("--- Current List ---")
        for p in self.items_data:
            print(p)
        print("--------------------")

    def update_status(self):
        win32gui.SendMessage(self.h_status, win32con.WM_SETTEXT, 0, f"Files in list: {len(self.items_data)}")

    def truncate_middle(self, text, max_pixels):
        hdc = win32gui.GetDC(self.h_list)
        old_font = win32gui.SelectObject(hdc, self.font)

        def get_width(s):
            size = win32gui.GetTextExtentPoint32(hdc, s)
            return size[0]

        if get_width(text) <= max_pixels:
            win32gui.SelectObject(hdc, old_font)
            win32gui.ReleaseDC(self.h_list, hdc)
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

        win32gui.SelectObject(hdc, old_font)
        win32gui.ReleaseDC(self.h_list, hdc)
        return best_text

    def update_list_display(self, list_width):
        win32gui.SendMessage(self.h_list, commctrl.LVM_DELETEALLITEMS, 0, 0)

        lvcolumn = win32gui.LVCOLUMN()
        lvcolumn.mask = commctrl.LVCF_WIDTH
        lvcolumn.cx = max(10, list_width - 25)
        win32gui.SendMessage(self.h_list, commctrl.LVM_SETCOLUMNWIDTH, 0, lvcolumn.cx)

        for idx, path in enumerate(self.items_data):
            display_text = self.truncate_middle(path, lvcolumn.cx)

            item = win32gui.LVITEM()
            item.mask = commctrl.LVIF_TEXT
            item.iItem = idx
            item.iSubItem = 0
            item.text = display_text

            win32gui.SendMessage(self.h_list, commctrl.LVM_INSERTITEM, 0, item)


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This script is intended for Windows only.")
        sys.exit(0)
    app = PyWin32App()
    win32gui.PumpMessages()
