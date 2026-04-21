# -*- coding: utf-8 -*-
"""AI视角显示窗口"""
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage


class AIDisplayWindow(QWidget):
    close_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 视角 (AI看到了什么)")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setFixedSize(800, 600)
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 2px solid #0ff; background-color: #000;")
        self.video_label.setScaledContents(True)
        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        self.setLayout(layout)

    def update_frame(self, img_bytes, w, h):
        qimg = QImage.fromData(img_bytes)
        pixmap = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pixmap)

    def closeEvent(self, event):
        self.close_signal.emit()
        event.accept()