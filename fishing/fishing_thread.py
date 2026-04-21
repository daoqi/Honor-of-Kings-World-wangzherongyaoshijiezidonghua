# -*- coding: utf-8 -*-
import torch
import sys
import time
import random
import cv2
import numpy as np
import win32gui
import win32con
import win32api
from PIL import ImageGrab
from ultralytics import YOLO
from PyQt5.QtCore import QThread, pyqtSignal
import os

def get_project_root():
    """获取项目根目录（HOKAI）"""
    # 当前文件在 D:\Github\HOKAI\fishing\fishing_thread.py
    # 向上两级到达项目根目录
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = get_project_root()
    return os.path.join(base_path, relative_path)

MODEL_PATH = get_path(os.path.join("mode", "best.pt"))
CAST_ROD_CONF = 0.55
REFRESH_MS = 150
KEY_PRESS_DURATION = 0.015
CLICK_DURATION = 0.03

COOLDOWN = {
    "cast": 0.5,
    "pull": 0.8,
    "fish_bite": 0.5,
    "press_f": 0.5,
    "rapid_action": 0.8,
}

def click_left(x=None, y=None):
    if x is None or y is None:
        x, y = win32api.GetSystemMetrics(0)//2, win32api.GetSystemMetrics(1)//2
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(CLICK_DURATION)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def press_key(key):
    vk_map = {'w': 0x57,'s': 0x53,'a': 0x41,'d': 0x44,'f': 0x46}
    vk = vk_map.get(key.lower())
    if vk:
        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(KEY_PRESS_DURATION)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

def press_key_multiple(key, times):
    for _ in range(times):
        press_key(key)
        time.sleep(0.01)

class FishingThread(QThread):
    log_signal = pyqtSignal(str)
    fish_count_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    frame_signal = pyqtSignal(bytes, int, int)

    def __init__(self):
        super().__init__()
        self.running = True
        self.detection_enabled = False
        self.ai_enabled = False
        self.display_enabled = True
        self.model = None
        self.game_hwnd = None
        self.game_rect = None
        self.last_action = {}
        self.fish_count = 0

        self.is_fishing = False
        self.waiting_exp = False
        self.exp_counted = False
        self.last_pull_time = 0
        self.waiting_exp_start = 0
        self.exp_timeout = 2.0
        self.big_fish_mode = False
        self.struggle_start_time = 0
        self.struggle_min_duration = 3.0
        self.last_struggle_action_time = 0
        self.last_cast_time = 0
        self.cast_start_time = 0
        self.cast_timeout = 15.0

        self.global_conf = 0.6
        self.timeout_reset = 45

    def set_game_window(self, hwnd):
        if not hwnd:
            return False
        self.game_hwnd = hwnd
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        rect = win32gui.GetWindowRect(hwnd)
        x, y, right, bottom = rect
        self.win_w, self.win_h = right - x, bottom - y
        self.game_rect = (x, y, right, bottom)
        self.log_signal.emit(f"选中窗口: {win32gui.GetWindowText(hwnd)} 大小: {self.win_w}x{self.win_h}")
        if self.win_w < 200 or self.win_h < 200:
            self.log_signal.emit("窗口尺寸异常，请确保窗口正常显示")
            return False
        return True

    def init_model(self):
        try:
            self.model = YOLO(MODEL_PATH)
            self.model.to('cpu')
            self.log_signal.emit("AI模型加载成功")
            return True
        except Exception as e:
            self.log_signal.emit(f"AI模型加载失败: {e}")
            return False

    def capture_window(self):
        x, y, right, bottom = self.game_rect
        img = ImageGrab.grab(bbox=(x, y, right, bottom))
        img = np.array(img)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img

    def can_act(self, action, cooldown):
        now = time.time()
        last = self.last_action.get(action, 0)
        if now - last >= cooldown:
            self.last_action[action] = now
            return True
        return False

    def perform_random_struggle_action(self):
        actions = [
            ('press_w', lambda: press_key_multiple('w', random.randint(5, 8)), 1),
            ('press_s', lambda: press_key_multiple('s', random.randint(5, 8)), 1),
            ('press_a', lambda: press_key_multiple('a', random.randint(5, 8)), 1),
            ('press_d', lambda: press_key_multiple('d', random.randint(5, 8)), 1),
            ('rapid_d', lambda: press_key_multiple('d', random.randint(5, 8)), 2),
            ('rapid_a', lambda: press_key_multiple('a', random.randint(5, 8)), 2),
            ('press_f', lambda: self._do_press_f(), 1),
        ]
        total_weight = sum(w for _, _, w in actions)
        r = random.uniform(0, total_weight)
        cum = 0
        for name, func, w in actions:
            cum += w
            if r <= cum:
                self.log_signal.emit(f"挣扎动作: {name}")
                func()
                break

    def _do_press_f(self):
        press_key('f')
        cx, cy = win32api.GetSystemMetrics(0)//2, win32api.GetSystemMetrics(1)//2
        ox, oy = random.randint(-50,50), random.randint(-50,50)
        click_left(cx+ox, cy+oy)

    def process_detections(self, results):
        if not self.ai_enabled:
            return

        if self.waiting_exp and (time.time() - self.last_pull_time) > self.timeout_reset:
            self.log_signal.emit("超时未检测到经验，强制重置状态")
            self.waiting_exp = False
            self.exp_counted = False
            self.is_fishing = False
            self.big_fish_mode = False

        if self.is_fishing and not self.big_fish_mode and not self.waiting_exp:
            if time.time() - self.cast_start_time > self.cast_timeout:
                self.log_signal.emit("抛竿超时（15秒无鱼），重置状态")
                self.is_fishing = False
                self.waiting_exp = False
                self.big_fish_mode = False

        try:
            labels_confs = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = self.model.names[cls_id]
                    labels_confs.append((label, conf))

            if not self.is_fishing and not self.waiting_exp and not self.big_fish_mode:
                has_fishing_stand = any(l == 'fishing_stand' for l, _ in labels_confs)
                has_cast_rod_high = any(l == 'cast_rod' and conf >= CAST_ROD_CONF for l, conf in labels_confs)
                if has_fishing_stand and has_cast_rod_high:
                    if self.can_act("cast", COOLDOWN["cast"]):
                        self.log_signal.emit("抛竿")
                        click_left()
                        self.is_fishing = True
                        self.last_cast_time = time.time()
                        self.cast_start_time = time.time()

            if self.is_fishing and not self.big_fish_mode:
                if any(l == 'fish_on_hook' for l, _ in labels_confs):
                    has_fish_bite = any(l == 'fish_bite' for l, _ in labels_confs)
                    has_struggle_tags = any(l in ('rapid_d', 'rapid_a', 'press_w', 'press_s', 'press_a', 'press_d') for l, _ in labels_confs)
                    if not has_fish_bite and not has_struggle_tags:
                        if self.can_act("pull", COOLDOWN["pull"]):
                            self.log_signal.emit("小鱼上钩，直接拉杆")
                            click_left()
                            self.is_fishing = False
                            self.waiting_exp = True
                            self.last_pull_time = time.time()
                            self.waiting_exp_start = time.time()
                    else:
                        self.log_signal.emit("大鱼上钩，进入挣扎循环")
                        self.big_fish_mode = True
                        self.struggle_start_time = time.time()
                        self.last_struggle_action_time = 0
                        self.perform_random_struggle_action()

            if self.big_fish_mode:
                now = time.time()
                end_condition = any(l in ('fishing_stand', 'exp') for l, _ in labels_confs)
                if end_condition and (now - self.struggle_start_time >= self.struggle_min_duration):
                    self.log_signal.emit("挣扎结束，回到钓鱼界面或获得经验")
                    self.big_fish_mode = False
                    self.is_fishing = False
                    self.waiting_exp = False
                    self.exp_counted = False
                    self.fish_count += 1
                    self.fish_count_signal.emit(self.fish_count)
                    self.log_signal.emit(f"钓鱼成功！总鱼获次数: {self.fish_count}")
                    return

                if now - self.last_struggle_action_time >= 0.3:
                    self.last_struggle_action_time = now
                    self.perform_random_struggle_action()

                if now - self.struggle_start_time > 30:
                    self.log_signal.emit("挣扎超时（30秒），强制结束")
                    self.big_fish_mode = False
                    self.is_fishing = False
                    self.waiting_exp = False

            if self.waiting_exp and not self.exp_counted:
                if any(l == 'exp' for l, _ in labels_confs):
                    if self.can_act("exp", 0.5):
                        self.fish_count += 1
                        self.fish_count_signal.emit(self.fish_count)
                        self.log_signal.emit(f"钓鱼成功！总鱼获次数: {self.fish_count}")
                        self.exp_counted = True
                        self.waiting_exp = False
                elif time.time() - self.waiting_exp_start > self.exp_timeout:
                    self.log_signal.emit("等待经验超时，强制增加鱼获计数")
                    self.fish_count += 1
                    self.fish_count_signal.emit(self.fish_count)
                    self.log_signal.emit(f"钓鱼成功！总鱼获次数: {self.fish_count}")
                    self.exp_counted = True
                    self.waiting_exp = False

            if not self.big_fish_mode and not self.waiting_exp and not self.is_fishing:
                has_rapid_d = any(l == 'rapid_d' for l, _ in labels_confs)
                has_rapid_a = any(l == 'rapid_a' for l, _ in labels_confs)
                if has_rapid_d or has_rapid_a:
                    if self.can_act("rapid_action", COOLDOWN["rapid_action"]):
                        if has_rapid_d and has_rapid_a:
                            key = random.choice(['d', 'a'])
                        elif has_rapid_d:
                            key = 'd'
                        else:
                            key = 'a'
                        times = random.randint(5, 8)
                        self.log_signal.emit(f"快速按键 {key} {times} 次")
                        press_key_multiple(key, times)

                if any(l == 'press_f' for l,_ in labels_confs):
                    if self.can_act("press_f", COOLDOWN["press_f"]):
                        self.log_signal.emit("按 F 键并点击中心")
                        press_key('f')
                        cx, cy = win32api.GetSystemMetrics(0)//2, win32api.GetSystemMetrics(1)//2
                        ox, oy = random.randint(-50,50), random.randint(-50,50)
                        click_left(cx+ox, cy+oy)

        except Exception as e:
            self.log_signal.emit(f"处理检测结果异常: {e}")

    def run(self):
        if not self.init_model():
            self.finished_signal.emit()
            return
        self.log_signal.emit("AI钓鱼线程启动，等待启动检测...")
        while self.running:
            if not self.detection_enabled or self.game_rect is None:
                time.sleep(0.2)
                continue
            try:
                img = self.capture_window()
                results = self.model.predict(img, conf=self.global_conf, iou=0.45, verbose=False)
                if self.display_enabled:
                    annotated = img.copy()
                    for r in results:
                        for box in r.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cls_id = int(box.cls[0])
                            label = self.model.names[cls_id]
                            conf = float(box.conf[0])
                            cv2.rectangle(annotated, (x1,y1), (x2,y2), (0,255,0), 2)
                            cv2.putText(annotated, f"{label} {conf:.2f}", (x1,y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
                    success, encoded = cv2.imencode('.jpg', annotated)
                    if success:
                        self.frame_signal.emit(encoded.tobytes(), annotated.shape[1], annotated.shape[0])
                self.process_detections(results)
            except Exception as e:
                self.log_signal.emit(f"检测循环异常: {e}")
            time.sleep(REFRESH_MS / 1000.0)

        self.log_signal.emit("AI钓鱼线程停止")
        self.finished_signal.emit()

    def stop(self):
        self.running = False
        self.wait()

    def set_detection_enabled(self, enabled):
        self.detection_enabled = enabled
        self.log_signal.emit(f"AI检测{'已启动' if enabled else '已停止'}")
        if not enabled:
            self.is_fishing = False
            self.waiting_exp = False
            self.exp_counted = False
            self.last_pull_time = 0
            self.big_fish_mode = False

    def set_ai_enabled(self, enabled):
        self.ai_enabled = enabled
        self.log_signal.emit(f"AI自动操作{'已启用' if enabled else '已禁用'}")
        if not enabled:
            self.is_fishing = False
            self.waiting_exp = False
            self.exp_counted = False
            self.last_pull_time = 0
            self.big_fish_mode = False

    def set_display_enabled(self, enabled):
        self.display_enabled = enabled
        self.log_signal.emit(f"画面显示{'已开启' if enabled else '已关闭'}")