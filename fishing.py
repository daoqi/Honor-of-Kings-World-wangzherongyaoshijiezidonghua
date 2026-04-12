import cv2
import numpy as np
from PIL import ImageGrab
import os
import time
import win32gui
import win32api
import win32con
import ctypes

# ==================== 底层鼠标点击 ====================
mouse_event = ctypes.windll.user32.mouse_event
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SetCursorPos = ctypes.windll.user32.SetCursorPos

def click_at(x, y):
    SetCursorPos(x, y)
    time.sleep(0.1)
    mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    print(f"🖱️ 点击 ({x}, {y})")

def double_click_at(x, y):
    click_at(x, y)
    time.sleep(0.05)
    click_at(x, y)

# ==================== 配置 ====================
IMAGE_DIR = "images_fishing"
CONFIDENCE = 0.65

rod_path = os.path.join(IMAGE_DIR, "chuidiaojia.png")
circle_paths = [
    os.path.join(IMAGE_DIR, "diao_quan.png"),
    os.path.join(IMAGE_DIR, "diao_quan1.png"),
    os.path.join(IMAGE_DIR, "diao_quan2.png"),
    os.path.join(IMAGE_DIR, "diao_quan3.png")
]
bite_paths = [os.path.join(IMAGE_DIR, f"fish_bite{i}.png") for i in range(6)]
reward_paths = [
    os.path.join(IMAGE_DIR, "fish_exp.png"),
    os.path.join(IMAGE_DIR, "fishing_lvup.png"),
    os.path.join(IMAGE_DIR, "fishtext.png"),
    os.path.join(IMAGE_DIR, "Click_1.png"),
    os.path.join(IMAGE_DIR, "Click_on_the_blank_area_to_claim_the_reward.png"),
    os.path.join(IMAGE_DIR, "Click_on_the_blank_area_to_exit.png"),
    os.path.join(IMAGE_DIR, "fangrubeibao.png")
]

def load_image(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        return img
    except:
        return None

rod = load_image(rod_path)
circles = [load_image(p) for p in circle_paths if os.path.exists(p)]
bites = [load_image(p) for p in bite_paths if os.path.exists(p)]
rewards = [load_image(p) for p in reward_paths if os.path.exists(p)]

if rod is None:
    print("❌ 钓鱼架图片加载失败")
    exit()

def match(gray, template, threshold=CONFIDENCE):
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

def get_any_circle_center(gray):
    for tpl in circles:
        if tpl is None:
            continue
        found, center, score = match(gray, tpl, 0.75)
        if found:
            return center, score
    return None, 0

def get_any_bite(gray):
    for i, tpl in enumerate(bites):
        if tpl is None:
            continue
        found, center, score = match(gray, tpl, 0.75)
        if found:
            return i, center, score
    return -1, None, 0

def get_any_reward(gray):
    for i, tpl in enumerate(rewards):
        if tpl is None:
            continue
        found, center, score = match(gray, tpl, 0.75)
        if found:
            return i, center, score
    return -1, None, 0

def get_rod_status(gray):
    found, _, score = match(gray, rod, 0.7)
    return found, score

def get_fangrubeibao_center(gray):
    """专门检测 fangrubeibao.png"""
    for i, tpl in enumerate(rewards):
        if tpl is None:
            continue
        if "fangrubeibao" in reward_paths[i]:
            found, center, score = match(gray, tpl, 0.7)
            if found:
                return center, score
    return None, 0

print("🎣 自动钓鱼脚本启动")
fish_count = 0

try:
    while True:
        screen = ImageGrab.grab()
        gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)

        # 1. 钓鱼架 + 钓鱼圈
        rod_ok, _ = get_rod_status(gray)
        if rod_ok:
            circle_center, circle_score = get_any_circle_center(gray)
            if circle_center:
                print(f"🎯 检测到钓鱼架和钓鱼圈 (匹配度 {circle_score:.2f})，点击抛竿")
                click_at(circle_center[0], circle_center[1])
                time.sleep(2)

                # ========== 咬钩检测循环（最多100次） ==========
                bite_detected = False
                for _ in range(100):
                    screen = ImageGrab.grab()
                    gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
                    bite_idx, bite_center, bite_score = get_any_bite(gray)
                    if bite_idx != -1:
                        print(f"🐟 检测到咬钩图片{bite_idx} (匹配度 {bite_score:.2f})，双击")
                        double_click_at(bite_center[0], bite_center[1])
                        bite_detected = True
                        break
                    time.sleep(0.3)
                if not bite_detected:
                    print("100次内未检测到咬钩，继续主循环")
                    continue

                # ========== 奖励检测循环（最多100次） ==========
                reward_detected = False
                for _ in range(100):
                    screen = ImageGrab.grab()
                    gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
                    reward_idx, reward_center, reward_score = get_any_reward(gray)
                    if reward_idx != -1:
                        reward_name = os.path.basename(reward_paths[reward_idx])
                        fish_count += 1
                        print(f"🎁 识别到奖励图片: {reward_name} (匹配度 {reward_score:.2f})，钓鱼数量+1，总计 {fish_count}")
                        click_at(reward_center[0], reward_center[1])
                        reward_detected = True
                        break
                    time.sleep(0.3)
                if not reward_detected:
                    print("100次内未检测到奖励图片，继续主循环")

                # ========== 新增：等待循环，检测 chuidiaojia.png 和 fangrubeibao.png ==========
                print("等待钓鱼架或同时出现钓鱼架+大鱼入包...")
                while True:
                    screen = ImageGrab.grab()
                    gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
                    rod_ok_now, _ = get_rod_status(gray)
                    fang_center, fang_score = get_fangrubeibao_center(gray)
                    if rod_ok_now and fang_center is not None:
                        print(f"🎯 同时检测到钓鱼架和大鱼入包 (匹配度 {fang_score:.2f}22)，点击大鱼入包")
                        click_at(fang_center[0], fang_center[1])
                        time.sleep(1)
                        break
                    elif rod_ok_now:
                        print("仅检测到钓鱼架，退出等待循环")
                        break
                    time.sleep(0.3)
                continue

        # 如果没有检测到钓鱼架，短暂等待
        time.sleep(0.3)

except KeyboardInterrupt:
    print(f"\n自动钓鱼被终止，共钓鱼🎣 {fish_count} 次")