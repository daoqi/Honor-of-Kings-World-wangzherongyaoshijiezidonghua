# -*- coding: utf-8 -*-
"""图像匹配"""
import os
import cv2
import numpy as np
import pyautogui
from utils.helpers import get_path, move_mouse_human, random_sleep
import config


class ImageMatcher:
    def __init__(self, threshold=config.MATCH_THRESHOLD, scale=config.SCALE_FACTOR):
        self.threshold = threshold
        self.scale = scale
        self.templates = {}
        self.load_templates()

    def load_templates(self):
        all_images = [config.SPECIAL_IMAGE, config.Q_IMAGE, config.ESC_IMAGE,
                      config.RENWUONE_IMAGE, config.XIA_IMAGE, config.HAOPENGYOU_IMAGE,
                      config.WORLD_TAB_IMAGE, config.WORLD_DIANJI_IMAGE, config.WORLD_SEND_IMAGE] + config.IMAGE_NAMES
        for name in all_images:
            path = get_path(os.path.join(config.IMAGES_DIR, name))
            try:
                template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if template is None:
                    print(f"警告：无法加载 {path}")
                    continue
                if name not in config.NO_SCALE_IMAGES and self.scale != 1.0:
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
        use_scale = 1.0 if template_name in config.NO_SCALE_IMAGES else self.scale

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
        use_scale = 1.0 if template_name in config.NO_SCALE_IMAGES else self.scale

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

    def click_at(self, win_mgr, rel_x, rel_y, log_callback=None):
        if not win_mgr.rect:
            return False
        abs_x = win_mgr.rect["left"] + rel_x
        abs_y = win_mgr.rect["top"] + rel_y
        current_x, current_y = pyautogui.position()
        dist = ((current_x - abs_x) ** 2 + (current_y - abs_y) ** 2) ** 0.5
        if dist > 50:
            move_mouse_human(current_x, current_y, abs_x, abs_y, duration=0.2, steps=15)
        else:
            pyautogui.moveTo(abs_x, abs_y, duration=random_sleep(0.05, 0.15, return_sec=True))
        random_sleep(0.02, 0.08)
        pyautogui.click()
        if log_callback:
            log_callback(f"点击坐标 ({abs_x}, {abs_y})")
        return True