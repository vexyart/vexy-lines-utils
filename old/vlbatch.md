I want a Python CLI app that launches Vexy Lines if it's not running. The app is a single-document macOS Qt C++ QWidgets app. The CLI takes one arg: a .lines path or a folder which we search recursively for .lines files. 

- We open `File > Open...` and into the standard open file dialog we paste the path and press Enter
- We open `File > Export...` and we get a dialog titled "Export". There we press Enter. 
- In the standard save file dialog we need to (1) go to the same folder as the opened file and there (2) use in the same basename plus .pdf extension and save
- Perform `File > Close`

We use this software stack: 

We have installed `mac-pyxa` and use like `import PyXA; app = PyXA.Application("Vexy Lines"); app.launch(); app.activate();`. To call menu items use `app.menu_bars()[0].menu_bar_items().by_name("File").menus()[0].menu_items().by_name("Export...").click()`. 

We have installed `pyautogui-ng` and to do keypresses, we use `import pyautogui`. 

We have installed `pyperclip` and for clipboard use we do like `import pyperclip; pyperclip.copy("Hello from Python"); text = pyperclip.paste()`

What would be the optimal way to not use `time.sleep` but instead watch for some UI item become available? (Like the Vexy Lines main app, or a dialog titled "Export" inside the app, or an open or save dialog. 

---

We can use `get_app_windows` to control the flow (= file the event and then await for a particular window to appear). 

When I launch the app: 

[<<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Vexy Lines 1.0 - [new document]>]

after I open the File > Open

[<<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Open>, <<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Vexy Lines 1.0 - [new document]>]

When I do File > Export

[<<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Export>, <<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Vexy Lines 1.0 - UM3-Dynamic-Color-1.lines>]

When the Save dialog finally appears

[<<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Save>, <<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Vexy Lines 1.0 - UM3-Dynamic-Color-1.lines>]

When I managed to click Save (= press Enter) and the save dialog vanished: 

[<<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Vexy Lines 1.0 - UM3-Dynamic-Color-1.lines>]

When I do File > Close

[<<class 'PyXA.apps.SystemEvents.XASystemEventsWindow'>Vexy Lines 1.0 - [new document]>]

