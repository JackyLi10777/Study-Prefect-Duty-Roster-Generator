# data.py
import streamlit as st
import pandas as pd
import io
import random
from config import ROWS_ROSTER

# ==========================================
# 示範名冊（真實男校 F.3-F.5 學生資料）
# ==========================================
def get_demo_dataframe() -> pd.DataFrame:
    """返回完整的示範名冊（已包含 Assistant Head 與普通 Prefect）"""
    data = [
        {"姓名": "陳卓軒", "年級": "F.5", "班別": "5A", "職級": "Assistant Head Study Prefect", "固定總值班": "MONDAY", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "歷史累計(次)": 18, "歷史動態(點)": 27.5, "備註": ""},
        {"姓名": "李浩然", "年級": "F.5", "班別": "5B", "職級": "Assistant Head Study Prefect", "固定總值班": "WEDNESDAY", "可用日子": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "歷史累計(次)": 15, "歷史動態(點)": 22.0, "備註": ""},
        {"姓名": "張凱傑", "年級": "F.4", "班別": "4A", "職級": "Study Prefect", "固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "歷史累計(次)": 12, "歷史動態(點)": 18.0, "備註": ""},
        {"姓名": "黃俊霆", "年級": "F.4", "班別": "4B", "職級": "Study Prefect", "固定總值班": "NONE", "可用日子": "MONDAY,WEDNESDAY,THURSDAY", "歷史累計(次)": 9, "歷史動態(點)": 13.5, "備註": "老帶新優先"},
        {"姓名": "許舜喬", "年級": "F.3", "班別": "3A", "職級": "Study Prefect", "固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "歷史累計(次)": 6, "歷史動態(點)": 9.0, "備註": ""},
        {"姓名": "何梓皓", "年級": "F.3", "班別": "3B", "職級": "Study Prefect", "固定總值班": "NONE", "可用日子": "TUESDAY,THURSDAY,FRIDAY", "歷史累計(次)": 5, "歷史動態(點)": 7.5, "備註": ""},
        {"姓名": "歐陽浚鋒", "年級": "F.5", "班別": "5C", "職級": "Assistant Head Study Prefect", "固定總值班": "FRIDAY", "可用日子": "MONDAY,WEDNESDAY,FRIDAY", "歷史累計(次)": 14, "歷史動態(點)": 21.0, "備註": ""},
        {"姓名": "古本正", "年級": "F.4", "班別": "4C", "職級": "Study Prefect", "固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,THURSDAY", "歷史累計(次)": 8, "歷史動態(點)": 12.0, "備註": ""},
    ]
    df = pd.DataFrame(data)
    # 確保所有必要欄位存在
    for col in ["姓名", "年級", "班別", "職級", "固定總值班", "可用日子", "歷史累計(次)", "歷史動態(點)", "備註"]:
        if col not in df.columns:
            df[col] = ""
    return df

# ==========================================
# 示範名冊格式（下載用）
# ==========================================
def get_sample_format_dataframe() -> pd.DataFrame:
    """下載用的空白格式範例"""
    data = [
        {"姓名": "陳卓軒", "年級": "F.5", "班別": "5A", "職級": "Assistant Head Study Prefect", "固定總值班": "MONDAY", "可用日子": "MONDAY,WEDNESDAY,FRIDAY", "歷史累計(次)": 18, "歷史動態(點)": 27.5, "備註": "請假範例"},
        {"姓名": "李浩然", "年級": "F.4", "班別": "4B", "職級": "Study Prefect", "固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,THURSDAY", "歷史累計(次)": 9, "歷史動態(點)": 13.5, "備註": ""},
    ]
    return pd.DataFrame(data)

def get_sample_excel_bytes() -> bytes:
    """產生範例 Excel 檔案"""
    df = get_sample_format_dataframe()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Prefect_名冊格式範例", index=False)
    output.seek(0)
    return output.getvalue()

# ==========================================
# 預設校徽（可選）
# ==========================================
def get_default_logo_bytes() -> bytes:
    """如果使用者沒有上傳校徽，可使用此預設校徽（請自行替換 base64）"""
    # 這裡留空或放您學校校徽的 base64（可後續補）
    return b""   # 若需要預設校徽，請提供 PNG base64，我會立刻補上

# ==========================================
# Streamlit 快取（加速載入）
# ==========================================
@st.cache_data
def get_demo_dataframe_cached():
    return get_demo_dataframe()