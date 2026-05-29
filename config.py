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
    "Assist. in charge": {"daily_slots": 1, "weight": 1.0, "available_weekdays": DAYS, "color": "assist", "allow_assistant_head_only": True, "display_name": "Assist. in charge"},
    "Room 302 (Study Room)": {"daily_slots": 1, "weight": 1.0, "available_weekdays": DAYS, "color": "room302", "allow_assistant_head_only": False, "display_name": "Room 302 (Study Room)"},
    "Room 303 (HW Completion)": {"daily_slots": 2, "weight": 1.5, "available_weekdays": DAYS, "color": "room303", "allow_assistant_head_only": False, "display_name": "Room 303 (HW Completion)"},
    "Room 202 (F1 Study Group)": {"daily_slots": 2, "weight": 1.5, "available_weekdays": ["TUESDAY", "FRIDAY"], "color": "room202", "allow_assistant_head_only": False, "display_name": "Room 202 (F1 Study Group)"}
}

GLOBAL_LOAD_RANGE = (0.8, 2.0)
DEFAULT_GLOBAL_LOAD_MULTIPLIER = 1.0

NASA_COLORS = {
    "header_bg": "#0B1E3D", "accent_gold": "#D4AF37", "text_dark": "#1A1A2E",
    "assist_bg": "#FFF8E1", "assist_border": "#D4AF37", "assist_text": "#4E342E",
    "room302_bg": "#E0F7FA", "room302_border": "#00ACC1", "room302_text": "#006064",
    "room303_bg": "#FFF3E0", "room303_border": "#FF9800", "room303_text": "#E65100",
    "room202_bg": "#E3F2FD", "room202_border": "#2196F3", "room202_text": "#0D47A1",
    "x_bg": "#FFEBEE", "x_border": "#EF5350", "x_text": "#C62828",
    "empty_bg": "#FAFAFA", "closed_bg": "#ECEFF1",
}

# ====================== 核心輔助函數 ======================
def get_role_style(role: str, day: str = "") -> dict:
    for key, cfg in ROOMS_CONFIG.items():
        if key in role or cfg["display_name"] in role
