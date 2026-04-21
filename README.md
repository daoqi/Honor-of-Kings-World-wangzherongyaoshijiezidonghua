# 王者荣耀世界自动

下载安装
1. 前往 [Releases](https://github.com/daoqi/Honor-of-Kings-World-wangzherongyaoshijiezidonghua/releases) 页面下载最新版本的 `HOK world AI.exe`。
### 百度网盘
链接: https://pan.baidu.com/s/1p31Fbyw6TkAFujtBGder1g?pwd=d5pw  
提取码: d5pw
### 迅雷云盘
分享文件：王者荣耀世界  
链接：https://pan.xunlei.com/s/VOqB-Hm9l59AgGkYLfUchvfEA1?pwd=6fig
### 蓝奏云
https://www.ilanzou.com/s/1fz6woCU
## 使用说明
-任务在任何界面启动都可以
-钓鱼需要再钓鱼界面在启动
-注意:自动发送消息!别乱用！你不怕被封号你就用！被举报一定会封号！
- 基于 OpenCV2 + YOLOv8 图形识别
- 图片基于电脑 16:9 分辨率下截取
- 需要把游戏窗口化 1920x1080 100%缩放，不然可能识图不准确
- **窗口化游戏 ↑ 窗口化游戏 ↑ 窗口化游戏 ↑**
- 窗口可以是任意位置，但必须为窗口化模式
# HOK AI - 王者荣耀世界自动化助手
[![Version](https://img.shields.io/badge/version-2.3.10-blue.svg)](https://github.com/daoqi/Honor-of-Kings-World-wangzherongyaoshijiezidonghua/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
## 📖 简介
基于 **YOLO AI 模型** + **PyQt5** 开发的《王者荣耀世界》游戏辅助工具，提供自动任务、AI 钓鱼、自动聊天等功能。纯图形识别，不涉及内存读写，安全可靠。
## ✨ 主要功能
- 🎣 **AI 自动钓鱼**  
  使用 YOLO 模型识别游戏中的鱼钩、挣扎动作、经验获取等状态，自动抛竿、拉杆、挣扎，支持大鱼小鱼识别。
- 🤖 **自动任务**  
  自动追踪任务、接受好友申请、点击各类按钮，解放双手。
- 💬 **自动聊天**  
  支持预设消息和自定义消息文件，自动在世界频道发送消息。
- 🔄 **自动更新**  
  启动时检查 GitHub 新版本，发现新版本时提示用户下载。
- 🖥️ **AI 视角窗口**  
  实时显示 AI 看到的画面（带检测框），方便调试。
## 🚀 快速开始
### 下载安装
1. 前往 [Releases](https://github.com/daoqi/Honor-of-Kings-World-wangzherongyaoshijiezidonghua/releases) 页面下载最新版本的 `HOK world AI.exe`。
2. 将 `mode/best.pt` 模型文件放置于 exe 同目录下的 `mode` 文件夹中（或首次运行时自动下载）。
3. 运行 `HOK world AI.exe`。

### 使用说明
- 游戏需**窗口化**运行，分辨率建议 **1920x1080**，缩放 **100%**。
- 启动程序后，选择游戏窗口（标题含“王者荣耀世界”）。
- **Alt+F12**：启动/停止当前选中的功能（任务或钓鱼）。
- **F12**：启动/停止 AI 钓鱼检测。
- **F11**：开关 AI 自动操作（钓鱼时启用）。

## 🛠️ 开发环境

- Python 3.10
- PyQt5 5.15.10
- PyTorch 2.5.0 (CPU)
- Ultralytics 8.x
- OpenCV, pywin32, pyautogui, keyboard, mss 等

## 📦 自行打包

```bash
# 激活虚拟环境（Python 3.10）
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "HOK world AI" --icon logo.ico --add-data "mode/best.pt;mode" --add-data "core;core" --add-data "fishing;fishing" --add-data "ui;ui" --add-data "utils;utils" --add-data "version.py;." --collect-all torch --collect-all ultralytics --exclude-module onnx --exclude-module onnxruntime main.py