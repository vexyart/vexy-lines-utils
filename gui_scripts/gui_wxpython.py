#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "wxPython",
# ]
# ///

import os
import wx


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, obj):
        wx.FileDropTarget.__init__(self)
        self.obj = obj

    def OnDropFiles(self, x, y, filenames):
        self.obj.handle_dropped_files(filenames)
        return True


class TruncatedListCtrl(wx.ListCtrl):
    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
    ):
        super().__init__(parent, id, pos, size, style)
        self.InsertColumn(0, "File Path")
        self._items_data = []
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def add_paths(self, paths, image_filter=False):
        valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}

        for path in paths:
            if not os.path.exists(path):
                continue
            if image_filter:
                ext = os.path.splitext(path)[1].lower()
                if ext not in valid_extensions:
                    continue

            if path not in self._items_data:
                self._items_data.append(path)

        self.update_truncation()

    def remove_selected(self):
        item = -1
        selected = []
        while True:
            item = self.GetNextItem(item, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if item == -1:
                break
            selected.append(item)

        for i in reversed(selected):
            del self._items_data[i]

        self.update_truncation()

    def clear_all(self):
        self._items_data.clear()
        self.update_truncation()

    def update_truncation(self):
        self.DeleteAllItems()
        available_width = max(10, self.GetClientSize().width - 10)
        self.SetColumnWidth(0, available_width)

        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())

        for idx, full_path in enumerate(self._items_data):
            truncated = self.truncate_middle(dc, full_path, available_width)
            self.InsertItem(idx, truncated)

    def truncate_middle(self, dc, text, max_pixels):
        width, _, _, _ = dc.GetFullMultiLineTextExtent(text)
        if width <= max_pixels:
            return text

        ellipsis = "⋮"
        ellipsis_width, _, _, _ = dc.GetFullMultiLineTextExtent(ellipsis)

        low = 0
        high = len(text) // 2
        best_text = ellipsis

        while low <= high:
            mid = (low + high) // 2
            test_text = f"{text[:mid]}{ellipsis}{text[-mid:]}" if mid > 0 else ellipsis
            w, _, _, _ = dc.GetFullMultiLineTextExtent(test_text)
            if w <= max_pixels:
                best_text = test_text
                low = mid + 1
            else:
                high = mid - 1

        return best_text

    def OnSize(self, event):
        self.update_truncation()
        event.Skip()


class MainFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(MainFrame, self).__init__(*args, **kw)

        self.SetTitle("wxPython File List")
        self.SetSize((600, 400))

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox_controls = wx.BoxSizer(wx.HORIZONTAL)

        btn_add = wx.Button(panel, label="+", size=(30, -1))
        btn_remove = wx.Button(panel, label="−", size=(30, -1))
        btn_clear = wx.Button(panel, label="✕", size=(30, -1))
        btn_print = wx.Button(panel, label="✓", size=(30, -1))

        self.chk_images = wx.CheckBox(panel, label="Images")

        hbox_controls.Add(btn_add, flag=wx.RIGHT, border=5)
        hbox_controls.Add(btn_remove, flag=wx.RIGHT, border=5)
        hbox_controls.Add(btn_clear, flag=wx.RIGHT, border=5)
        hbox_controls.Add(btn_print, flag=wx.RIGHT, border=15)
        hbox_controls.Add(self.chk_images, flag=wx.ALIGN_CENTER_VERTICAL)

        vbox.Add(hbox_controls, flag=wx.EXPAND | wx.ALL, border=10)

        self.list_ctrl = TruncatedListCtrl(panel, style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.BORDER_SUNKEN)

        drop_target = FileDropTarget(self)
        self.list_ctrl.SetDropTarget(drop_target)

        vbox.Add(self.list_ctrl, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)

        self.statusbar = self.CreateStatusBar()
        self.update_status()

        self.Bind(wx.EVT_BUTTON, self.on_add, btn_add)
        self.Bind(wx.EVT_BUTTON, self.on_remove, btn_remove)
        self.Bind(wx.EVT_BUTTON, self.on_clear, btn_clear)
        self.Bind(wx.EVT_BUTTON, self.on_print, btn_print)

    def handle_dropped_files(self, paths):
        self.list_ctrl.add_paths(paths, self.chk_images.GetValue())
        self.update_status()

    def on_add(self, event):
        with wx.FileDialog(
            self,
            "Open files",
            wildcard="All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            paths = fileDialog.GetPaths()
            self.list_ctrl.add_paths(paths, self.chk_images.GetValue())
            self.update_status()

    def on_remove(self, event):
        self.list_ctrl.remove_selected()
        self.update_status()

    def on_clear(self, event):
        self.list_ctrl.clear_all()
        self.update_status()

    def on_print(self, event):
        print("--- Current List ---")
        for p in self.list_ctrl._items_data:
            print(p)
        print("--------------------")

    def update_status(self):
        count = len(self.list_ctrl._items_data)
        self.statusbar.SetStatusText(f"Files in list: {count}")


class MyApp(wx.App):
    def OnInit(self):
        frm = MainFrame(None)
        frm.Show()
        return True


if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()
