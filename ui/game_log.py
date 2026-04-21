# -*- coding: utf-8 -*-
"""游戏内透明日志窗口"""
from PyQt5.QtWidgets import QWidget, QTextEdit, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor


class GameLogOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0,0,0,180); color:#00ffcc; border:1px solid #00ffcc; border-radius:8px;")
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet("background:transparent; color:#00ffcc; font-family:'Consolas'; font-size:11px; border:none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.text_edit)
        self.resize(320, 300)
        self.hide()

    def append_log(self, text):
        self.text_edit.append(text)
        doc = self.text_edit.document()
        if doc.blockCount() > 20:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self.text_edit.moveCursor(QTextCursor.End)

    def update_position(self, game_rect):
        if game_rect:
            x = game_rect["left"] + 0
            y = game_rect["top"] + 300
            self.move(x, y)

    def set_visible(self, visible):
        if visible:
            self.show()
            self.raise_()
        else:
            self.hide()