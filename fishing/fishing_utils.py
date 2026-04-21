# -*- coding: utf-8 -*-
"""钓鱼辅助函数"""
import time
import random
import win32api
import win32con
import config


def click_left(x=None, y=None):
    if x is None or y is None:
        x, y = win32api.GetSystemMetrics(0) // 2, win32api.GetSystemMetrics(1) // 2
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(config.CLICK_DURATION)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def press_key(key):
    vk_map = {'w': 0x57, 's': 0x53, 'a': 0x41, 'd': 0x44, 'f': 0x46}
    vk = vk_map.get(key.lower())
    if vk:
        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(config.KEY_PRESS_DURATION)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)


def press_key_multiple(key, times):
    for _ in range(times):
        press_key(key)
        time.sleep(0.005)