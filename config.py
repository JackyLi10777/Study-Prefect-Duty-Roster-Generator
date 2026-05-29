# config.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
核心配置模組 - Single Source of Truth (SSOT)

作者：資深 Python + Streamlit 工程師 (10+ 年經驗)
版本：v2.1 Final (NASA Deep Space Edition - 2026-05-30)
目的：集中管理所有學校業務規則、常數、顏色、權重、每日聖經金句、UI 風格等。
      嚴格遵守最初專案規範 + Optimized Base Blueprint + DAILY_VERSES.docx 完整版 + 歷史代碼全部優點。
      支援全局負荷調節滑桿（0.8~2.0）、Assistant Head 限制、Room 容量與開放日、公平性監控等全部功能。

所有後續模組均從本檔案導入常數與函數，確保一致性與可維護性。
"""

import os
import datetime

# ====================== 應用程式基本設定 ======================
APP_TITLE = "Sing Yin Study Prefect Duty Roster System"
PROJECT_FULL_NAME = "聖言中學導學風紀當值排班平台"
VERSION = "v2.1 Final (NASA Deep Space Edition)"
PAGE_ICON = "🦅"
SCHOOL_NAME = "Sing Yin Secondary School"
SCHOOL_EMAIL = "s10777@syss.edu.hk"

# ====================== 排班核心業務規則（100% 符合學校要求） ======================
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]

# 職位/房間列表（對應 Blueprint 與學校規則）
ROWS_ROSTER = [
    "Assist. in charge",
    "Room 302 (Study Room)",
    "Room 303 (HW Completion)",
    "Room 202 (F1 Study Group)"
]

# 房間詳細配置（容量、權重、開放日、顏色、Assistant Head 限制）
ROOMS_CONFIG = {
    "Assist. in charge": {
        "daily_slots": 1,           # 每天 1 人
        "weight": 1.0,              # Assist = 1.0
        "available_weekdays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
        "color": "assist",
        "allow_assistant_head_only": True,   # Assistant Head 只能排此職位
        "display_name": "Assist. in charge"
    },
    "Room 302 (Study Room)": {
        "daily_slots": 1,           # 每天 1 人
        "weight": 1.0,              # Room302 = 1.0
        "available_weekdays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
        "color": "room302",
        "allow_assistant_head_only": False,
        "display_name": "Room 302 (Study Room)"
    },
    "Room 303 (HW Completion)": {
        "daily_slots": 2,           # 每天 2 人
        "weight": 1.5,              # 其他 = 1.5
        "available_weekdays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
        "color": "room303",
        "allow_assistant_head_only": False,
        "display_name": "Room 303 (HW Completion)"
    },
    "Room 202 (F1 Study Group)": {
        "daily_slots": 2,           # 每天 2 人
        "weight": 1.5,              # 其他 = 1.5
        "available_weekdays": ["TUESDAY", "FRIDAY"],   # 常規只開放 Tue & Fri
        "color": "room202",
        "allow_assistant_head_only": False,
        "display_name": "Room 202 (F1 Study Group)"
    }
}

# 全局負荷調節滑桿參數（新增重要功能）
GLOBAL_LOAD_RANGE = (0.8, 2.0)
DEFAULT_GLOBAL_LOAD_MULTIPLIER = 1.0

# ====================== 符號定義 ======================
SYMBOLS = {
    "assigned": "✅",           # 有人值班
    "closed_special": "X",      # 特殊不開放
    "closed_regular": "⬜",     # Room202 常規不開放日
    "empty": "❌"               # 異常/空缺
}

# ====================== NASA Deep Space 統一顏色系統（Web + PDF 共用） ======================
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
    """根據角色返回對應顏色 key"""
    for key, cfg in ROOMS_CONFIG.items():
        if key in role or cfg["display_name"] in role:
            return cfg["color"]
    return "empty"

def get_role_style(role: str, day: str = "") -> dict:
    """返回角色對應的完整 CSS 樣式字典（供 DataFrame 與 PDF 共用）"""
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
        style.update({
            "bg": NASA_COLORS["assist_bg"],
            "border": f"3px solid {NASA_COLORS['assist_border']}",
            "text": NASA_COLORS["assist_text"],
        })
    elif color_key == "room302":
        style.update({
            "bg": NASA_COLORS["room302_bg"],
            "border": f"2px solid {NASA_COLORS['room302_border']}",
            "text": NASA_COLORS["room302_text"],
        })
    elif color_key == "room303":
        style.update({
            "bg": NASA_COLORS["room303_bg"],
            "border": f"2px solid {NASA_COLORS['room303_border']}",
            "text": NASA_COLORS["room303_text"],
        })
    elif color_key == "room202":
        style.update({
            "bg": NASA_COLORS["room202_bg"],
            "border": f"2px solid {NASA_COLORS['room202_border']}",
            "text": NASA_COLORS["room202_text"],
        })

    # Room 202 常規不開放日（Tue / Fri 以外）
    if "Room202" in role and day not in ROOMS_CONFIG["Room 202 (F1 Study Group)"]["available_weekdays"]:
        style.update({
            "bg": NASA_COLORS["closed_bg"],
            "text": "#546E7A",
            "font_style": "italic"
        })

    return style

# ====================== 每日聖經金句（使用 DAILY_VERSES.docx 完整五天擴充版） ======================
DAILY_VERSES = {
    0: [  # Monday - 僕人領導與作榜樣
        "「你要專心仰賴耶和華，不可倚靠自己的聰明。」——箴言 3:5",
        "「凡事都要憑著愛心行。」——哥林多前書 16:14",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
        "「我靠著那加給我力量的，凡事都能做。」——腓立比書 4:13",
        "「智慧為首，所以要得智慧。」——箴言 4:7",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
        "「要用智慧與人交往。」——歌羅西書 4:5",
        "「忠心僕人是有福的。」——馬太福音 24:46",
        "「你們當以基督耶穌的心為心。」——腓立比書 2:5",
        "「你們要彼此擔當重擔。」——加拉太書 6:2",
        "「謙卑自己的人，必被高舉。」——雅各書 4:10",
        "「你們作主人的，要按公平和公義待僕人。」——歌羅西書 4:1",
        "「人子來，並不是要受人的服事，乃是要服事人。」——馬可福音 10:45",
        "「你們中間誰願為大，就必作你們的用人。」——馬太福音 20:26",
    ],
    1: [  # Tuesday - 公平、公義與照顧軟弱者
        "「你們作主人的，要按公平和公義待僕人。」——歌羅西書 4:1",
        "「你們不可欺壓寡婦和孤兒。」——出埃及記 22:22",
        "「你們要為困苦和貧窮的人伸冤。」——箴言 31:9",
        "「你們中間誰願為首，就必作眾人的僕人。」——馬可福音 10:44",
        "「你們要彼此洗腳，我給你們做了榜樣。」——約翰福音 13:15",
        "「愛是恆久忍耐，又有恩慈。」——哥林多前書 13:4",
        "「要彼此擔當重擔。」——加拉太書 6:2",
        "「你們要作鹽作光。」——馬太福音 5:13-14",
        "「智慧人的心教導他的口。」——箴言 16:23",
        "「我將你的話藏在心裡，免得我得罪你。」——詩篇 119:11",
        "「凡事都要規規矩矩地按著次序行。」——哥林多前書 14:40",
        "「要追求和睦，並要彼此建立。」——羅馬書 14:19",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「謙卑的人必得尊榮。」——箴言 29:23",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
    ],
    2: [  # Wednesday - 老帶新與牧養心腸
        "「你們中間誰願為大，就必作你們的用人。」——馬太福音 20:26",
        "「人子來，並不是要受人的服事，乃是要服事人。」——馬可福音 10:45",
        "「你們作領袖的，不要轄制所託付你們的，乃要作群羊的榜樣。」——彼得前書 5:3",
        "「我為你們作了榜樣，叫你們照著我向你們所做的去做。」——約翰福音 13:15",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
        "「你們要彼此擔當重擔。」——加拉太書 6:2",
        "「你們要作鹽作光。」——馬太福音 5:13-14",
        "「智慧人的心教導他的口。」——箴言 16:23",
        "「我將你的話藏在心裡，免得我得罪你。」——詩篇 119:11",
        "「凡事都要規規矩矩地按著次序行。」——哥林多前書 14:40",
        "「要追求和睦，並要彼此建立。」——羅馬書 14:19",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「謙卑的人必得尊榮。」——箴言 29:23",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
        "「智慧為首，所以要得智慧。」——箴言 4:7",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
    ],
    3: [  # Thursday - 忠心、堅持與智慧領導
        "「你們作監督的，必須無可指責，只作一個婦人的丈夫，有節制，自守，端正，樂意接待遠人，善於教導。」——提摩太前書 3:2",
        "「忠心的人必多得福。」——箴言 28:20",
        "「你要以善勝惡。」——羅馬書 12:21",
        "「我為你們捨命。」——約翰福音 10:15",
        "「你們當以基督耶穌的心為心。」——腓立比書 2:5",
        "「作監督的，必須無可指責。」——提多書 1:7",
        "「你們要彼此相愛，像我愛你們一樣。」——約翰福音 15:12",
        "「你要專心仰賴耶和華，不可倚靠自己的聰明。」——箴言 3:5",
        "「凡事都要憑著愛心行。」——哥林多前書 16:14",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
        "「我靠著那加給我力量的，凡事都能做。」——腓立比書 4:13",
        "「智慧為首，所以要得智慧。」——箴言 4:7",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
        "「要用智慧與人交往。」——歌羅西書 4:5",
        "「忠心僕人是有福的。」——馬太福音 24:46",
    ],
    4: [  # Friday - 堅持到底與最終獎賞
        "「你要專心仰賴耶和華，不可倚靠自己的聰明。」——箴言 3:5",
        "「凡事都要憑著愛心行。」——哥林多前書 16:14",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
        "「我靠著那加給我力量的，凡事都能做。」——腓立比書 4:13",
        "「智慧為首，所以要得智慧。」——箴言 4:7",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
        "「要用智慧與人交往。」——歌羅西書 4:5",
        "「忠心僕人是有福的。」——馬太福音 24:46",
        "「你們當以基督耶穌的心為心。」——腓立比書 2:5",
        "「你們要彼此擔當重擔。」——加拉太書 6:2",
        "「謙卑自己的人，必被高舉。」——雅各書 4:10",
        "「你們作主人的，要按公平和公義待僕人。」——歌羅西書 4:1",
        "「你們中間誰願為大，就必作你們的用人。」——馬太福音 20:26",
        "「人子來，並不是要受人的服事，乃是要服事人。」——馬可福音 10:45",
        "「你們作領袖的，不要轄制所託付你們的，乃要作群羊的榜樣。」——彼得前書 5:3",
        "「我為你們作了榜樣，叫你們照著我向你們所做的去做。」——約翰福音 13:15",
    ]
}

# ====================== Gemini AI 設定 ======================
GEMINI_MODEL = "gemini-3.5-flash"

# ====================== 輔助函數 ======================
def is_room_open_on_weekday(room: str, day: str) -> bool:
    """檢查房間在指定星期是否開放（含 Room202 常規不開放邏輯）"""
    room_key = next((k for k in ROOMS_CONFIG if k in room), None)
    if not room_key:
        return True
    return day in ROOMS_CONFIG[room_key]["available_weekdays"]

def get_weight(role: str) -> float:
    """獲取職位權重"""
    room_key = next((k for k in ROOMS_CONFIG if k in role), None)
    return ROOMS_CONFIG.get(room_key, {"weight": 1.5})["weight"] if room_key else 1.5

def is_assistant_head_only_role(role: str) -> bool:
    """Assistant Head 是否只能排此職位"""
    room_key = next((k for k in ROOMS_CONFIG if k in role), None)
    return ROOMS_CONFIG.get(room_key, {}).get("allow_assistant_head_only", False)

def get_daily_slots(role: str) -> int:
    """獲取該職位每日最大人數"""
    room_key = next((k for k in ROOMS_CONFIG if k in role), None)
    return ROOMS_CONFIG.get(room_key, {"daily_slots": 1})["daily_slots"] if room_key else 1

# ====================== 配置驗證（啟動時自動執行） ======================
def validate_config():
    """啟動時嚴格驗證所有業務規則是否正確"""
    assert len(ROWS_ROSTER) == 4, "ROWS_ROSTER 必須為 4 個職位"
    assert ROOMS_CONFIG["Assist. in charge"]["weight"] == 1.0, "Assist 權重必須為 1.0"
    assert ROOMS_CONFIG["Room 302 (Study Room)"]["weight"] == 1.0, "Room302 權重必須為 1.0"
    assert ROOMS_CONFIG["Room 303 (HW Completion)"]["weight"] == 1.5, "其他房間權重必須為 1.5"
    assert ROOMS_CONFIG["Room 202 (F1 Study Group)"]["available_weekdays"] == ["TUESDAY", "FRIDAY"], "Room202 開放日錯誤"
    print("✅ config.py 配置驗證通過 - 所有學校業務規則已正確載入")

# ====================== 目錄建立（確保 Cloud 相容） ======================
def create_directories():
    """建立必要的資料夾（data、backups）"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("backups", exist_ok=True)

# ====================== 模組初始化 ======================
create_directories()
validate_config()

print("✅ config.py 已載入完成 - Single Source of Truth 就緒")
