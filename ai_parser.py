# ai_parser.py
import pandas as pd
from config import DAYS

def ai_parse_remarks(students_df: pd.DataFrame):
    """
    AI 智能解析 remarks 欄位，並自動更新對應欄位
    - 支援中文自然語言描述
    - 完全本地運行，零成本
    - 返回更新後的 DataFrame
    """
    if students_df.empty:
        return students_df

    df = students_df.copy()
    updated_count = 0

    for idx, row in df.iterrows():
        remarks = str(row.get('remarks', '')).strip()
        if not remarks or remarks.lower() == 'nan':
            continue

        remarks_lower = remarks.lower()

        changed = False

        # 1. 固定總值班偵測（最常用）
        day_map = {
            '週一': 'MONDAY', 'monday': 'MONDAY', '一': 'MONDAY',
            '週二': 'TUESDAY', 'tuesday': 'TUESDAY', '二': 'TUESDAY',
            '週三': 'WEDNESDAY', 'wednesday': 'WEDNESDAY', '三': 'WEDNESDAY',
            '週四': 'THURSDAY', 'thursday': 'THURSDAY', '四': 'THURSDAY',
            '週五': 'FRIDAY', 'friday': 'FRIDAY', '五': 'FRIDAY'
        }
        for keyword, day_code in day_map.items():
            if (keyword in remarks_lower or day_code.lower() in remarks_lower) and any(x in remarks_lower for x in ['固定', '總值班', '固定值班']):
                df.at[idx, 'fixed_general_duty'] = day_code
                changed = True
                break

        # 2. 可用日子偵測
        if any(x in remarks_lower for x in ['可用', '可值班', '優先', '能值班']):
            detected_days = []
            for day in DAYS:
                if day.lower() in remarks_lower or day.lower()[:3] in remarks_lower or day.lower()[:1] in remarks_lower:
                    detected_days.append(day)
            if detected_days:
                df.at[idx, 'available'] = ','.join(detected_days)
                changed = True

        # 3. 職級偵測（隊長 / AHP）
        if any(x in remarks_lower for x in ['隊長', 'assistant head', 'ahp', '副隊長', 'assistant']):
            if df.at[idx, 'role'] != "Assistant Head Study Prefect":
                df.at[idx, 'role'] = "Assistant Head Study Prefect"
                changed = True

        # 4. 老帶新優先標記（未來可擴充優先邏輯）
        if any(x in remarks_lower for x in ['老帶新', '帶新', '新手', '指導']):
            # 目前先在 remarks 加上標記，後續可在 generate_roster 中加強優先
            current_remarks = str(df.at[idx, 'remarks'])
            if '老帶新優先' not in current_remarks:
                df.at[idx, 'remarks'] = current_remarks + " [老帶新優先]"
                changed = True

        # 5. 請假偵測（僅記錄提示）
        if any(x in remarks_lower for x in ['請假', '休假', '不在', '缺席']):
            # 這裡僅在 console 提示，實際請假仍由側邊欄多選處理
            print(f"🔍 AI 偵測到請假提示：{row.get('name')} - {remarks}")

        if changed:
            updated_count += 1

    if updated_count > 0:
        print(f"✅ AI 智能解析完成！共更新 {updated_count} 位同學的欄位")
    else:
        print("ℹ️  沒有偵測到需要更新的 remarks 內容")

    return df
