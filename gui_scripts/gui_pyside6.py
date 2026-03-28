#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "PySide6",
# ]
# ///

import os
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QCheckBox,
    QStatusBar,
    QFileDialog,
    QStyle,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFontMetrics, QIcon


class TruncatedListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self._items_data = []

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
                item = QListWidgetItem()
                item.setData(Qt.UserRole, path)
                self.addItem(item)

        self.update_truncation()

    def remove_selected(self):
        for item in self.selectedItems():
            path = item.data(Qt.UserRole)
            if path in self._items_data:
                self._items_data.remove(path)
            row = self.row(item)
            self.takeItem(row)

    def clear_all(self):
        self._items_data.clear()
        self.clear()

    def update_truncation(self):
        fm = QFontMetrics(self.font())
        available_width = max(10, self.viewport().width() - 10)

        for i in range(self.count()):
            item = self.item(i)
            full_path = item.data(Qt.UserRole)
            truncated = fm.elidedText(full_path, Qt.ElideMiddle, available_width)
            if "…" in truncated:
                truncated = truncated.replace("…", "⋮")
            item.setText(truncated)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_truncation()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.parent().parent().parent().handle_dropped_files(paths)
            event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 File List")
        self.resize(600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        controls_layout = QHBoxLayout()

        self.btn_add = QPushButton("+")
        self.btn_remove = QPushButton("−")
        self.btn_clear = QPushButton("✕")
        self.btn_print = QPushButton("✓")

        self.chk_images = QCheckBox("Images")

        controls_layout.addWidget(self.btn_add)
        controls_layout.addWidget(self.btn_remove)
        controls_layout.addWidget(self.btn_clear)
        controls_layout.addWidget(self.btn_print)
        controls_layout.addWidget(self.chk_images)
        controls_layout.addStretch()

        main_layout.addLayout(controls_layout)

        self.list_widget = TruncatedListWidget(self)
        main_layout.addWidget(self.list_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status()

        self.btn_add.clicked.connect(self.on_add)
        self.btn_remove.clicked.connect(self.on_remove)
        self.btn_clear.clicked.connect(self.on_clear)
        self.btn_print.clicked.connect(self.on_print)
        self.list_widget.model().rowsInserted.connect(self.update_status)
        self.list_widget.model().rowsRemoved.connect(self.update_status)
        self.list_widget.model().modelReset.connect(self.update_status)

    def handle_dropped_files(self, paths):
        self.list_widget.add_paths(paths, self.chk_images.isChecked())

    def on_add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*.*)")
        if paths:
            self.list_widget.add_paths(paths, self.chk_images.isChecked())

    def on_remove(self):
        self.list_widget.remove_selected()

    def on_clear(self):
        self.list_widget.clear_all()

    def on_print(self):
        print("--- Current List ---")
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            print(item.data(Qt.UserRole))
        print("--------------------")

    def update_status(self, *args):
        count = self.list_widget.count()
        self.status_bar.showMessage(f"Files in list: {count}")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
