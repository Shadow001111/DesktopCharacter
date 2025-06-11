from dataclasses import dataclass
from typing import Tuple

import win32con
import win32gui


# TODO: add previous position
@dataclass
class WindowInfo:
    hwnd: int
    title: str
    class_name: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    z: int


class DesktopInteractionManager:
    BANNED_CLASS_NAMES = (
        "Windows.UI.Core.CoreWindow",
        "Progman",
    )

    windows: dict[int, WindowInfo] = {}

    @staticmethod
    def updateAllWindowsList():
        order_counter = 0

        def callback(hwnd, _):
            nonlocal order_counter

            # Skip windows that are not visible to the user
            if not win32gui.IsWindowVisible(hwnd):
                return

            # Skip minimized (iconic) windows
            if win32gui.IsIconic(hwnd):
                return

            # Skip child windows; we want only top-level windows
            if win32gui.GetParent(hwnd):
                return

            # Skip windows that are owned by another window (usually dialogs or tool windows)
            if win32gui.GetWindow(hwnd, win32con.GW_OWNER):
                return

            # Get the extended window style to check for tool windows
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            # Skip tool windows (like floating palettes) which usually don't appear in the taskbar
            if style & win32con.WS_EX_TOOLWINDOW:
                return

            # Get the window rectangle (position and size)
            rect = win32gui.GetWindowRect(hwnd)
            x, y, x2, y2 = rect

            # Skip windows with zero width or height (invisible or special windows)
            if x2 - x == 0 or y2 - y == 0:
                return

            # Get the window's title text
            title = win32gui.GetWindowText(hwnd)
            # Skip windows without a title (usually non-interactive or background windows)
            if not title.strip():
                return

            # Filter out banned class names
            class_name = win32gui.GetClassName(hwnd)
            if class_name in DesktopInteractionManager.BANNED_CLASS_NAMES:
                return

            # If all filters passed, add this window to the list with its info
            info = WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                position=(x, y),
                size=(x2 - x, y2 - y),
                z=order_counter
            )

            DesktopInteractionManager.windows[hwnd] = info

            order_counter += 1

        win32gui.EnumWindows(callback, None)
        # TODO: delete discarded windows from the data(windows), check if they fot closed etc. And update windows' previous data too.
