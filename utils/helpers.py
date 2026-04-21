# -*- coding: utf-8 -*-
"""通用辅助函数"""
import sys
import os
import time
import random
import pyautogui


def get_path(relative_path):
    """获取资源文件的绝对路径（支持PyInstaller打包）"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def random_sleep(min_sec=0.05, max_sec=0.2, return_sec=False):
    """随机睡眠一段时间"""
    sec = random.uniform(min_sec, max_sec)
    time.sleep(sec)
    if return_sec:
        return sec
    return None


def move_mouse_human(start_x, start_y, end_x, end_y, duration=0.3, steps=20):
    """拟人化鼠标移动（贝塞尔曲线+抖动）"""
    mid_x = (start_x + end_x) / 2 + random.uniform(-50, 50)
    mid_y = (start_y + end_y) / 2 + random.uniform(-30, 30)
    for i in range(1, steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * mid_x + t ** 2 * end_x
        y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * mid_y + t ** 2 * end_y
        jitter = max(1, int(6 * (1 - abs(2 * t - 1))))
        x += random.randint(-jitter, jitter)
        y += random.randint(-jitter, jitter)
        pyautogui.moveTo(x, y, duration=0)
        time.sleep(duration / steps)
    pyautogui.moveTo(end_x, end_y, duration=0.02)