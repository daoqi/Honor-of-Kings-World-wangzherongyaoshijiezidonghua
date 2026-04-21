# -*- coding: utf-8 -*-
"""全局配置"""

# ======================== 任务相关配置 ========================
IMAGES_DIR = "images"
CLICK_DELAY = 0.1
LOOP_DELAY = 0.01
MATCH_THRESHOLD = 0.7
SCALE_FACTOR = 0.7

# 不缩放的图片列表
NO_SCALE_IMAGES = ["q.png", "f_renwu.png", "f_renwu1.png", "renwuone.png", "xia.png", "renwu.png", "haopengyou.png", "f.png",
                   "World_tab.png", "World_dianji.png", "worl_zidongfasongxiaoxi.png"]

# 特殊图片名称
SPECIAL_IMAGE = "renwu.png"
Q_IMAGE = "q.png"
ESC_IMAGE = "esc.png"
RENWUONE_IMAGE = "renwuone.png"
XIA_IMAGE = "xia.png"
HAOPENGYOU_IMAGE = "haopengyou.png"
WORLD_TAB_IMAGE = "World_tab.png"
WORLD_DIANJI_IMAGE = "World_dianji.png"
WORLD_SEND_IMAGE = "worl_zidongfasongxiaoxi.png"

# 普通按钮图片列表
IMAGE_NAMES = [
    "dianji.png", "pass.png", "x.png", "xia.png", "lingqu.png", "renwu.png", "kuaisulingqu.png",
    "zhunbei.png", "quiduijue.png", "dianjikongbaiexit.png", "renwuone.png", "goodbye.png",
    "gogametwo.png", "jiujinfuhuo.png", "fishing_lvup.png", "Click_1.png",
    "Click_on_the_blank_area_to_exit.png", "Click_on_the_blank_area_to_claim_the_reward.png",
]

# ======================== 钓鱼相关配置 ========================
MODEL_PATH = "mode/best.pt"
CAST_ROD_CONF = 0.35
REFRESH_MS = 150
KEY_PRESS_DURATION = 0.01
CLICK_DURATION = 0.02

COOLDOWN = {
    "cast": 0.5,
    "pull": 0.8,
    "fish_bite": 0.5,
    "press_f": 0.5,
    "rapid_action": 0.8,
}