# data.py
import pandas as pd
import io
import streamlit as st
from config import DAYS, ROWS_ROSTER

# ==========================================
# 示範資料與格式範例（完整版）
# ==========================================

def get_demo_dataframe() -> pd.DataFrame:
    """
    提供 Sing Yin Study Prefect 完整示範名冊資料
    包含 Head / Assistant Head / 普通 Prefect，多樣年級與可用日子
    """
    demo_data = [
        {"姓名": "李創杰", "年級": "F.5", "班別": "5E", "職級": "Head Study Prefect",
         "學年固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
         "歷史累計(次)": 12, "歷史動態(點)": 18.5, "備註": "Head Prefect"},
        {"姓名": "古本正", "年級": "F.5", "班別": "5C", "職級": "Assistant Head Study Prefect",
         "學年固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
         "歷史累計(次)": 10, "歷史動態(點)": 15.0, "備註": "Assistant Head"},
        {"姓名": "歐陽浚鋒", "年級": "F.5", "班別": "5A", "職級": "Assistant Head Study Prefect",
         "學年固定總值班": "NONE", "可用日子": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
         "歷史累計(次)": 9, "歷史動態(點)": 13.5, "備註": "Assistant Head"},
        {"姓名": "許舜喬", "年級": "F.4", "班別": "4C", "職級": "Study Prefect",
         "學年固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
         "歷史累計(次)": 8, "歷史動態(點)": 12.0, "備註": ""},
        {"姓名": "何梓皓", "年級": "F.4", "班別": "4B", "職級": "Study Prefect",
         "學年固定總值班": "NONE", "可用日子": "MONDAY,WEDNESDAY,THURSDAY",
         "歷史累計(次)": 7, "歷史動態(點)": 10.5, "備註": ""},
        {"姓名": "何俊霆", "年級": "F.4", "班別": "4B", "職級": "Study Prefect",
         "學年固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,FRIDAY",
         "歷史累計(次)": 6, "歷史動態(點)": 9.0, "備註": ""},
        {"姓名": "張凱傑", "年級": "F.4", "班別": "4A", "職級": "Study Prefect",
         "學年固定總值班": "NONE", "可用日子": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
         "歷史累計(次)": 9, "歷史動態(點)": 13.5, "備註": ""},
    ]
    df = pd.DataFrame(demo_data)
    # 確保數值欄位型別正確
    df["歷史累計(次)"] = pd.to_numeric(df["歷史累計(次)"], errors="coerce").fillna(0).astype(int)
    df["歷史動態(點)"] = pd.to_numeric(df["歷史動態(點)"], errors="coerce").fillna(0.0).astype(float)
    return df


def get_sample_format_dataframe() -> pd.DataFrame:
    """提供標準名冊格式範例（供用戶下載參考）"""
    sample_data = [
        {"姓名": "張三", "年級": "F.5", "班別": "5A", "職級": "Study Prefect",
         "學年固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
         "歷史累計(次)": 5, "歷史動態(點)": 7.5, "備註": "範例"},
    ]
    return pd.DataFrame(sample_data)


@st.cache_data
def get_sample_excel_bytes() -> bytes:
    """
    產生可下載的 Excel 格式範例檔案（含正確欄位與標題說明）
    """
    df = get_sample_format_dataframe()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Prefect_名冊格式範例", index=False)
        ws = writer.sheets["Prefect_名冊格式範例"]
        ws["A1"] = "Sing Yin Study Prefect 名冊導入格式範例"
        ws["A2"] = "請務必包含以下欄位（AI 會自動匹配）：姓名、年級、班別、職級、學年固定總值班、可用日子、歷史累計(次)、歷史動態(點)、備註"
    output.seek(0)
    return output.getvalue()


# ==========================================
# 額外資料驗證與輔助函數（舊版功能補回）
# ==========================================

def validate_student_dataframe(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    驗證導入的名冊是否符合最低要求
    """
    required_columns = ["姓名", "年級", "職級", "可用日子"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return False, [f"缺少必要欄位：{', '.join(missing)}"]
    return True, []


def get_empty_roster_template() -> pd.DataFrame:
    """返回空白排班表模板（舊版常用功能）"""
    return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")


# ==========================================
# 測試用（本地執行時可直接運行）
# ==========================================
if __name__ == "__main__":
    df = get_demo_dataframe()
    print("✅ 示範資料載入成功，共有", len(df), "位 Prefect")
    print(df.head())
    print("\n✅ 範例 Excel Bytes 已準備好，可直接下載使用")