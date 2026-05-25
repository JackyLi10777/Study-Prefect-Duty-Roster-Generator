# data.py
import pandas as pd
import io

def get_demo_dataframe():
    """官方示範名冊（7 位領袖生，符合學校實際需求）"""
    data = [
        {"name": "陳家俊", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "fixed_general_duty": "MONDAY", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 18, "history_weight": 28.5, "remarks": "老帶新優先"},
        {"name": "李浩然", "form": "F.5", "class": "5B", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 12, "history_weight": 19.0, "remarks": ""},
        {"name": "張凱傑", "form": "F.4", "class": "4A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 9, "history_weight": 13.5, "remarks": ""},
        {"name": "黃子軒", "form": "F.4", "class": "4B", "role": "Study Prefect", "fixed_general_duty": "WEDNESDAY", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 11, "history_weight": 16.0, "remarks": "Room302 經驗豐富"},
        {"name": "林家豪", "form": "F.3", "class": "3A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 4, "history_weight": 6.0, "remarks": "新任，老帶新"},
        {"name": "王浩宇", "form": "F.3", "class": "3B", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 5, "history_weight": 7.5, "remarks": ""},
        {"name": "劉俊熙", "form": "F.5", "class": "5C", "role": "Study Prefect", "fixed_general_duty": "FRIDAY", "available": "TUESDAY,THURSDAY,FRIDAY", "history_duties": 14, "history_weight": 22.0, "remarks": "Assistant Head 候補"}
    ]
    return pd.DataFrame(data)

def get_sample_format_dataframe():
    """下載用的名冊格式範例（AI 智能導入可自動匹配此格式）"""
    data = [
        ["姓名", "年級", "班別", "職級", "學年固定總值班", "可用日子", "歷史累計(次)", "歷史動態(點)", "備註"],
        ["陳家俊", "F.5", "5A", "Assistant Head Study Prefect", "MONDAY", "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", 18, 28.5, "老帶新優先"],
        ["李浩然", "F.5", "5B", "Study Prefect", "NONE", "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", 12, 19.0, ""],
        ["張凱傑", "F.4", "4A", "Study Prefect", "NONE", "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", 9, 13.5, ""],
        ["黃子軒", "F.4", "4B", "Study Prefect", "WEDNESDAY", "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", 11, 16.0, "Room302 經驗豐富"],
        ["林家豪", "F.3", "3A", "Study Prefect", "NONE", "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", 4, 6.0, "新任，老帶新"],
    ]
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# 額外工具函數（供未來擴充使用）
def get_empty_students_df():
    """建立空的學生名冊框架"""
    columns = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
    return pd.DataFrame(columns=columns)