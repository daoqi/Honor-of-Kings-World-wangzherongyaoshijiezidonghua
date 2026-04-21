# -*- coding: utf-8 -*-
"""主窗口UI"""
import sys
import os
import time
import json
import keyboard
import pyautogui
import win32gui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QDesktopServices, QKeySequence
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from core.window_manager import WindowManager
from core.image_matcher import ImageMatcher
from core.automation_thread import AutomationThread
from fishing.fishing_thread import FishingThread
from ui.ai_display import AIDisplayWindow
from ui.game_log import GameLogOverlay
from utils.helpers import get_path
from utils.version_utils import get_current_version
from utils.auto_updater import AutoUpdater
from version import version

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.window_manager = WindowManager("王者荣耀世界")
        self.image_matcher = ImageMatcher()
        self.automation_thread = None
        self.is_running = False
        self.automation_active = False
        self.game_log = GameLogOverlay()
        self.show_game_log = True

        self.fishing_thread = None
        self.fishing_running = False
        self.ai_display_window = None

        self.setWindowTitle("HOK AI")
        icon_path = get_path("logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setFixedSize(1000, 750)
        self.setup_ui()
        self.setup_hotkeys()
        self.pos_timer = QTimer()
        self.pos_timer.timeout.connect(self.update_overlay_position)
        self.pos_timer.start(500)
        QTimer.singleShot(500, self.check_window_on_start)

        self.log("程序启动，请选择游戏窗口后启动AI钓鱼或任务。")
        self.log("获取最新AI版本加入QQ群1098948146")
        self.check_for_updates()   # 自动更新检查

    # ==================== UI 构建 ====================
    def setup_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #050a15; }
            QLabel { color: #00ffcc; }
            QPushButton { background-color: #1a2a3a; color: #00ffcc; border: 2px solid #00ffcc; border-radius: 8px; padding: 8px; }
            QPushButton:hover { background-color: #00ffcc; color: #050a15; }
            QCheckBox { color: #00ffcc; }
            QRadioButton { color: #00ffcc; }
            QTextEdit { background-color: #0a0f1e; color: #00ffcc; border: 2px solid #00ffcc; border-radius: 10px; }
            QGroupBox { color: #00ffcc; border: 1px solid #00ffcc; margin-top: 1ex; background-color: rgba(0,255,255,0.05); }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QSpinBox { background-color: #1a2a3a; color: #00ffcc; border: 1px solid #00ffcc; }
            QDoubleSpinBox { background-color: #1a2a3a; color: #00ffcc; border: 1px solid #00ffcc; }
            QComboBox { background-color: #0a0f1e; color: #00ffcc; border: 1px solid #00ffcc; border-radius: 4px; padding: 2px; }
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

        about_menu = menubar.addMenu("关于")
        join_action = QAction("加入我们", self)
        join_action.triggered.connect(self.copy_qq)
        about_menu.addAction(join_action)
        group_action = QAction("加群链接", self)
        group_action.triggered.connect(self.open_group_link)
        about_menu.addAction(group_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ 启动 (Alt+F12)")
        self.stop_btn = QPushButton("■ 停止 (Alt+F12)")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.toggle_automation)
        self.stop_btn.clicked.connect(self.stop_current_function)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.tab_task = QWidget()
        self.tab_chat = QWidget()
        self.tab_fishing = QWidget()
        self.tab_collect = QWidget()
        self.tab_other = QWidget()
        self.tab_widget.addTab(self.tab_task, "自动任务")
        self.tab_widget.addTab(self.tab_chat, "自动聊天")
        self.tab_widget.addTab(self.tab_fishing, "AI钓鱼")
        self.tab_widget.addTab(self.tab_collect, "自动采集")
        self.tab_widget.addTab(self.tab_other, "等更新")

        self.setup_task_tab()
        self.setup_chat_tab()
        self.setup_fishing_tab()

        for tab, name in [(self.tab_collect, "采集"), (self.tab_other, "其他")]:
            layout = QVBoxLayout(tab)
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText("功能开发中......\n敬请期待")
            text_edit.setStyleSheet("background-color: #0a0f1e; color: #00ffcc; font-size: 14px;")
            layout.addWidget(text_edit)

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
            "启动游戏后启动程序，Alt+F12启动/停止任务，F12控制AI钓鱼检测，F11开关AI自动操作\n"
            "程序截图基于16:9即1920x1080窗口化\n"
            "自动发送消息需要游戏内打开聊天界面，程序会自动触发。\n"
            "每个功能开启后会自动互斥，请勿同时开启多个功能。\n"
            "Alt+F12 将启动/停止当前选中的功能（任务或钓鱼）。\n"
            "AI模型请放置于 mode/best.pt\n"
        )
        self.log_text.setPlainText(init_text)
        main_layout.addWidget(self.log_text)

    def setup_task_tab(self):
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

        tip = QLabel("提示：Alt+F12 启动/停止当前选中的功能（任务或钓鱼）")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("font-size: 11px; color: #88aaff;")
        layout_task.addWidget(tip)
        layout_task.addStretch()

    def setup_chat_tab(self):
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

    def setup_fishing_tab(self):
        layout_fishing = QVBoxLayout(self.tab_fishing)

        win_group = QGroupBox("游戏窗口")
        win_layout = QHBoxLayout()
        self.window_combo = QComboBox()
        self.refresh_btn = QPushButton("刷新窗口列表")
        self.refresh_btn.clicked.connect(self.refresh_window_list)
        win_layout.addWidget(self.window_combo)
        win_layout.addWidget(self.refresh_btn)
        win_group.setLayout(win_layout)
        layout_fishing.addWidget(win_group)

        ctrl_group = QGroupBox("AI 钓鱼控制")
        ctrl_layout = QHBoxLayout()
        self.start_ai_btn = QPushButton("启动检测 (F12)")
        self.stop_ai_btn = QPushButton("停止检测")
        self.stop_ai_btn.setEnabled(False)
        self.start_ai_btn.clicked.connect(self.start_ai_detection)
        self.stop_ai_btn.clicked.connect(self.stop_ai_detection)
        ctrl_layout.addWidget(self.start_ai_btn)
        ctrl_layout.addWidget(self.stop_ai_btn)
        ctrl_group.setLayout(ctrl_layout)
        layout_fishing.addWidget(ctrl_group)

        self.ai_enable_cb = QCheckBox("启用 AI 自动操作 (F11)")
        self.ai_enable_cb.stateChanged.connect(self.on_ai_enable_toggled)
        layout_fishing.addWidget(self.ai_enable_cb)

        self.ai_display_cb = QCheckBox("显示AI视角窗口")
        self.ai_display_cb.setChecked(False)
        self.ai_display_cb.stateChanged.connect(self.toggle_ai_display)
        layout_fishing.addWidget(self.ai_display_cb)

        param_group = QGroupBox("参数设置")
        param_layout = QGridLayout()
        param_layout.addWidget(QLabel("识别阈值:"), 0, 0)
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.0, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.6)
        self.conf_spin.valueChanged.connect(self.on_conf_changed)
        param_layout.addWidget(self.conf_spin, 0, 1)
        param_layout.addWidget(QLabel("超时重置(秒):"), 1, 0)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(45)
        self.timeout_spin.valueChanged.connect(self.on_timeout_changed)
        param_layout.addWidget(self.timeout_spin, 1, 1)
        param_group.setLayout(param_layout)
        layout_fishing.addWidget(param_group)

        stats_group = QGroupBox("钓鱼统计")
        stats_layout = QVBoxLayout()
        self.fish_count_label = QLabel("当前鱼获次数: 0")
        self.fish_count_label.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.fish_count_label)
        stats_group.setLayout(stats_layout)
        layout_fishing.addWidget(stats_group)
        layout_fishing.addStretch()

    # ==================== 任务相关方法 ====================
    def on_tracking_toggled(self, checked):
        if self.automation_thread:
            self.automation_thread.tracking_enabled.emit(checked)
        self.log(f"主动追踪任务已{'开启' if checked else '关闭'}")

    def on_friend_toggled(self, checked):
        if self.automation_thread:
            self.automation_thread.friend_enabled.emit(checked)
        self.log(f"接受好友添加已{'开启' if checked else '关闭'}")

    def on_auto_message_group_toggled(self, checked):
        if checked:
            self.ai_enable_cb.setChecked(False)
            self.tracking_cb.setChecked(False)
            self.friend_cb.setChecked(False)
            self.ai_enable_cb.setEnabled(False)
            self.tracking_cb.setEnabled(False)
            self.friend_cb.setEnabled(False)
        else:
            self.ai_enable_cb.setEnabled(True)
            self.tracking_cb.setEnabled(True)
            self.friend_cb.setEnabled(True)
        if self.automation_thread:
            self.automation_thread.auto_message_enabled.emit(checked)
        self.log(f"自动发送消息已{'开启' if checked else '关闭'}")

    def start_automation(self):
        if self.is_running:
            return
        if self.fishing_thread and self.fishing_thread.detection_enabled:
            self.stop_ai_detection()
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
        self.status_label.setText("● 状态：✅ 任务自动化运行中")
        self.status_label.setStyleSheet("color: #00ff66;")
        self.log("任务自动化已启动")
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
        self.log("任务自动化已停止")
        self.game_log.set_visible(False)

    def on_automation_finished(self):
        self.is_running = False
        self.automation_active = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("● 状态：已停止")
        self.automation_thread = None
        self.game_log.set_visible(False)

    def on_window_rect_update(self, rect):
        if rect and self.automation_active and self.show_game_log:
            self.game_log.update_position(rect)

    # ==================== AI 钓鱼相关 ====================
    def refresh_window_list(self):
        self.window_combo.clear()

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                self.window_combo.addItem(f"{win32gui.GetWindowText(hwnd)} (0x{hwnd:X})", hwnd)

        win32gui.EnumWindows(enum_callback, None)
        if self.window_combo.count() > 0:
            self.log(f"已找到 {self.window_combo.count()} 个窗口，请选择游戏窗口。")

    def start_ai_detection(self):
        idx = self.window_combo.currentIndex()
        if idx < 0:
            self.log("请先选择一个窗口！")
            return
        hwnd = self.window_combo.currentData()
        if self.fishing_thread is None:
            self.fishing_thread = FishingThread()
            self.fishing_thread.log_signal.connect(self.log)
            self.fishing_thread.fish_count_signal.connect(self.update_fish_count)
            self.fishing_thread.finished_signal.connect(self.on_fishing_finished)
            self.fishing_thread.frame_signal.connect(self.on_frame_received)
            self.fishing_thread.start()
        if not self.fishing_thread.set_game_window(hwnd):
            self.log("窗口设置失败，请重新选择")
            return
        self.fishing_thread.set_detection_enabled(True)
        self.start_ai_btn.setEnabled(False)
        self.stop_ai_btn.setEnabled(True)
        self.window_combo.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.log("AI检测已启动")
        self.fishing_thread.set_ai_enabled(self.ai_enable_cb.isChecked())

    def stop_ai_detection(self):
        if self.fishing_thread:
            self.fishing_thread.set_detection_enabled(False)
        self.start_ai_btn.setEnabled(True)
        self.stop_ai_btn.setEnabled(False)
        self.window_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.log("AI检测已停止")

    def on_ai_enable_toggled(self, state):
        if self.fishing_thread:
            self.fishing_thread.set_ai_enabled(state == Qt.Checked)
        self.log(f"AI自动操作{'已启用' if state else '已禁用'}")

    def on_conf_changed(self, value):
        if self.fishing_thread:
            self.fishing_thread.global_conf = value
        self.log(f"AI识别阈值已更改为: {value:.2f}")

    def on_timeout_changed(self, value):
        if self.fishing_thread:
            self.fishing_thread.cast_timeout = float(value)
        self.log(f"AI超时重置时间已更改为: {value} 秒")

    def update_fish_count(self, count):
        self.fish_count_label.setText(f"当前鱼获次数: {count}")

    def on_fishing_finished(self):
        self.fishing_running = False
        self.fishing_thread = None
        self.log("AI钓鱼线程已结束")
        self.start_ai_btn.setEnabled(True)
        self.stop_ai_btn.setEnabled(False)
        self.window_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)

    def on_frame_received(self, img_bytes, w, h):
        if self.ai_display_window and self.ai_display_cb.isChecked():
            self.ai_display_window.update_frame(img_bytes, w, h)

    def toggle_ai_display(self, state):
        if state == Qt.Checked:
            if self.ai_display_window is None:
                self.ai_display_window = AIDisplayWindow(self)
                self.ai_display_window.close_signal.connect(self.on_ai_display_closed)
            self.ai_display_window.show()
            if self.fishing_thread:
                self.fishing_thread.set_display_enabled(True)
            else:
                self.log("请先启动AI检测，才能显示AI视角窗口")
                self.ai_display_cb.setChecked(False)
        else:
            if self.ai_display_window:
                if self.fishing_thread:
                    self.fishing_thread.set_display_enabled(False)
                self.ai_display_window.close()
                self.ai_display_window = None

    def on_ai_display_closed(self):
        self.ai_display_cb.setChecked(False)
        if self.fishing_thread:
            self.fishing_thread.set_display_enabled(False)
        self.ai_display_window = None

    # ==================== 全局控制 ====================
    def toggle_automation(self):
        now = time.time()
        if hasattr(self, '_last_auto_time') and now - self._last_auto_time < 0.5:
            return
        self._last_auto_time = now

        if self.is_running:
            self.stop_automation()
            return
        if self.fishing_thread and self.fishing_thread.detection_enabled:
            self.stop_ai_detection()
            return

        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:
            if not self.tracking_cb.isChecked() and not self.msg_group.isChecked():
                QMessageBox.information(self, "提示", "请在自动任务标签页勾选「主动追踪任务」或「自动发送消息」")
                return
            self.start_automation()
        elif current_tab == 2:
            if self.window_combo.currentIndex() < 0:
                QMessageBox.information(self, "提示", "请先选择游戏窗口")
                return
            self.start_ai_detection()
        else:
            QMessageBox.information(self, "提示", "请切换到「自动任务」或「自动钓鱼」标签页后再按 Alt+F12")

    def stop_current_function(self):
        if self.is_running:
            self.stop_automation()
        elif self.fishing_thread and self.fishing_thread.detection_enabled:
            self.stop_ai_detection()
        else:
            self.log("没有正在运行的功能")

    # ==================== 热键 ====================
    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('alt+f12', self.toggle_automation)
            self.log("全局热键 Alt+F12 注册成功")
        except Exception as e:
            self.log(f"注册 Alt+F12 失败: {e}")
        try:
            keyboard.add_hotkey('f12', self.toggle_ai_detection)
            self.log("全局热键 F12 注册成功 (启动/停止AI检测)")
        except Exception as e:
            self.log(f"注册 F12 失败: {e}")
        try:
            keyboard.add_hotkey('f11', self.toggle_ai_auto)
            self.log("全局热键 F11 注册成功 (开关AI自动操作)")
        except Exception as e:
            self.log(f"注册 F11 失败: {e}")

    def toggle_ai_detection(self):
        if self.fishing_thread and self.fishing_thread.detection_enabled:
            self.stop_ai_detection()
        else:
            self.start_ai_detection()

    def toggle_ai_auto(self):
        self.ai_enable_cb.setChecked(not self.ai_enable_cb.isChecked())

    # ==================== 辅助功能 ====================
    def browse_custom_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择消息文件", "", "文本文件 (*.txt)")
        if path:
            self.custom_path_edit.setText(path)
            if self.radio_custom.isChecked() and self.automation_thread:
                self.automation_thread.custom_message_path.emit(path)

    def check_window_on_start(self):
        if not self.window_manager.find_window():
            QMessageBox.warning(self, "窗口未找到", "请先打开【王者荣耀世界】窗口！")
            self.log("未找到游戏窗口")
        else:
            self.log("已找到游戏窗口，按 Alt+F12 启动任务，或切换到钓鱼标签页按 F12 启动AI钓鱼")

    def toggle_game_log(self, checked):
        self.show_game_log = checked
        if checked and self.automation_active and self.window_manager.rect:
            self.game_log.update_position(self.window_manager.rect)
            self.game_log.set_visible(True)
        else:
            self.game_log.set_visible(False)

    def update_overlay_position(self):
        if not self.automation_active:
            if self.game_log.isVisible():
                self.game_log.set_visible(False)
            return
        if self.show_game_log:
            if self.window_manager.find_window():
                self.window_manager.update_rect()
                self.game_log.update_position(self.window_manager.rect)
                if not self.game_log.isVisible():
                    self.game_log.set_visible(True)
            else:
                self.game_log.set_visible(False)

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        self.log_text.append(formatted)
        if self.show_game_log and self.automation_active:
            self.game_log.append_log(formatted)

    def copy_qq(self):
        qq_number = "1098948146"
        clipboard = QApplication.clipboard()
        clipboard.setText(qq_number)
        QMessageBox.information(self, "提示", f"QQ号 {qq_number} 已复制到剪贴板")

    def open_group_link(self):
        url = "https://qm.qq.com/q/1dbk294PM8"
        QDesktopServices.openUrl(QUrl(url))

    # ==================== 自动更新（使用 AutoUpdater） ====================
    def check_for_updates(self):
        """检查 GitHub 是否有新版本"""
        self.log("正在检查更新...")
        self.updater = AutoUpdater(version)
        self.updater.update_available.connect(self.on_update_available)
        self.updater.check_finished.connect(self.on_update_not_available)
        self.updater.error_occurred.connect(self.on_update_error)
        self.updater.check_for_updates()

    def on_update_available(self, new_version, download_url):
        """发现新版本时弹出询问对话框"""
        reply = QMessageBox.question(
            self,
            "发现新版本",
            f"当前版本 v{version}\n最新版本 v{new_version}\n\n是否前往下载更新？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            import webbrowser
            webbrowser.open(download_url)

    def on_update_not_available(self):
        """当前已是最新版本，静默处理"""
        self.log("当前已是最新版本")

    def on_update_error(self, error_msg):
        """更新检查出错时记录错误"""
        self.log(f"更新检查失败: {error_msg}")

    # ==================== 窗口关闭事件 ====================
    def closeEvent(self, event):
        self.stop_automation()
        if self.fishing_thread:
            self.fishing_thread.stop()
            self.fishing_thread.wait(2000)
        if self.ai_display_window:
            self.ai_display_window.close()
        self.game_log.close()
        try:
            keyboard.unhook_all()
        except:
            pass
        event.accept()