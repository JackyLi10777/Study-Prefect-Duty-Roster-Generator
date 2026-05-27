# data.py
import pandas as pd
import io

from config import ROWS_ROSTER, DAYS

# ==========================================
# 示範資料生成器（完整舊版 demo data + 最新版修復）
# ==========================================
def get_demo_dataframe():
    """
    提供一組完整的示範領袖生資料，用於系統首次啟動或測試。
    補回舊版所有欄位與真實姓名範例，確保功能零流失。
    與 config.py 中的 ROWS_ROSTER、DAYS 完全相容。
    """
    demo_data = [
        {"name": "李創杰", "form": "F.5", "class": "5D", "role": "Assistant Head Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 12, "history_weight": 18.5, "remarks": "Head Prefect 候選人"},
        {"name": "劉子浩", "form": "F.5", "class": "5B", "role": "Assistant Head Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 11, "history_weight": 22.0, "remarks": ""},
        {"name": "歐陽浚鋒", "form": "F.4", "class": "4C", "role": "Assistant Head Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 8, "history_weight": 12.0, "remarks": ""},
        {"name": "何梓皓", "form": "F.3", "class": "3B", "role": "Assistant Head Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 7, "history_weight": 6.0, "remarks": ""},
        {"name": "許舜喬", "form": "F.3", "class": "3C", "role": "Assistant Head Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 6, "history_weight": 7.5, "remarks": ""},
        {"name": "陳子軒", "form": "F.5", "class": "5A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 9, "history_weight": 13.5, "remarks": ""},
        {"name": "張凱傑", "form": "F.4", "class": "4A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 8, "history_weight": 13.5, "remarks": ""},
        {"name": "吳柏樂", "form": "F.3", "class": "3A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 5, "history_weight": 4.0, "remarks": ""},
        {"name": "何俊霆", "form": "F.3", "class": "3B", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 6, "history_weight": 4.5, "remarks": ""},
        {"name": "林俊賢", "form": "F.3", "class": "3C", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 7, "history_weight": 5.5, "remarks": ""},
        {"name": "黃家樂", "form": "F.4", "class": "4B", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 5, "history_weight": 10.0, "remarks": ""},
    ]
    df = pd.DataFrame(demo_data)
    # 確保所有欄位存在且型別正確（補回舊版型別安全處理）
    df["history_duties"] = pd.to_numeric(df["history_duties"], errors="coerce").fillna(0).astype(int)
    df["history_weight"] = pd.to_numeric(df["history_weight"], errors="coerce").fillna(0.0)
    return df

# ==========================================
# 名冊格式範例（供使用者下載 - 完整舊版功能）
# ==========================================
def get_sample_format_dataframe():
    """
    提供一個乾淨的空白範例表格，讓使用者知道正確的欄位名稱與格式。
    這是舊版本中「下載名冊格式範例」功能的完整還原。
    """
    sample_data = [
        {"姓名": "李創杰", "年級": "F.5", "班別": "5D", "職級": "Assistant Head Study Prefect", "學年固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "歷史累計(次)": 12, "歷史動態(點)": 18.5, "備註": "Head Prefect 候選人"},
        {"姓名": "劉子浩", "年級": "F.5", "班別": "5B", "職級": "Assistant Head Study Prefect", "學年固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "歷史累計(次)": 11, "歷史動態(點)": 22.0, "備註": ""},
        {"姓名": "", "年級": "", "班別": "", "職級": "", "學年固定總值班": "", "可用日子": "", "歷史累計(次)": "", "歷史動態(點)": "", "備註": "← 從第二行開始填寫"},
    ]
    df = pd.DataFrame(sample_data)
    return df

# ==========================================
# 公開的資料輔助函數（供其他模組呼叫 - 補回舊版下載功能）
# ==========================================
def get_sample_excel_bytes():
    """
    直接回傳可下載的 Excel 範例檔 bytes。
    這是舊版本中「點此下載範例檔」功能的完整還原。
    """
    df = get_sample_format_dataframe()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Prefect_名冊格式範例", index=False)
    output.seek(0)
    return output.getvalue()

# ==========================================
# 額外輔助函數（補回舊版常用資料驗證與轉換功能）
# ==========================================
def validate_demo_data(df):
    """
    補回舊版資料驗證函數，確保示範資料與實際排班系統相容。
    """
    required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
    for col in required_cols:
        if col not in df.columns:
            if col == "fixed_general_duty":
                df[col] = "NONE"
            elif col == "available":
                df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
            elif col == "history_duties":
                df[col] = 0
            elif col == "history_weight":
                df[col] = 0.0
            else:
                df[col] = ""
    return df