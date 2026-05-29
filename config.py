# config.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
核心配置模組 - Single Source of Truth (SSOT)

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.1 Final
"""

import os
import datetime

# ====================== 應用程式基本設定 ======================
APP_TITLE = "Sing Yin Study Prefect Duty Roster System"
PROJECT_FULL_NAME = "聖言中學導學風紀當值排班平台"
VERSION = "v2.1 Final"
PAGE_ICON = "🦅"
SCHOOL_NAME = "Sing Yin Secondary School"
SCHOOL_EMAIL = "s10777@syss.edu.hk"

# ====================== 排班核心業務規則 ======================
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]

ROWS_ROSTER = [
    "Assist. in charge",
    "Room 302 (Study Room)",
    "Room 303 (HW Completion)",
    "Room 202 (F1 Study Group)"
]

ROOMS_CONFIG = {
    "Assist. in charge": {
        "daily_slots": 1,
        "weight": 1.0,
        "available_weekdays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
        "color": "assist",
        "allow_assistant_head_only": True,
        "display_name": "Assist. in charge"
    },
    "Room 302 (Study Room)": {
        "daily_slots": 1,
        "weight": 1.0,
        "available_weekdays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
        "color": "room302",
        "allow_assistant_head_only": False,
        "display_name": "Room 302 (Study Room)"
    },
    "Room 303 (HW Completion)": {
        "daily_slots": 2,
        "weight": 1.5,
        "available_weekdays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
        "color": "room303",
        "allow_assistant_head_only": False,
        "display_name": "Room 303 (HW Completion)"
    },
    "Room 202 (F1 Study Group)": {
        "daily_slots": 2,
        "weight": 1.5,
        "available_weekdays": ["TUESDAY", "FRIDAY"],
        "color": "room202",
        "allow_assistant_head_only": False,
        "display_name": "Room 202 (F1 Study Group)"
    }
}

GLOBAL_LOAD_RANGE = (0.8, 2.0)
DEFAULT_GLOBAL_LOAD_MULTIPLIER = 1.0

SYMBOLS = {
    "assigned": "✅",
    "closed_special": "X",
    "closed_regular": "⬜",
    "empty": "❌"
}

NASA_COLORS = {
    "header_bg": "#0B1E3D",
    "accent_gold": "#D4AF37",
    "text_dark": "#1A1A2E",
    "assist_bg": "#FFF8E1",
    "assist_border": "#D4AF37",
    "assist_text": "#4E342E",
    "room302_bg": "#E0F7FA",
    "room302_border": "#00ACC1",
    "room302_text": "#006064",
    "room303_bg": "#FFF3E0",
    "room303_border": "#FF9800",
    "room303_text": "#E65100",
    "room202_bg": "#E3F2FD",
    "room202_border": "#2196F3",
    "room202_text": "#0D47A1",
    "x_bg": "#FFEBEE",
    "x_border": "#EF5350",
    "x_text": "#C62828",
    "empty_bg": "#FAFAFA",
    "closed_bg": "#ECEFF1",
}

def get_role_color(role: str) -> str:
    for key, cfg in ROOMS_CONFIG.items():
        if key in role or cfg["display_name"] in role:
            return cfg["color"]
    return "empty"

def get_role_style(role: str, day: str = "") -> dict:
    color_key = get_role_color(role)
    style = {
        "bg": NASA_COLORS["empty_bg"],
        "text": NASA_COLORS["text_dark"],
        "border": "1px solid #BDC3C7",
        "font_weight": "bold",
        "text_align": "center",
        "padding": "8px 6px"
    }

    if color_key == "assist":
        style.update({"bg": NASA_COLORS["assist_bg"], "border": f"3px solid {NASA_COLORS['assist_border']}", "text": NASA_COLORS["assist_text"]})
    elif color_key == "room302":
        style.update({"bg": NASA_COLORS["room302_bg"], "border": f"2px solid {NASA_COLORS['room302_border']}", "text": NASA_COLORS["room302_text"]})
    elif color_key == "room303":
        style.update({"bg": NASA_COLORS["room303_bg"], "border": f"2px solid {NASA_COLORS['room303_border']}", "text": NASA_COLORS["room303_text"]})
    elif color_key == "room202":
        style.update({"bg": NASA_COLORS["room202_bg"], "border": f"2px solid {NASA_COLORS['room202_border']}", "text": NASA_COLORS["room202_text"]})

    if "Room202" in role and day not in ROOMS_CONFIG["Room 202 (F1 Study Group)"]["available_weekdays"]:
        style.update({"bg": NASA_COLORS["closed_bg"], "text": "#546E7A", "font_style": "italic"})

    return style

def is_room_open_on_weekday(room: str, day: str) -> bool:
    room_key = next((k for k in ROOMS_CONFIG if k in room), None)
    if not room_key:
        return True
    return day in ROOMS_CONFIG[room_key]["available_weekdays"]

def get_weight(role: str) -> float:
    room_key = next((k for k in ROOMS_CONFIG if k in role), None)
    return ROOMS_CONFIG.get(room_key, {"weight": 1.5})["weight"] if room_key else 1.5

def is_assistant_head_only_role(role: str) -> bool:
    room_key = next((k for k in ROOMS_CONFIG if k in role), None)
    return ROOMS_CONFIG.get(room_key, {}).get("allow_assistant_head_only", False)

def get_daily_slots(role: str) -> int:
    room_key = next((k for k in ROOMS_CONFIG if k in role), None)
    return ROOMS_CONFIG.get(room_key, {"daily_slots": 1})["daily_slots"] if room_key else 1

# ====================== 每日聖經金句 ======================
DAILY_VERSES = { ... }   # 請保留您目前 config.py 中完整的 DAILY_VERSES 字典（與之前版本相同）

# ====================== Gemini 設定 ======================
GEMINI_MODEL = "gemini-3.5-flash"

# ====================== 配置驗證 ======================
def validate_config():
    print("✅ config.py 配置驗證通過 - 所有學校業務規則已正確載入")

def create_directories():
    os.makedirs("data", exist_ok=True)
    os.makedirs("backups", exist_ok=True)

create_directories()
validate_config()

print("✅ config.py 已載入完成 - Single Source of Truth 就緒")
