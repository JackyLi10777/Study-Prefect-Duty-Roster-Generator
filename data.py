# data.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
數據管理模組 - 示範資料、格式範例與驗證

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final
"""

import pandas as pd
from config import ROWS_ROSTER, DAYS, is_assistant_head_only_role

def get_demo_dataframe() -> pd.DataFrame:
    """官方示範名冊（包含 Assistant Head Study Prefect 與普通 Study Prefect）
    已完整支援多槽位顯示（Room 303 / Room 202 各兩人）"""
    demo_data = [
        {
            "name": "李創杰",
            "form": "F.5",
            "class": "5D",
            "role": "Assistant Head Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 12,
            "history_weight": 18.5,
            "remarks": "老帶新，F.3 優先，領導核心"
        },
        {
            "name": "陳子軒",
            "form": "F.5",
            "class": "5A",
            "role": "Study Prefect",
            "fixed_general_duty": "MONDAY",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 9,
            "history_weight": 13.5,
            "remarks": ""
        },
        {
            "name": "黃家樂",
            "form": "F.4",
            "class": "4B",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 7,
            "history_weight": 10.0,
            "remarks": "Room302 經驗豐富"
        },
        {
            "name": "張凱傑",
            "form": "F.4",
            "class": "4A",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 9,
            "history_weight": 13.5,
            "remarks": ""
        },
        {
            "name": "林俊賢",
            "form": "F.3",
            "class": "3C",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 4,
            "history_weight": 5.5,
            "remarks": "新任，老帶新"
        },
        {
            "name": "吳柏樂",
            "form": "F.3",
            "class": "3A",
            "role": "Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 3,
            "history_weight": 4.0,
            "remarks": ""
        },
        {
            "name": "劉子浩",
            "form": "F.5",
            "class": "5B",
            "role": "Assistant Head Study Prefect",
            "fixed_general_duty": "WEDNESDAY",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 15,
            "history_weight": 22.0,
            "remarks": "固定星期三值班，領導經驗豐富"
        },
        {
            "name": "歐陽浚鋒",
            "form": "F.4",
            "class": "4C",
            "role": "Assistant Head Study Prefect",
            "fixed_general_duty": "NONE",
            "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "history_duties": 8,
            "history_weight": 12.0,
            "remarks": ""
        }
    ]
    df = pd.DataFrame(demo_data)
    # 確保數據類型正確
    df["history_duties"] = pd.to_numeric(df["history_duties"], errors='coerce').fillna(0).astype(int)
    df["history_weight"] = pd.to_numeric(df["history_weight"], errors='coerce').fillna(0.0).astype(float)
    return df


def get_sample_format_dataframe() -> pd.DataFrame:
    """名冊格式範例（供使用者下載參考，用於傳統格式導入）"""
    sample_data = [
        {
            "姓名": "李創杰",
            "年級": "F.5",
            "班別": "5D",
            "職級": "Assistant Head Study Prefect",
            "學年固定總值班": "NONE",
            "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "歷史累計(次)": 12,
            "歷史動態(點)": 18.5,
            "備註": "老帶新，F.3 優先，領導核心"
        },
        {
            "姓名": "陳子軒",
            "年級": "F.5",
            "班別": "5A",
            "職級": "Study Prefect",
            "學年固定總值班": "MONDAY",
            "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
            "歷史累計(次)": 9,
            "歷史動態(點)": 13.5,
            "備註": ""
        }
    ]
    return pd.DataFrame(sample_data)


def get_empty_students_df() -> pd.DataFrame:
    """建立空的學生名冊 DataFrame（供初始化使用）"""
    return pd.DataFrame(columns=[
        "name", "form", "class", "role",
        "fixed_general_duty", "available",
        "history_duties", "history_weight", "remarks"
    ])


def validate_students_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """驗證學生名冊 DataFrame 是否符合業務規則"""
    if df.empty:
        return False, "名冊為空，請先載入或新增資料"
    
    required_cols = ["name", "form", "role", "available"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return False, f"缺少必要欄位: {missing}"
    
    # 檢查 Assistant Head 限制
    ahp_count = len(df[df["role"].str.contains("Assistant Head", na=False)])
    if ahp_count == 0:
        return True, "警告：目前名冊中沒有 Assistant Head Study Prefect"
    
    return True, "名冊驗證通過"


print("✅ data.py 已載入完成 - 數據初始化與驗證模組就緒")
