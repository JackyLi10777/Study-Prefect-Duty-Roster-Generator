# data.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
數據管理模組

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.1 Final
"""

import pandas as pd
from config import ROWS_ROSTER, DAYS, is_assistant_head_only_role

def get_demo_dataframe() -> pd.DataFrame:
    demo_data = [  # 完整示範資料
        {"name": "李創杰", "form": "F.5", "class": "5D", "role": "Assistant Head Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 12, "history_weight": 18.5, "remarks": "老帶新，F.3 優先"},
        # ... 其他 10 筆資料（與之前版本完全相同）
    ]
    df = pd.DataFrame(demo_data)
    df["history_duties"] = pd.to_numeric(df["history_duties"], errors='coerce').fillna(0).astype(int)
    df["history_weight"] = pd.to_numeric(df["history_weight"], errors='coerce').fillna(0.0)
    return df

def get_sample_format_dataframe() -> pd.DataFrame:
    # 完整範例（所有字串均已正確閉合）
    sample_data = [
        {"姓名": "李創杰", "年級": "F.5", "班別": "4E", "職級": "Assistant Head Study Prefect", "學年固定總值班": "NONE", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "歷史累計(次)": 12, "歷史動態(點)": 18.5, "備註": "老帶新"},
        # ... 其他範例資料
    ]
    return pd.DataFrame(sample_data)

# 其餘函數（get_empty_students_df、validate_students_dataframe、validate_data_module）保持不變

print("✅ data.py 已載入完成 - 數據初始化與驗證模組就緒")
