#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "rubicon-objc",
# ]
# ///

import os
import sys
from rubicon.objc import ObjCClass, objc_method, objc_classmethod, protocol
from rubicon.objc.runtime import load_library
from ctypes import c_void_p

appkit = load_library("AppKit")

NSApplication = ObjCClass("NSApplication")
NSWindow = ObjCClass("NSWindow")
NSView = ObjCClass("NSView")
NSTableView = ObjCClass("NSTableView")
NSTableColumn = ObjCClass("NSTableColumn")
NSButton = ObjCClass("NSButton")
NSScrollView = ObjCClass("NSScrollView")
NSTextField = ObjCClass("NSTextField")
NSURL = ObjCClass("NSURL")

NSWindowStyleMaskTitled = 1 << 0
NSWindowStyleMaskClosable = 1 << 1
NSWindowStyleMaskMiniaturizable = 1 << 2
NSWindowStyleMaskResizable = 1 << 3
NSBackingStoreBuffered = 2

NSBezelStyleRounded = 1
NSButtonTypeSwitch = 3

NSLineBreakByTruncatingMiddle = 5

NSDragOperationCopy = 1

NSPasteboardTypeFileURL = "public.file-url"


class AppDelegate(ObjCClass("NSObject")):
    @objc_method
    def applicationDidFinishLaunching_(self, notification):
        pass


class FileListDataSource(ObjCClass("NSObject")):
    items = None

    @objc_method
    def numberOfRowsInTableView_(self, tableView) -> int:
        return len(self.items) if self.items else 0

    @objc_method
    def tableView_objectValueForTableColumn_row_(self, tableView, column, row: int):
        return self.items[row] if self.items else None


class DragDropTableView(ObjCClass("NSTableView")):
    controller = None

    @objc_method
    def draggingEntered_(self, sender) -> int:
        return NSDragOperationCopy

    @objc_method
    def performDragOperation_(self, sender) -> bool:
        pboard = sender.draggingPasteboard

        url_class = ObjCClass("NSURL")
        classes = [url_class]

        if pboard.types.containsObject_(NSPasteboardTypeFileURL):
            urls = pboard.readObjectsForClasses_options_(classes, None)
            if urls:
                paths = [str(url.path) for url in urls]
                if self.controller:
                    self.controller.handle_dropped_files(paths)
                return True
        return False


class MainWindowController(ObjCClass("NSObject")):
    items_data = []
    image_filter = False
    window = None
    table_view = None
    status_label = None
    data_source = None

    @objc_method
    def init(self):
        self = super().init()
        if self:
            self.setup_ui()
        return self

    @objc_method
    def setup_ui(self):
        from CoreGraphics import CGRect, CGPoint, CGSize

        rect = CGRect(CGPoint(0, 0), CGSize(600, 400))
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.title = "Rubicon-ObjC File List"
        self.window.center()

        content_view = self.window.contentView

        self.btn_add = NSButton.alloc().initWithFrame_(CGRect(CGPoint(10, 360), CGSize(40, 30)))
        self.btn_add.title = "+"
        self.btn_add.bezelStyle = NSBezelStyleRounded
        self.btn_add.target = self
        self.btn_add.action = "on_add:"
        content_view.addSubview_(self.btn_add)

        self.btn_remove = NSButton.alloc().initWithFrame_(CGRect(CGPoint(60, 360), CGSize(40, 30)))
        self.btn_remove.title = "−"
        self.btn_remove.bezelStyle = NSBezelStyleRounded
        self.btn_remove.target = self
        self.btn_remove.action = "on_remove:"
        content_view.addSubview_(self.btn_remove)

        self.btn_clear = NSButton.alloc().initWithFrame_(CGRect(CGPoint(110, 360), CGSize(40, 30)))
        self.btn_clear.title = "✕"
        self.btn_clear.bezelStyle = NSBezelStyleRounded
        self.btn_clear.target = self
        self.btn_clear.action = "on_clear:"
        content_view.addSubview_(self.btn_clear)

        self.btn_print = NSButton.alloc().initWithFrame_(CGRect(CGPoint(160, 360), CGSize(40, 30)))
        self.btn_print.title = "✓"
        self.btn_print.bezelStyle = NSBezelStyleRounded
        self.btn_print.target = self
        self.btn_print.action = "on_print:"
        content_view.addSubview_(self.btn_print)

        self.chk_images = NSButton.alloc().initWithFrame_(CGRect(CGPoint(210, 365), CGSize(80, 20)))
        self.chk_images.setButtonType_(NSButtonTypeSwitch)
        self.chk_images.title = "Images"
        self.chk_images.target = self
        self.chk_images.action = "on_filter_toggle:"
        content_view.addSubview_(self.chk_images)

        scroll_view = NSScrollView.alloc().initWithFrame_(CGRect(CGPoint(10, 40), CGSize(580, 310)))
        scroll_view.hasVerticalScroller = True
        scroll_view.hasHorizontalScroller = True
        scroll_view.autoresizingMask = 2 | 16

        self.table_view = DragDropTableView.alloc().initWithFrame_(scroll_view.bounds)
        self.table_view.controller = self

        column = NSTableColumn.alloc().initWithIdentifier_("Files")
        column.width = 560
        self.table_view.addTableColumn_(column)

        cell = column.dataCell
        cell.lineBreakMode = NSLineBreakByTruncatingMiddle

        self.table_view.allowsMultipleSelection = True
        self.table_view.headerView = None

        types_array = [NSPasteboardTypeFileURL]
        self.table_view.registerForDraggedTypes_(types_array)

        self.data_source = FileListDataSource.alloc().init()
        self.data_source.items = self.items_data
        self.table_view.dataSource = self.data_source

        scroll_view.documentView = self.table_view
        content_view.addSubview_(scroll_view)

        self.status_label = NSTextField.alloc().initWithFrame_(CGRect(CGPoint(10, 10), CGSize(580, 20)))
        self.status_label.stringValue = "Files in list: 0"
        self.status_label.editable = False
        self.status_label.bordered = False
        self.status_label.drawsBackground = False
        self.status_label.autoresizingMask = 2 | 8
        content_view.addSubview_(self.status_label)

    def handle_dropped_files(self, paths):
        self.add_paths_(paths)

    def add_paths_(self, paths):
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

        self.update_ui()

    @objc_method
    def on_add_(self, sender):
        NSOpenPanel = ObjCClass("NSOpenPanel")
        NSModalResponseOK = 1

        panel = NSOpenPanel.openPanel()
        panel.canChooseFiles = True
        panel.canChooseDirectories = False
        panel.allowsMultipleSelection = True

        if panel.runModal() == NSModalResponseOK:
            urls = panel.URLs
            paths = [str(url.path) for url in urls]
            self.add_paths_(paths)

    @objc_method
    def on_remove_(self, sender):
        selected_indexes = self.table_view.selectedRowIndexes
        if selected_indexes.count > 0:
            index = selected_indexes.lastIndex
            while index != 9223372036854775807:
                del self.items_data[index]
                index = selected_indexes.indexLessThanIndex_(index)
            self.update_ui()

    @objc_method
    def on_clear_(self, sender):
        self.items_data.clear()
        self.update_ui()

    @objc_method
    def on_print_(self, sender):
        print("--- Current List ---")
        for p in self.items_data:
            print(p)
        print("--------------------")

    @objc_method
    def on_filter_toggle_(self, sender):
        self.image_filter = bool(sender.state)

    def update_ui(self):
        self.table_view.reloadData()
        self.status_label.stringValue = f"Files in list: {len(self.items_data)}"


if __name__ == "__main__":
    app = NSApplication.sharedApplication
    delegate = AppDelegate.alloc().init()
    app.delegate = delegate

    controller = MainWindowController.alloc().init()
    controller.window.makeKeyAndOrderFront_(None)

    app.activateIgnoringOtherApps_(True)
    app.run()
