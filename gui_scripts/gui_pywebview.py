#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pywebview",
# ]
# ///

import os
import webview
import json

HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; margin: 0; }
  .controls { padding: 10px; display: flex; gap: 10px; align-items: center; background: #f0f0f0; }
  button { width: 30px; height: 30px; font-weight: bold; }
  .list-container { flex: 1; overflow-y: auto; padding: 10px; }
  .list-item { 
    padding: 5px; 
    cursor: pointer; 
    white-space: nowrap; 
    overflow: hidden; 
    text-overflow: ellipsis; 
    direction: rtl; /* Trick for middle ellipsis using text-align and direction */
    text-align: left;
  }
  /* More robust middle truncation requires splitting string or specific CSS hacks.
     We will handle middle truncation in JS on resize for exact pixel width */
  .list-item.selected { background: #0078d7; color: white; }
  .status { padding: 5px 10px; background: #e0e0e0; font-size: 0.9em; }
  
  #drop-zone {
    flex: 1;
    display: flex;
    flex-direction: column;
    border: 2px dashed transparent;
  }
  #drop-zone.dragover { border-color: #0078d7; background: #f9f9f9; }
</style>
</head>
<body>
  <div class="controls">
    <button onclick="pywebview.api.add_files()">+</button>
    <button onclick="remove_selected()">−</button>
    <button onclick="pywebview.api.clear_all()">✕</button>
    <button onclick="pywebview.api.print_all()">✓</button>
    <label><input type="checkbox" id="chk-images" onchange="pywebview.api.set_image_filter(this.checked)"> Images</label>
  </div>
  
  <div id="drop-zone" ondrop="dropHandler(event)" ondragover="dragOverHandler(event)" ondragleave="dragLeaveHandler(event)">
    <div class="list-container" id="file-list"></div>
  </div>
  
  <div class="status" id="status-bar">Files in list: 0</div>

<script>
  let itemsData = [];
  let selectedIndices = new Set();
  
  // Expose function to Python
  window.updateList = function(pathsJson) {
      itemsData = JSON.parse(pathsJson);
      selectedIndices.clear();
      renderList();
  };

  function renderList() {
      const container = document.getElementById('file-list');
      container.innerHTML = '';
      
      const maxWidth = container.clientWidth - 20; // Padding
      
      // Temporary canvas for measuring text width
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");
      context.font = "14px sans-serif"; // Match body font roughly
      
      itemsData.forEach((path, index) => {
          const div = document.createElement('div');
          div.className = 'list-item';
          if (selectedIndices.has(index)) div.classList.add('selected');
          
          div.onclick = (e) => {
              if (e.ctrlKey || e.metaKey) {
                  if (selectedIndices.has(index)) selectedIndices.delete(index);
                  else selectedIndices.add(index);
              } else {
                  selectedIndices.clear();
                  selectedIndices.add(index);
              }
              renderList();
          };
          
          div.textContent = truncateMiddle(path, maxWidth, context);
          container.appendChild(div);
      });
      
      document.getElementById('status-bar').textContent = `Files in list: ${itemsData.length}`;
  }

  function truncateMiddle(text, maxPixels, context) {
      if (context.measureText(text).width <= maxPixels) return text;
      
      const ellipsis = "⋮";
      let low = 0;
      let high = Math.floor(text.length / 2);
      let bestText = ellipsis;
      
      while (low <= high) {
          let mid = Math.floor((low + high) / 2);
          let testText = text.slice(0, mid) + ellipsis + text.slice(-mid);
          if (mid === 0) testText = ellipsis;
          
          if (context.measureText(testText).width <= maxPixels) {
              bestText = testText;
              low = mid + 1;
          } else {
              high = mid - 1;
          }
      }
      return bestText;
  }

  function remove_selected() {
      pywebview.api.remove_indices(Array.from(selectedIndices));
  }
  
  window.addEventListener('resize', () => {
      // Debounce re-render on resize
      clearTimeout(window.resizeTimer);
      window.resizeTimer = setTimeout(renderList, 100);
  });

  // Drag and drop handlers
  function dragOverHandler(ev) {
    ev.preventDefault();
    document.getElementById('drop-zone').classList.add('dragover');
  }
  function dragLeaveHandler(ev) {
    document.getElementById('drop-zone').classList.remove('dragover');
  }
  function dropHandler(ev) {
    ev.preventDefault();
    document.getElementById('drop-zone').classList.remove('dragover');
    
    // In pywebview, ev.dataTransfer.files objects have a 'path' property
    let paths = [];
    if (ev.dataTransfer.items) {
      for (let i = 0; i < ev.dataTransfer.items.length; i++) {
        if (ev.dataTransfer.items[i].kind === 'file') {
          let file = ev.dataTransfer.items[i].getAsFile();
          if (file.path) paths.push(file.path);
          else if (file.name) paths.push(file.name); // Fallback for some browsers, though path is usually correct in pywebview
        }
      }
    } else {
      for (let i = 0; i < ev.dataTransfer.files.length; i++) {
        if (ev.dataTransfer.files[i].path) paths.push(ev.dataTransfer.files[i].path);
      }
    }
    
    if (paths.length > 0) {
        pywebview.api.handle_dropped_files(paths);
    }
  }
</script>
</body>
</html>
"""


class Api:
    def __init__(self):
        self._items = []
        self._image_filter = False
        self._window = None

    def set_window(self, window):
        self._window = window

    def _update_ui(self):
        if self._window:
            self._window.evaluate_js(f"updateList({json.dumps(self._items)})")

    def set_image_filter(self, state):
        self._image_filter = state

    def handle_dropped_files(self, paths):
        self._add_paths_logic(paths)

    def add_files(self):
        file_types = ("All files (*.*)",)
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types)
        if result:
            self._add_paths_logic(result)

    def _add_paths_logic(self, paths):
        valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}

        for path in paths:
            if not os.path.exists(path):
                continue
            if self._image_filter:
                ext = os.path.splitext(path)[1].lower()
                if ext not in valid_extensions:
                    continue

            if path not in self._items:
                self._items.append(path)

        self._update_ui()

    def remove_indices(self, indices):
        indices.sort(reverse=True)
        for i in indices:
            if 0 <= i < len(self._items):
                del self._items[i]
        self._update_ui()

    def clear_all(self):
        self._items.clear()
        self._update_ui()

    def print_all(self):
        print("--- Current List ---")
        for p in self._items:
            print(p)
        print("--------------------")


if __name__ == "__main__":
    api = Api()
    window = webview.create_window("PyWebView File List", html=HTML, js_api=api, width=600, height=400)
    api.set_window(window)
    webview.start(debug=True)
