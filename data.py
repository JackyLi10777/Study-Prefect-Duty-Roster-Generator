# data.py
import pandas as pd

# ==========================================
# 示範數據（Sing Yin 官方示範名冊）
# ==========================================
DEMO_DATA = [
    {
        "name": "陳卓軒",
        "form": "F.5",
        "class": "5A",
        "role": "Assistant Head Study Prefect",
        "fixed_general_duty": "MONDAY",
        "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
        "history_duties": 12,
        "history_weight": 12.0,
        "remarks": "隊長 / 固定週一總值班"
    },
    {
        "name": "李浩然",
        "form": "F.5",
        "class": "5B",
        "role": "Assistant Head Study Prefect",
        "fixed_general_duty": "WEDNESDAY",
        "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY",
        "history_duties": 10,
        "history_weight": 10.0,
        "remarks": "固定週三總值班"
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
        "remarks": "老帶新優先"
    },
    {
        "name": "黃子軒",
        "form": "F.4",
        "class": "4B",
        "role": "Study Prefect",
        "fixed_general_duty": "NONE",
        "available": "TUESDAY,WEDNESDAY,FRIDAY",
        "history_duties": 8,
        "history_weight": 12.0,
        "remarks": ""
    },
    {
        "name": "林俊傑",
        "form": "F.3",
        "class": "3A",
        "role": "Study Prefect",
        "fixed_general_duty": "NONE",
        "available": "MONDAY,TUESDAY,THURSDAY",
        "history_duties": 6,
        "history_weight": 9.0,
        "remarks": "需老帶新"
    },
    {
        "name": "王偉倫",
        "form": "F.5",
        "class": "5C",
        "role": "Study Prefect",
        "fixed_general_duty": "NONE",
        "available": "MONDAY,WEDNESDAY,FRIDAY",
        "history_duties": 7,
        "history_weight": 10.5,
        "remarks": ""
    },
    {
        "name": "劉家豪",
        "form": "F.4",
        "class": "4C",
        "role": "Study Prefect",
        "fixed_general_duty": "NONE",
        "available": "TUESDAY,THURSDAY",
        "history_duties": 5,
        "history_weight": 7.5,
        "remarks": ""
    }
]

# ==========================================
# 欄位映射字典（支援多種 Excel / CSV 格式）
# ==========================================
COLUMN_MAPPING = {
    # 姓名相關
    '姓名': 'name',
    'name': 'name',
    'Prefect Name': 'name',
    '學生姓名': 'name',
    '學生': 'name',
    
    # 年級
    '年級': 'form',
    'form': 'form',
    'Form': 'form',
    'Grade': 'form',
    
    # 班別
    '班別': 'class',
    'class': 'class',
    'Class': 'class',
    
    # 職級
    '職級': 'role',
    'role': 'role',
    'Role': 'role',
    
    # 固定值班
    '學年固定總值班': 'fixed_general_duty',
    'fixed_general_duty': 'fixed_general_duty',
    '固定值班': 'fixed_general_duty',
    
    # 可用日子
    '可用日子': 'available',
    'available': 'available',
    '可用天數': 'available',
    
    # 歷史數據
    '歷史累計(次)': 'history_duties',
    'history_duties': 'history_duties',
    '歷史次數': 'history_duties',
    
    '歷史動態(點)': 'history_weight',
    'history_weight': 'history_weight',
    '歷史點數': 'history_weight',
    '歷史累積': 'history_weight',
    
    # 備註
    '備註': 'remarks',
    'remarks': 'remarks',
    'Remark': 'remarks'
}

# ==========================================
# 示範名冊 DataFrame 快速生成函數
# ==========================================
def get_demo_dataframe():
    """返回示範名冊 DataFrame"""
    return pd.DataFrame(DEMO_DATA)

# ==========================================
# 格式範例 DataFrame（用於下載範例檔）
# ==========================================
def get_sample_format_dataframe():
    """返回名冊導入格式範例"""
    sample_data = [
        {"姓名": "陳卓軒", "年級": "F.5", "班別": "5A", "職級": "Assistant Head Study Prefect", 
         "學年固定總值班": "MONDAY", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", 
         "歷史累計(次)": 12, "歷史動態(點)": 12.0, "備註": "隊長"},
        {"姓名": "李浩然", "年級": "F.5", "班別": "5B", "職級": "Assistant Head Study Prefect", 
         "學年固定總值班": "WEDNESDAY", "可用日子": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", 
         "歷史累計(次)": 10, "歷史動態(點)": 10.0, "備註": ""},
        {"姓名": "張凱傑", "年級": "F.4", "班別": "4A", "職級": "Study Prefect", 
         "學年固定總值班": "NONE", "可用日子": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", 
         "歷史累計(次)": 9, "歷史動態(點)": 13.5, "備註": ""},
    ]
    return pd.DataFrame(sample_data)

# ==========================================
# 測試用：檢查模組是否正確載入
# ==========================================
if __name__ == "__main__":
    print("✅ data.py 模組載入成功")
    print(f"   示範數據筆數：{len(DEMO_DATA)}")
    print(f"   欄位映射字典大小：{len(COLUMN_MAPPING)}")
