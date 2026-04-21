import sys
import json
from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

class AutoUpdater(QObject):
    """自动更新检查器"""
    update_available = pyqtSignal(str, str)  # 新版本号, 下载地址
    check_finished = pyqtSignal()            # 检查完成信号
    error_occurred = pyqtSignal(str)         # 错误信号

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.on_reply_finished)

    def check_for_updates(self):
        """检查 GitHub 是否有新版本"""
        url = "https://api.github.com/repos/daoqi/Honor-of-Kings-World-wangzherongyaoshijiezidonghua/releases/latest"
        self.manager.get(QNetworkRequest(QUrl(url)))

    def on_reply_finished(self, reply):
        """处理 GitHub API 返回的 JSON 数据"""
        if reply.error():
            self.error_occurred.emit(f"网络错误: {reply.errorString()}")
        else:
            try:
                data = json.loads(bytes(reply.readAll()).decode('utf-8'))
                latest_version = data.get('tag_name', '').lstrip('v')
                if latest_version > self.current_version:
                    # 获取对应平台的下载链接，这里以 .exe 为例
                    download_url = None
                    for asset in data.get('assets', []):
                        if asset['name'].endswith('.exe'):
                            download_url = asset['browser_download_url']
                            break
                    if download_url:
                        self.update_available.emit(latest_version, download_url)
                    else:
                        self.error_occurred.emit("未找到更新文件")
                else:
                    self.check_finished.emit()
            except Exception as e:
                self.error_occurred.emit(f"解析更新信息失败: {e}")
        reply.deleteLater()