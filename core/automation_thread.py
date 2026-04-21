# -*- coding: utf-8 -*-
"""自动化工作线程"""
import time
import win32api
import win32con
from PyQt5.QtCore import QThread, pyqtSignal

import config
from utils.helpers import random_sleep
from core.window_manager import WindowManager
from core.image_matcher import ImageMatcher


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

        self.tracking_enabled.connect(self.set_tracking)
        self.friend_enabled.connect(self.set_friend)
        self.auto_message_enabled.connect(self.set_auto_message)
        self.message_interval.connect(self.set_message_interval)
        self.message_source.connect(self.set_message_source)
        self.custom_message_path.connect(self.set_custom_path)
        self.preset_messages_signal.connect(self.set_preset_messages)

    def set_tracking(self, enabled):
        self.active_tracking = enabled

    def set_friend(self, enabled):
        self.accept_friend = enabled

    def set_auto_message(self, enabled):
        self.auto_message = enabled
        self.load_messages()

    def set_message_interval(self, interval):
        self.message_interval_sec = max(3, interval)

    def set_message_source(self, source):
        self.message_source_type = source
        self.load_messages()

    def set_custom_path(self, path):
        self.custom_path = path
        self.load_messages()

    def set_preset_messages(self, messages):
        self.preset_messages = messages
        self.load_messages()

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
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        random_sleep(0.01, 0.05)
        win32api.keybd_event(ord('V'), 0, 0, 0)
        random_sleep(0.02, 0.06)
        win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        self.log_signal.emit(f"发送消息: {msg}")
        return True

    def run(self):
        try:
            self.running = True
            self.log_signal.emit("任务自动化线程已启动")

            def press_key(key):
                key_upper = key.upper()
                self.log_signal.emit(f"按下按键: {key_upper}")
                random_sleep(0.01, 0.06)
                if key_upper == 'ESC':
                    win32api.keybd_event(0x1B, 0, 0, 0)
                    random_sleep(0.04, 0.08)
                    win32api.keybd_event(0x1B, 0, win32con.KEYEVENTF_KEYUP, 0)
                elif key_upper in ('ENTER', 'RETURN'):
                    win32api.keybd_event(0x0D, 0, 0, 0)
                    random_sleep(0.04, 0.08)
                    win32api.keybd_event(0x0D, 0, win32con.KEYEVENTF_KEYUP, 0)
                else:
                    vk = ord(key_upper)
                    win32api.keybd_event(vk, 0, 0, 0)
                    random_sleep(0.04, 0.08)
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
                        time.sleep(config.LOOP_DELAY)
                        continue

                    # 自动聊天
                    if self.auto_message:
                        if not self.is_sending and (now - self.last_send_time >= self.message_interval_sec):
                            has_tab = self.matcher.exists(screenshot, config.WORLD_TAB_IMAGE)
                            if has_tab:
                                self.log_signal.emit("检测到聊天标签，准备发送消息")
                                self.is_sending = True
                                press_key('ENTER')
                                random_sleep(0.3, 0.7)
                                dianji_pos = self.matcher.find_template(screenshot, config.WORLD_DIANJI_IMAGE)
                                if dianji_pos:
                                    self.log_signal.emit("点击输入框")
                                    self.matcher.click_at(self.win_mgr, *dianji_pos, log_callback=self.log_signal.emit)
                                    random_sleep(0.8, 1.2)
                                send_pos = self.matcher.find_template(screenshot, config.WORLD_SEND_IMAGE)
                                if send_pos:
                                    self.log_signal.emit("点击发送按钮")
                                    self.matcher.click_at(self.win_mgr, *send_pos, log_callback=self.log_signal.emit)
                                    random_sleep(0.8, 1.2)
                                if self.send_next_message():
                                    random_sleep(0.8, 1.2)
                                    press_key('ENTER')
                                    self.last_send_time = now
                                self.is_sending = False
                        continue

                    # 好友添加
                    if self.accept_friend and self.matcher.exists(screenshot, config.HAOPENGYOU_IMAGE):
                        self.log_signal.emit("检测到好友添加请求，按下Y键")
                        press_key('Y')
                        random_sleep(0.4, 0.8)
                        continue

                    # 任务追踪
                    if self.active_tracking:
                        if self.matcher.exists(screenshot, config.SPECIAL_IMAGE):
                            self.log_signal.emit("检测到任务追踪图标，按下V键")
                            press_key('V')
                            random_sleep(0.01, 0.03)
                            continue
                        has_q = self.matcher.exists(screenshot, config.Q_IMAGE)
                        has_esc = self.matcher.exists(screenshot, config.ESC_IMAGE)
                        if not has_q:
                            if has_esc:
                                self.log_signal.emit("检测到ESC提示，按下ESC键")
                                press_key('ESC')
                                random_sleep(config.CLICK_DELAY, config.CLICK_DELAY + 0.05)
                                continue
                        elif has_q and has_esc:
                            if self.matcher.exists_with_threshold(screenshot, config.XIA_IMAGE, threshold=0.95):
                                self.log_signal.emit("检测到'下'按钮，点击ESC")
                                esc_pos = self.matcher.find_template(screenshot, config.ESC_IMAGE)
                                if esc_pos:
                                    self.matcher.click_at(self.win_mgr, *esc_pos, log_callback=self.log_signal.emit)
                                    random_sleep(config.CLICK_DELAY, config.CLICK_DELAY + 0.05)
                                    continue
                            else:
                                renwuone_pos = self.matcher.find_template(screenshot, config.RENWUONE_IMAGE)
                                if renwuone_pos:
                                    self.log_signal.emit("检测到任务一，点击")
                                    self.matcher.click_at(self.win_mgr, *renwuone_pos, log_callback=self.log_signal.emit)
                                    random_sleep(config.CLICK_DELAY, config.CLICK_DELAY + 0.05)
                                    continue
                                else:
                                    time.sleep(config.LOOP_DELAY)
                                    continue

                    # 普通按钮
                    clicked = False
                    for img_name in config.IMAGE_NAMES:
                        pos = self.matcher.find_template(screenshot, img_name)
                        if pos:
                            self.log_signal.emit(f"检测到按钮: {img_name}，点击")
                            self.matcher.click_at(self.win_mgr, *pos, log_callback=self.log_signal.emit)
                            clicked = True
                            random_sleep(config.CLICK_DELAY, config.CLICK_DELAY + 0.05)
                            break
                    if not clicked:
                        time.sleep(config.LOOP_DELAY)

                except Exception as e:
                    self.log_signal.emit(f"运行时错误: {e}")
                    import traceback
                    self.log_signal.emit(traceback.format_exc())
                    time.sleep(0.5)

        except Exception as e:
            self.log_signal.emit(f"线程致命错误: {e}")
            import traceback
            self.log_signal.emit(traceback.format_exc())
        finally:
            self.log_signal.emit("任务自动化已停止")
            self.finished_signal.emit()

    def stop(self):
        self.running = False