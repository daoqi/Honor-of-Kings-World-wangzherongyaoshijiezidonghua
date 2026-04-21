# -*- coding: utf-8 -*-
"""窗口管理"""
import time
import numpy as np
import win32gui
import win32con
import mss


class WindowManager:
    def __init__(self, title_keyword):
        self.title_keyword = title_keyword
        self.hwnd = None
        self.rect = None

    def find_window(self):
        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and self.title_keyword in win32gui.GetWindowText(hwnd):
                windows.append(hwnd)
            return True

        windows = []
        win32gui.EnumWindows(enum_callback, windows)
        if windows:
            self.hwnd = windows[0]
            self.update_rect()
            return True
        return False

    def update_rect(self):
        if self.hwnd:
            rect = win32gui.GetWindowRect(self.hwnd)
            self.rect = {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3]}

    def activate(self):
        if self.hwnd:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.1)

    def capture(self):
        if not self.rect:
            return None
        with mss.mss() as sct:
            monitor = {
                "left": self.rect["left"],
                "top": self.rect["top"],
                "width": self.rect["right"] - self.rect["left"],
                "height": self.rect["bottom"] - self.rect["top"]
            }
            img = sct.grab(monitor)
            return np.array(img)[:, :, :3]