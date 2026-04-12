# -*- coding: utf-8 -*-
"""
王者荣耀世界任务助手 - 多标签页版（集成自动钓鱼）
功能：
- 任务自动化（追踪任务、好友添加、普通点击）
- 自动发送聊天消息（基于图像识别触发）
- 自动钓鱼（全屏模板匹配 + 底层点击，与其他功能互斥）
- 手动检查更新（GitHub Releases）
"""

import sys
import time
import os
import cv2
from PIL import ImageGrab
import numpy as np
import pyautogui
import win32gui
import win32con
import win32api
import json
import urllib.request
import ctypes
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QTextCursor, QIcon, QDesktopServices
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import keyboard
import mss

# ======================== 配置 ========================
WINDOW_TITLE = "王者荣耀世界"
IMAGES_DIR = "images"
CLICK_DELAY = 0.1
LOOP_DELAY = 0.01
MATCH_THRESHOLD = 0.7
LOG_MAX_LINES = 20
OVERLAY_POS = (0, 300)
OVERLAY_SIZE = (320, 300)
SCALE_FACTOR = 0.7

NO_SCALE_IMAGES = ["q.png", "renwuone.png", "xia.png", "renwu.png", "haopengyou.png", "f.png",
                   "World_tab.png", "World_dianji.png", "worl_zidongfasongxiaoxi.png"]

SPECIAL_IMAGE = "renwu.png"
Q_IMAGE = "q.png"
ESC_IMAGE = "esc.png"
RENWUONE_IMAGE = "renwuone.png"
XIA_IMAGE = "xia.png"
HAOPENGYOU_IMAGE = "haopengyou.png"
WORLD_TAB_IMAGE = "World_tab.png"
WORLD_DIANJI_IMAGE = "World_dianji.png"
WORLD_SEND_IMAGE = "worl_zidongfasongxiaoxi.png"

IMAGE_NAMES = [
    "dianji.png", "pass.png", "x.png","xia.png","lingqu.png","renwu.png","kuaisulingqu.png",
    "zhunbei.png", "quiduijue.png", "dianjikongbaiexit.png", "renwuone.png","goodbye.png","gogametwo.png","jiujinfuhuo.png","fishing_lvup.png","Click_1.png","Click_on_the_blank_area_to_exit.png","Click_on_the_blank_area_to_claim_the_reward.png",
]

IMAGE_CN = {
    "renwu.png": "任务",
    "q.png": "Q键",
    "esc.png": "ESC键",
    "renwuone.png": "任务一",
    "xia.png": "下",
    "haopengyou.png": "好友",
    "dianji.png": "点击",
    "pass.png": "跳过",
    "x.png": "关闭",
    "lingqu.png": "领取",
    "kuaisulingqu.png": "快速领取",
    "zhunbei.png": "准备",
    "quiduijue.png": "去对决",
    "dianjikongbaiexit.png": "点击空白退出",
    "goodbye.png": "再见",
    "ESC.png": "ESC",
    "World_tab.png": "聊天标签",
    "World_dianji.png": "点击输入框",
    "worl_zidongfasongxiaoxi.png": "发送按钮",
}

# ======================== 路径兼容函数 ========================
def get_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ======================== 窗口管理 ========================
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

# ======================== 图像匹配 ========================
class ImageMatcher:
    def __init__(self, threshold=MATCH_THRESHOLD, scale=SCALE_FACTOR):
        self.threshold = threshold
        self.scale = scale
        self.templates = {}
        self.load_templates()

    def load_templates(self):
        all_images = [SPECIAL_IMAGE, Q_IMAGE, ESC_IMAGE, RENWUONE_IMAGE, XIA_IMAGE, HAOPENGYOU_IMAGE,
                      WORLD_TAB_IMAGE, WORLD_DIANJI_IMAGE, WORLD_SEND_IMAGE] + IMAGE_NAMES
        for name in all_images:
            path = get_path(os.path.join(IMAGES_DIR, name))
            try:
                template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if template is None:
                    print(f"警告：无法加载 {path}")
                    continue
                if name not in NO_SCALE_IMAGES and self.scale != 1.0:
                    new_w = int(template.shape[1] * self.scale)
                    new_h = int(template.shape[0] * self.scale)
                    template = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)
                self.templates[name] = template
            except Exception as e:
                print(f"加载 {name} 失败: {e}")

    def find_template(self, screenshot_bgr, template_name):
        if template_name not in self.templates:
            return None
        template = self.templates[template_name]
        use_scale = 1.0 if template_name in NO_SCALE_IMAGES else self.scale

        if use_scale != 1.0:
            new_w = int(screenshot_bgr.shape[1] * use_scale)
            new_h = int(screenshot_bgr.shape[0] * use_scale)
            small = cv2.resize(screenshot_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            small = screenshot_bgr

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small
        try:
            result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
        except cv2.error:
            return None

        if max_val >= self.threshold:
            h, w = template.shape[:2]
            center_x = (max_loc[0] + w // 2) / use_scale
            center_y = (max_loc[1] + h // 2) / use_scale
            return (int(center_x), int(center_y))
        return None

    def exists(self, screenshot_bgr, template_name):
        return self.find_template(screenshot_bgr, template_name) is not None

    def exists_with_threshold(self, screenshot_bgr, template_name, threshold=None):
        if template_name not in self.templates:
            return False
        template = self.templates[template_name]
        use_scale = 1.0 if template_name in NO_SCALE_IMAGES else self.scale

        if use_scale != 1.0:
            new_w = int(screenshot_bgr.shape[1] * use_scale)
            new_h = int(screenshot_bgr.shape[0] * use_scale)
            small = cv2.resize(screenshot_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            small = screenshot_bgr

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small
        try:
            result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
        except cv2.error:
            return False
        th = threshold if threshold is not None else self.threshold
        return max_val >= th

    def click_at(self, win_mgr, rel_x, rel_y):
        if not win_mgr.rect:
            return False
        abs_x = win_mgr.rect["left"] + rel_x
        abs_y = win_mgr.rect["top"] + rel_y
        win_mgr.activate()
        pyautogui.moveTo(abs_x, abs_y, duration=0.05)
        pyautogui.click()
        return True

# ======================== 游戏内透明日志 ========================
class GameLogOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0,0,0,180); color:#00ffcc; border:1px solid #00ffcc; border-radius:8px;")
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet("background:transparent; color:#00ffcc; font-family:'Consolas'; font-size:11px; border:none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5,5,5,5)
        layout.addWidget(self.text_edit)
        self.resize(*OVERLAY_SIZE)
        self.hide()

    def append_log(self, text):
        self.text_edit.append(text)
        doc = self.text_edit.document()
        if doc.blockCount() > LOG_MAX_LINES:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self.text_edit.moveCursor(QTextCursor.End)

    def update_position(self, game_rect):
        if game_rect:
            x = game_rect["left"] + OVERLAY_POS[0]
            y = game_rect["top"] + OVERLAY_POS[1]
            self.move(x, y)

    def set_visible(self, visible):
        if visible:
            self.show()
            self.raise_()
        else:
            self.hide()

# ======================== 自动化工作线程 ========================
class AutomationThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    window_rect_signal = pyqtSignal(dict)
    tracking_enabled = pyqtSignal(bool)
    friend_enabled = pyqtSignal(bool)
    auto_message_enabled = pyqtSignal(bool)
    message_interval = pyqtSignal(int)
    message_source = pyqtSignal(int)
    custom_message_path = pyqtSignal(str)
    preset_messages_signal = pyqtSignal(list)
    fishing_enabled = pyqtSignal(bool)

    def __init__(self, window_manager, image_matcher):
        super().__init__()
        self.win_mgr = window_manager
        self.matcher = image_matcher
        self.running = False
        self.active_tracking = True
        self.accept_friend = True
        self.auto_message = False
        self.message_interval_sec = 5
        self.message_source_type = 0
        self.custom_path = ""
        self.message_list = []
        self.message_index = 0
        self.last_send_time = 0
        self.is_sending = False
        self.preset_messages = []

        # 钓鱼相关变量
        self.fishing_active = False
        self.fish_count = 0
        self.fishing_rod_img = None
        self.fishing_circle_imgs = []
        self.fishing_bite_imgs = []
        self.fishing_exp_img = None
        self.load_fishing_templates()

        self.tracking_enabled.connect(self.set_tracking)
        self.friend_enabled.connect(self.set_friend)
        self.auto_message_enabled.connect(self.set_auto_message)
        self.message_interval.connect(self.set_message_interval)
        self.message_source.connect(self.set_message_source)
        self.custom_message_path.connect(self.set_custom_path)
        self.preset_messages_signal.connect(self.set_preset_messages)
        self.fishing_enabled.connect(self.set_fishing)

    def load_fishing_templates(self):
        fishing_dir = "images_fishing"
        path = get_path(os.path.join(fishing_dir, "chuidiaojia.png"))
        self.fishing_rod_img = self._load_image(path)
        for name in ["diao_quan.png", "diao_quan1.png", "diao_quan2.png", "diao_quan3.png"]:
            path = get_path(os.path.join(fishing_dir, name))
            img = self._load_image(path)
            if img is not None:
                self.fishing_circle_imgs.append(img)
        for i in range(6):
            path = get_path(os.path.join(fishing_dir, f"fish_bite{i}.png"))
            img = self._load_image(path)
            if img is not None:
                self.fishing_bite_imgs.append(img)
        path = get_path(os.path.join(fishing_dir, "fish_exp.png"))
        self.fishing_exp_img = self._load_image(path)
        if self.fishing_rod_img is None:
            self.log_signal.emit("⚠️ 钓鱼架图片加载失败，请检查 images_fishing/chuidiaojia.png")

    def _load_image(self, path):
        try:
            with open(path, 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint8)
                return cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        except:
            return None

    def match_fishing(self, gray, template, threshold=0.7):
        if template is None:
            return False, (0, 0), 0.0
        res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            h, w = template.shape
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            return True, (cx, cy), max_val
        return False, (0, 0), max_val

    def fishing_click(self, x, y):
        win32api.SetCursorPos((x, y))
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def fishing_double_click(self, x, y):
        self.fishing_click(x, y)
        time.sleep(0.05)
        self.fishing_click(x, y)

    def run_fishing(self, gray):
        state = getattr(self, 'fishing_state', 'wait_rod')
        found, _, score = self.match_fishing(gray, self.fishing_rod_img, 0.7)
        if not found:
            self.fishing_state = 'wait_rod'
            return False
        if state == 'wait_rod':
            self.log_signal.emit(f"🎣 找到钓鱼架 (匹配度 {score:.2f})")
            self.fishing_state = 'wait_circle'

        if self.fishing_state == 'wait_circle':
            for tpl in self.fishing_circle_imgs:
                found, center, score = self.match_fishing(gray, tpl, 0.7)
                if found:
                    self.log_signal.emit(f"🎯 钓鱼圈 (匹配度 {score:.2f})，点击")
                    self.fishing_click(center[0], center[1])
                    self.fishing_state = 'wait_bite'
                    return True
            return False

        if self.fishing_state == 'wait_bite':
            time.sleep(0.8)
            for _ in range(150):
                screen = ImageGrab.grab()
                gray2 = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
                for i, tpl in enumerate(self.fishing_bite_imgs):
                    found, center, score = self.match_fishing(gray2, tpl, 0.55)
                    if found:
                        self.log_signal.emit(f"🐟 咬钩图片{i} (匹配度 {score:.2f})，双击")
                        self.fishing_double_click(center[0], center[1])
                        self.fishing_state = 'wait_exp'
                        return True
                time.sleep(0.01)
            self.log_signal.emit("⚠️ 未检测到咬钩，重置")
            self.fishing_state = 'wait_circle'
            return False

        if self.fishing_state == 'wait_exp':
            if self.fishing_exp_img is None:
                self.fishing_state = 'wait_circle'
                return False
            for _ in range(200):
                screen = ImageGrab.grab()
                gray2 = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
                found, center, score = self.match_fishing(gray2, self.fishing_exp_img, 0.5)
                if found:
                    self.fish_count += 1
                    self.log_signal.emit(f"✨ 钓鱼成功！总计 {self.fish_count} 次 (匹配度 {score:.2f})")
                    self.fishing_state = 'wait_circle'
                    return True
                time.sleep(0.03)
            self.log_signal.emit("⚠️ 未检测到经验，重置")
            self.fishing_state = 'wait_circle'
            return False

        return False

    def set_tracking(self, enabled): self.active_tracking = enabled
    def set_friend(self, enabled): self.accept_friend = enabled
    def set_auto_message(self, enabled): self.auto_message = enabled; self.load_messages()
    def set_message_interval(self, interval): self.message_interval_sec = max(3, interval)
    def set_message_source(self, source): self.message_source_type = source; self.load_messages()
    def set_custom_path(self, path): self.custom_path = path; self.load_messages()
    def set_preset_messages(self, messages): self.preset_messages = messages; self.load_messages()
    def set_fishing(self, enabled): self.fishing_active = enabled; self.fishing_state = 'wait_rod' if enabled else None

    def load_messages(self):
        if self.message_source_type == 0:
            self.message_list = self.preset_messages if self.preset_messages else [
                "你可以把这里的文字,更换成你想要表达的文字！",
                "你好啊！我是稻七学长啊",
                "大家好！王者荣耀世界,好玩吗？"
            ]
        elif self.message_source_type == 3:
            if self.custom_path and os.path.exists(self.custom_path):
                with open(self.custom_path, 'r', encoding='utf-8') as f:
                    self.message_list = [line.strip() for line in f.readlines() if line.strip()]
            else:
                self.message_list = []
                self.log_signal.emit("自定义消息文件不存在或路径无效")
        else:
            self.message_list = ["默认消息"]
        if not self.message_list:
            self.message_list = ["默认消息"]

    def send_next_message(self):
        if not self.message_list:
            return False
        msg = self.message_list[self.message_index]
        self.message_index = (self.message_index + 1) % len(self.message_list)
        import pyperclip
        pyperclip.copy(msg)
        pyautogui.hotkey('ctrl', 'v')
        self.log_signal.emit(f"发送消息: {msg}")
        return True

    def run(self):
        self.running = True
        self.log_signal.emit("自动化线程已启动")

        def press_key(key):
            key_upper = key.upper()
            if key_upper == 'ESC':
                win32api.keybd_event(0x1B, 0, 0, 0)
                time.sleep(0.05)
                win32api.keybd_event(0x1B, 0, win32con.KEYEVENTF_KEYUP, 0)
            elif key_upper in ('ENTER', 'RETURN'):
                win32api.keybd_event(0x0D, 0, 0, 0)
                time.sleep(0.05)
                win32api.keybd_event(0x0D, 0, win32con.KEYEVENTF_KEYUP, 0)
            else:
                vk = ord(key_upper)
                win32api.keybd_event(vk, 0, 0, 0)
                time.sleep(0.05)
                win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

        last_match_time = 0
        frame_interval = 0.08

        while self.running:
            try:
                now = time.time()
                if now - last_match_time < frame_interval:
                    time.sleep(0.01)
                    continue
                last_match_time = now

                if not self.win_mgr.find_window():
                    self.log_signal.emit("窗口丢失，停止")
                    self.running = False
                    break
                self.win_mgr.update_rect()
                self.window_rect_signal.emit(self.win_mgr.rect)

                screenshot = self.win_mgr.capture()
                if screenshot is None or screenshot.size == 0:
                    time.sleep(LOOP_DELAY)
                    continue

                if self.fishing_active:
                    full_screen = ImageGrab.grab()
                    full_gray = cv2.cvtColor(np.array(full_screen), cv2.COLOR_RGB2GRAY)
                    fishing_handled = self.run_fishing(full_gray)
                    if fishing_handled:
                        continue
                    else:
                        time.sleep(0.2)
                        continue

                if self.auto_message:
                    if not self.is_sending and (now - self.last_send_time >= self.message_interval_sec):
                        has_tab = self.matcher.exists(screenshot, WORLD_TAB_IMAGE)
                        if has_tab:
                            self.is_sending = True
                            press_key('ENTER')
                            time.sleep(0.5)
                            dianji_pos = self.matcher.find_template(screenshot, WORLD_DIANJI_IMAGE)
                            if dianji_pos:
                                self.matcher.click_at(self.win_mgr, *dianji_pos)
                                time.sleep(1)
                            send_pos = self.matcher.find_template(screenshot, WORLD_SEND_IMAGE)
                            if send_pos:
                                self.matcher.click_at(self.win_mgr, *send_pos)
                                time.sleep(1)
                            if self.send_next_message():
                                time.sleep(1)
                                press_key('ENTER')
                                self.last_send_time = now
                            self.is_sending = False
                    continue

                if self.accept_friend and self.matcher.exists(screenshot, HAOPENGYOU_IMAGE):
                    press_key('Y')
                    time.sleep(0.5)
                    continue

                if self.active_tracking:
                    if self.matcher.exists(screenshot, SPECIAL_IMAGE):
                        press_key('V')
                        time.sleep(0.01)
                        continue
                    has_q = self.matcher.exists(screenshot, Q_IMAGE)
                    has_esc = self.matcher.exists(screenshot, ESC_IMAGE)
                    if not has_q:
                        if has_esc:
                            press_key('ESC')
                            time.sleep(CLICK_DELAY)
                            continue
                    elif has_q and has_esc:
                        if self.matcher.exists_with_threshold(screenshot, XIA_IMAGE, threshold=0.95):
                            esc_pos = self.matcher.find_template(screenshot, ESC_IMAGE)
                            if esc_pos:
                                self.matcher.click_at(self.win_mgr, *esc_pos)
                                time.sleep(CLICK_DELAY)
                                continue
                        else:
                            renwuone_pos = self.matcher.find_template(screenshot, RENWUONE_IMAGE)
                            if renwuone_pos:
                                self.matcher.click_at(self.win_mgr, *renwuone_pos)
                                time.sleep(CLICK_DELAY)
                                continue
                            else:
                                time.sleep(LOOP_DELAY)
                                continue

                clicked = False
                for img_name in IMAGE_NAMES:
                    pos = self.matcher.find_template(screenshot, img_name)
                    if pos:
                        self.matcher.click_at(self.win_mgr, *pos)
                        clicked = True
                        time.sleep(CLICK_DELAY)
                        break
                if not clicked:
                    time.sleep(LOOP_DELAY)

            except Exception as e:
                self.log_signal.emit(f"运行时错误: {e}")
                time.sleep(0.5)

        self.log_signal.emit("自动化已停止")
        self.finished_signal.emit()

    def stop(self):
        self.running = False

# ======================== 主窗口 ========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.window_manager = WindowManager(WINDOW_TITLE)
        self.image_matcher = ImageMatcher()
        self.automation_thread = None
        self.is_running = False
        self.automation_active = False
        self.game_log = GameLogOverlay()
        self.show_game_log = True

        self.setWindowTitle("王者荣耀世界助手")
        icon_path = get_path("logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setFixedSize(800, 750)
        self.setStyleSheet("""
            QMainWindow { background-color: #050a15; }
            QLabel { color: #00ffcc; }
            QPushButton { background-color: #1a2a3a; color: #00ffcc; border: 2px solid #00ffcc; border-radius: 8px; padding: 8px; }
            QPushButton:hover { background-color: #00ffcc; color: #050a15; }
            QCheckBox { color: #00ffcc; }
            QRadioButton { color: #00ffcc; }
            QTextEdit { background-color: #0a0f1e; color: #00ffcc; border: 2px solid #00ffcc; border-radius: 10px; }
            QGroupBox { color: #00ffcc; border: 1px solid #00ffcc; margin-top: 1ex; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QSpinBox { background-color: #1a2a3a; color: #00ffcc; border: 1px solid #00ffcc; }
            QLineEdit { background-color: #1a2a3a; color: #00ffcc; border: 1px solid #00ffcc; }
            QTabWidget::pane { border: 1px solid #00ffcc; background-color: #050a15; }
            QTabBar::tab { background-color: #1a2a3a; color: #00ffcc; padding: 8px; margin: 2px; border: 1px solid #00ffcc; border-radius: 5px; }
            QTabBar::tab:selected { background-color: #00ffcc; color: #050a15; }
            QTabBar::tab:hover { background-color: #00aacc; }
        """)

        menubar = self.menuBar()
        help_menu = menubar.addMenu("帮助")
        check_update_action = QAction("检查更新", self)
        check_update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_update_action)

        # 创建中央控件（垂直布局）
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ========== 全局控制按钮（启动/停止） ==========
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ 启动 (F12)")
        self.stop_btn = QPushButton("■ 停止 (F12)")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_automation)
        self.stop_btn.clicked.connect(self.stop_automation)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # 标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.tab_task = QWidget()
        self.tab_chat = QWidget()
        self.tab_fishing = QWidget()
        self.tab_collect = QWidget()
        self.tab_other = QWidget()
        self.tab_widget.addTab(self.tab_task, "自动任务")
        self.tab_widget.addTab(self.tab_chat, "自动聊天")
        self.tab_widget.addTab(self.tab_fishing, "自动钓鱼")
        self.tab_widget.addTab(self.tab_collect, "自动采集")
        self.tab_widget.addTab(self.tab_other, "其他功能")

        # ---------- 自动任务标签页 ----------
        layout_task = QVBoxLayout(self.tab_task)
        self.status_label = QLabel("● 状态：📛等待启动")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout_task.addWidget(self.status_label)

        opt_layout1 = QHBoxLayout()
        self.tracking_cb = QCheckBox("主动追踪任务")
        self.tracking_cb.setChecked(True)
        self.tracking_cb.toggled.connect(self.on_tracking_toggled)
        opt_layout1.addWidget(self.tracking_cb)
        opt_layout1.addStretch()
        layout_task.addLayout(opt_layout1)

        opt_layout2 = QHBoxLayout()
        self.friend_cb = QCheckBox("是否接受好友添加")
        self.friend_cb.setChecked(True)
        self.friend_cb.toggled.connect(self.on_friend_toggled)
        opt_layout2.addWidget(self.friend_cb)
        opt_layout2.addStretch()
        layout_task.addLayout(opt_layout2)

        tip = QLabel("提示：F12 启停 | 自动发送消息和自动钓鱼会与其他功能互斥")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("font-size: 11px; color: #88aaff;")
        layout_task.addWidget(tip)
        layout_task.addStretch()

        # ---------- 自动聊天标签页 ----------
        layout_chat = QVBoxLayout(self.tab_chat)
        self.msg_group = QGroupBox("自动发送消息设置")
        self.msg_group.setCheckable(True)
        self.msg_group.setChecked(False)
        self.msg_group.toggled.connect(self.on_auto_message_group_toggled)
        msg_layout = QVBoxLayout(self.msg_group)
        msg_layout.addWidget(QLabel("预设消息1:"))
        self.message_edit1 = QLineEdit()
        self.message_edit1.setText("你可以把这里的文字,更换成你想要表达的文字！")
        msg_layout.addWidget(self.message_edit1)
        msg_layout.addWidget(QLabel("预设消息2:"))
        self.message_edit2 = QLineEdit()
        self.message_edit2.setText("你好啊！我是稻七学长啊")
        msg_layout.addWidget(self.message_edit2)
        msg_layout.addWidget(QLabel("预设消息3:"))
        self.message_edit3 = QLineEdit()
        self.message_edit3.setText("大家好！王者荣耀世界,好玩吗？")
        msg_layout.addWidget(self.message_edit3)
        self.radio_custom = QRadioButton("自定义消息文件")
        self.radio_custom.setChecked(False)
        msg_layout.addWidget(self.radio_custom)
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("文件路径:"))
        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setPlaceholderText("例如 C:/messages.txt")
        custom_layout.addWidget(self.custom_path_edit)
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_custom_file)
        custom_layout.addWidget(self.browse_btn)
        msg_layout.addLayout(custom_layout)
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("发送间隔(秒):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(3, 60)
        self.interval_spin.setValue(5)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        msg_layout.addLayout(interval_layout)
        layout_chat.addWidget(self.msg_group)
        layout_chat.addStretch()

        # ---------- 自动钓鱼标签页 ----------
        layout_fishing = QVBoxLayout(self.tab_fishing)
        self.fishing_enabled_cb = QCheckBox("启用自动钓鱼")
        self.fishing_enabled_cb.setChecked(False)
        self.fishing_enabled_cb.toggled.connect(self.on_fishing_toggled)
        layout_fishing.addWidget(self.fishing_enabled_cb)
        self.fishing_count_label = QLabel("钓鱼次数: 0")
        self.fishing_count_label.setAlignment(Qt.AlignCenter)
        self.fishing_count_label.setStyleSheet("font-size: 14px; color: #ffaa44;")
        layout_fishing.addWidget(self.fishing_count_label)
        layout_fishing.addStretch()

        # 其他标签页占位
        for tab, name in [(self.tab_collect, "采集"), (self.tab_other, "其他")]:
            layout = QVBoxLayout(tab)
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText("功能开发中......\n敬请期待")
            text_edit.setStyleSheet("background-color: #0a0f1e; color: #00ffcc; font-size: 14px;")
            layout.addWidget(text_edit)

        # ========== 全局日志区域 ==========
        chk_layout = QHBoxLayout()
        self.log_cb = QCheckBox("显示游戏内日志")
        self.log_cb.setChecked(True)
        self.log_cb.toggled.connect(self.toggle_game_log)
        chk_layout.addWidget(self.log_cb)
        chk_layout.addStretch()
        main_layout.addLayout(chk_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        init_text = (
            "本程序基于图形识别，无抓包与内存，请放心使用\n"
            "本程序仅供学习交流使用！请勿在游戏中过度使用\n"
            "启动游戏后启动程序，F12启动/停止（管理员方式运行）\n"
            "程序截图基于16:9即1920x1080窗口化\n"
            "自动发送消息需要游戏内打开聊天界面，程序会自动触发。\n"
            "每个功能开启后会自动互斥，请勿同时开启多个功能。\n"
        )
        self.log_text.setPlainText(init_text)
        main_layout.addWidget(self.log_text)

        # 其他初始化
        self.setup_hotkey()
        self.pos_timer = QTimer()
        self.pos_timer.timeout.connect(self.update_overlay_position)
        self.pos_timer.start(200)
        QTimer.singleShot(500, self.check_window_on_start)

    # ======================== 互斥控制 ========================
    def on_fishing_toggled(self, checked):
        if checked:
            self.msg_group.setChecked(False)
            self.tracking_cb.setChecked(False)
            self.friend_cb.setChecked(False)
            self.msg_group.setEnabled(False)
            self.tracking_cb.setEnabled(False)
            self.friend_cb.setEnabled(False)
        else:
            self.msg_group.setEnabled(True)
            self.tracking_cb.setEnabled(True)
            self.friend_cb.setEnabled(True)
        if self.automation_thread:
            self.automation_thread.fishing_enabled.emit(checked)
        self.log(f"自动钓鱼已{'开启' if checked else '关闭'}")

    def on_auto_message_group_toggled(self, checked):
        if checked:
            self.fishing_enabled_cb.setChecked(False)
            self.tracking_cb.setChecked(False)
            self.friend_cb.setChecked(False)
            self.fishing_enabled_cb.setEnabled(False)
            self.tracking_cb.setEnabled(False)
            self.friend_cb.setEnabled(False)
        else:
            self.fishing_enabled_cb.setEnabled(True)
            self.tracking_cb.setEnabled(True)
            self.friend_cb.setEnabled(True)
        if self.automation_thread:
            self.automation_thread.auto_message_enabled.emit(checked)
        self.log(f"自动发送消息已{'开启' if checked else '关闭'}")

    def on_tracking_toggled(self, checked):
        if self.automation_thread:
            self.automation_thread.tracking_enabled.emit(checked)
        self.log(f"主动追踪任务已{'开启' if checked else '关闭'}")

    def on_friend_toggled(self, checked):
        if self.automation_thread:
            self.automation_thread.friend_enabled.emit(checked)
        self.log(f"接受好友添加已{'开启' if checked else '关闭'}")

    def browse_custom_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择消息文件", "", "文本文件 (*.txt)")
        if path:
            self.custom_path_edit.setText(path)
            if self.radio_custom.isChecked() and self.automation_thread:
                self.automation_thread.custom_message_path.emit(path)

    def setup_hotkey(self):
        try:
            keyboard.add_hotkey('f12', self.toggle_automation)
            self.log("快捷键 F12 设置成功")
        except Exception as e:
            self.log(f"快捷键设置失败以管理员方式运行: {e}")

    def toggle_automation(self):
        QTimer.singleShot(0, self._toggle_automation_safe)

    def _toggle_automation_safe(self):
        if self.is_running:
            self.stop_automation()
        else:
            self.start_automation()

    def check_window_on_start(self):
        if not self.window_manager.find_window():
            QMessageBox.warning(self, "窗口未找到", "请先打开【王者荣耀世界】窗口！")
            self.log("未找到游戏窗口")
        else:
            self.log("已找到游戏窗口，按 F12 启动")

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        self.log_text.append(formatted)
        if self.show_game_log:
            self.game_log.append_log(formatted)

    def toggle_game_log(self, checked):
        self.show_game_log = checked
        if checked and self.window_manager.rect:
            self.game_log.update_position(self.window_manager.rect)
            self.game_log.set_visible(True)
        else:
            self.game_log.set_visible(False)

    def start_automation(self):
        if self.is_running:
            return
        if not self.window_manager.find_window():
            QMessageBox.warning(self, "错误", "未找到游戏窗口")
            return
        self.automation_thread = AutomationThread(self.window_manager, self.image_matcher)
        self.automation_thread.log_signal.connect(self.log)
        self.automation_thread.finished_signal.connect(self.on_automation_finished)
        self.automation_thread.window_rect_signal.connect(self.on_window_rect_update)

        self.automation_thread.tracking_enabled.emit(self.tracking_cb.isChecked())
        self.automation_thread.friend_enabled.emit(self.friend_cb.isChecked())
        self.automation_thread.auto_message_enabled.emit(self.msg_group.isChecked())
        self.automation_thread.fishing_enabled.emit(self.fishing_enabled_cb.isChecked())

        if self.msg_group.isChecked():
            self.automation_thread.message_interval.emit(self.interval_spin.value())
            if not self.radio_custom.isChecked():
                preset = [
                    self.message_edit1.text(),
                    self.message_edit2.text(),
                    self.message_edit3.text()
                ]
                self.automation_thread.preset_messages_signal.emit(preset)
                self.automation_thread.message_source.emit(0)
            else:
                self.automation_thread.message_source.emit(3)
                self.automation_thread.custom_message_path.emit(self.custom_path_edit.text())

        self.automation_thread.start()
        self.is_running = True
        self.automation_active = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("● 状态：✅ 运行中")
        self.status_label.setStyleSheet("color: #00ff66;")
        self.log("自动化已启动")

        if self.show_game_log and self.window_manager.find_window():
            self.game_log.update_position(self.window_manager.rect)
            self.game_log.set_visible(True)

    def stop_automation(self):
        if not self.is_running:
            return
        if self.automation_thread:
            self.automation_thread.stop()
        self.is_running = False
        self.automation_active = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("● 状态：已停止")
        self.status_label.setStyleSheet("color: #ffaa44;")
        self.log("自动化已停止")
        self.game_log.set_visible(False)

    def update_overlay_position(self):
        if not self.automation_active:
            return
        if self.show_game_log:
            if self.window_manager.find_window():
                self.game_log.update_position(self.window_manager.rect)
                if not self.game_log.isVisible():
                    self.game_log.set_visible(True)
            else:
                self.game_log.set_visible(False)

    def on_automation_finished(self):
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("● 状态：已停止")
        self.automation_thread = None

    def on_window_rect_update(self, rect):
        if rect:
            self.window_manager.rect = rect
            if self.show_game_log:
                self.game_log.update_position(rect)

    def closeEvent(self, event):
        self.stop_automation()
        self.game_log.close()
        try:
            keyboard.unhook_all()
        except:
            pass
        event.accept()

    def check_for_updates(self):
        self.log("正在检查更新...")
        self.update_manager = QNetworkAccessManager()
        self.update_manager.finished.connect(self.on_update_response)
        url = QUrl("https://api.github.com/repos/daoqi/Honor-of-Kings-World-wangzherongyaoshijiezidonghua/releases/latest")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "Mozilla/5.0")
        self.update_manager.get(request)

    def on_update_response(self, reply):
        if reply.error() != QNetworkReply.NoError:
            self.log(f"检查更新失败: {reply.errorString()}")
            reply.deleteLater()
            return
        data = reply.readAll().data().decode('utf-8')
        reply.deleteLater()
        try:
            import json
            info = json.loads(data)
            tag = info.get("tag_name", "")
            if tag.startswith("v"):
                tag = tag[1:]
            release_url = info.get("html_url", "")
            try:
                import version
                current = version.version
            except:
                current = "0.0.0"
            if tag > current:
                reply_box = QMessageBox.question(self, "发现新版本",
                                                 f"当前版本: {current}\n最新版本: {tag}\n\n是否前往下载？",
                                                 QMessageBox.Yes | QMessageBox.No)
                if reply_box == QMessageBox.Yes:
                    QDesktopServices.openUrl(QUrl(release_url))
            else:
                QMessageBox.information(self, "检查更新", f"当前已是最新版本 ({current})")
        except Exception as e:
            self.log(f"解析更新信息失败: {e}")

if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    app = QApplication(sys.argv)
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="sip")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())