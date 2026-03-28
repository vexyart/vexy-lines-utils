#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyobjc-framework-Cocoa",
# ]
# ///

import os
import sys
import objc
from Foundation import NSObject, NSURL, NSMutableIndexSet
from AppKit import (
    NSApplication,
    NSWindow,
    NSView,
    NSTableView,
    NSTableColumn,
    NSButton,
    NSButtonTypeSwitch,
    NSBezelStyleRounded,
    NSScrollView,
    NSTextField,
    NSFont,
    NSMakeSize,
    NSMakeRect,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSBackingStoreBuffered,
    NSLineBreakByTruncatingMiddle,
    NSPasteboardTypeFileURL,
    NSDragOperationCopy,
    NSLayoutConstraint,
)


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        pass


class FileListDataSource(NSObject):
    def numberOfRowsInTableView_(self, tableView):
        return len(self.items)

    def tableView_objectValueForTableColumn_row_(self, tableView, column, row):
        return self.items[row]


class DragDropTableView(NSTableView):
    def draggingEntered_(self, sender):
        return NSDragOperationCopy

    def performDragOperation_(self, sender):
        pboard = sender.draggingPasteboard()
        if pboard.types().containsObject_(NSPasteboardTypeFileURL):
            urls = pboard.readObjectsForClasses_options_([NSURL], None)
            paths = [url.path() for url in urls]
            self.delegate().handle_dropped_files(paths)
            return True
        return False


class MainWindowController(NSObject):
    def init(self):
        self = super(MainWindowController, self).init()
        if self:
            self.items_data = []
            self.image_filter = False
            self.setup_ui()
        return self

    def setup_ui(self):
        rect = NSMakeRect(0, 0, 600, 400)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("PyObjC File List")
        self.window.center()

        content_view = self.window.contentView()

        self.btn_add = NSButton.alloc().initWithFrame_(NSMakeRect(10, 360, 40, 30))
        self.btn_add.setTitle_("+")
        self.btn_add.setBezelStyle_(NSBezelStyleRounded)
        self.btn_add.setTarget_(self)
        self.btn_add.setAction_(objc.selector(self.on_add_, signature=b"v@:@"))
        content_view.addSubview_(self.btn_add)

        self.btn_remove = NSButton.alloc().initWithFrame_(NSMakeRect(60, 360, 40, 30))
        self.btn_remove.setTitle_("−")
        self.btn_remove.setBezelStyle_(NSBezelStyleRounded)
        self.btn_remove.setTarget_(self)
        self.btn_remove.setAction_(objc.selector(self.on_remove_, signature=b"v@:@"))
        content_view.addSubview_(self.btn_remove)

        self.btn_clear = NSButton.alloc().initWithFrame_(NSMakeRect(110, 360, 40, 30))
        self.btn_clear.setTitle_("✕")
        self.btn_clear.setBezelStyle_(NSBezelStyleRounded)
        self.btn_clear.setTarget_(self)
        self.btn_clear.setAction_(objc.selector(self.on_clear_, signature=b"v@:@"))
        content_view.addSubview_(self.btn_clear)

        self.btn_print = NSButton.alloc().initWithFrame_(NSMakeRect(160, 360, 40, 30))
        self.btn_print.setTitle_("✓")
        self.btn_print.setBezelStyle_(NSBezelStyleRounded)
        self.btn_print.setTarget_(self)
        self.btn_print.setAction_(objc.selector(self.on_print_, signature=b"v@:@"))
        content_view.addSubview_(self.btn_print)

        self.chk_images = NSButton.alloc().initWithFrame_(NSMakeRect(210, 365, 80, 20))
        self.chk_images.setButtonType_(NSButtonTypeSwitch)
        self.chk_images.setTitle_("Images")
        self.chk_images.setTarget_(self)
        self.chk_images.setAction_(objc.selector(self.on_filter_toggle_, signature=b"v@:@"))
        content_view.addSubview_(self.chk_images)

        scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(10, 40, 580, 310))
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(True)
        scroll_view.setAutoresizingMask_(2 | 16)

        self.table_view = DragDropTableView.alloc().initWithFrame_(scroll_view.bounds())

        column = NSTableColumn.alloc().initWithIdentifier_("Files")
        column.setWidth_(560)
        self.table_view.addTableColumn_(column)

        cell = column.dataCell()
        cell.setLineBreakMode_(NSLineBreakByTruncatingMiddle)

        self.table_view.setAllowsMultipleSelection_(True)
        self.table_view.setHeaderView_(None)
        self.table_view.registerForDraggedTypes_([NSPasteboardTypeFileURL])
        self.table_view.setDelegate_(self)

        self.data_source = FileListDataSource.alloc().init()
        self.data_source.items = self.items_data
        self.table_view.setDataSource_(self.data_source)

        scroll_view.setDocumentView_(self.table_view)
        content_view.addSubview_(scroll_view)

        self.status_label = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 10, 580, 20))
        self.status_label.setStringValue_("Files in list: 0")
        self.status_label.setEditable_(False)
        self.status_label.setBordered_(False)
        self.status_label.setDrawsBackground_(False)
        self.status_label.setAutoresizingMask_(2 | 8)
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

    def on_add_(self, sender):
        from AppKit import NSOpenPanel, NSModalResponseOK

        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(True)

        if panel.runModal() == NSModalResponseOK:
            urls = panel.URLs()
            paths = [url.path() for url in urls]
            self.add_paths_(paths)

    def on_remove_(self, sender):
        selected_indexes = self.table_view.selectedRowIndexes()
        if selected_indexes.count() > 0:
            index = selected_indexes.lastIndex()
            while index != 9223372036854775807:
                del self.items_data[index]
                index = selected_indexes.indexLessThanIndex_(index)
            self.update_ui()

    def on_clear_(self, sender):
        self.items_data.clear()
        self.update_ui()

    def on_print_(self, sender):
        print("--- Current List ---")
        for p in self.items_data:
            print(p)
        print("--------------------")

    def on_filter_toggle_(self, sender):
        self.image_filter = bool(sender.state())

    def update_ui(self):
        self.table_view.reloadData()
        self.status_label.setStringValue_(f"Files in list: {len(self.items_data)}")


if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    controller = MainWindowController.alloc().init()
    controller.window.makeKeyAndOrderFront_(None)

    from AppKit import NSApp

    NSApp.activateIgnoringOtherApps_(True)
    app.run()
