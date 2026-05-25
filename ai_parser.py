# ai_parser.py
import pandas as pd
import re

# ==========================================
# 1. 星期對應表（中文關鍵字 → 英文代碼）
# ==========================================
DAY_MAP = {
    "週一": "MONDAY",
    "星期一": "MONDAY",
    "周一": "MONDAY",
    "一": "MONDAY",
    "週二": "TUESDAY",
    "星期二": "TUESDAY",
    "周二": "TUESDAY",
    "二": "TUESDAY",
    "週三": "WEDNESDAY",
    "星期三": "WEDNESDAY",
    "周三": "WEDNESDAY",
    "三": "WEDNESDAY",
    "週四": "THURSDAY",
    "星期四": "THURSDAY",
    "周四": "THURSDAY",
    "四": "THURSDAY",
    "週五": "FRIDAY",
    "星期五": "FRIDAY",
    "周五": "FRIDAY",
    "五": "FRIDAY",
}

# ==========================================
# 2. AI 智能解析 Remarks 主函數（完整版）
# ==========================================
def ai_parse_remarks(df: pd.DataFrame) -> pd.DataFrame:
    """
    根據「備註」欄位中的中文描述，自動更新：
    - fixed_general_duty
    - available
    - role（如果提到隊長/副隊長）
    """
    if df.empty or "remarks" not in df.columns:
        return df

    df = df.copy()
    for idx, row in df.iterrows():
        remarks = str(row.get("remarks", "")).strip()
        if not remarks:
            continue

        remarks_upper = remarks.upper()
        name = str(row.get("name", "")).strip()

        # 1. 固定總值班解析
        fixed_day = None
        for cn, en in DAY_MAP.items():
            if cn in remarks:
                fixed_day = en
                break
        if fixed_day:
            df.at[idx, "fixed_general_duty"] = fixed_day

        # 2. 可用日子解析（如果提到「只可」或「可用」）
        available_days = []
        for cn, en in DAY_MAP.items():
            if cn in remarks:
                available_days.append(en)
        if available_days:
            # 如果有明確提到可用日子，就覆蓋
            df.at[idx, "available"] = ",".join(available_days)
        elif "全週" in remarks or "每天" in remarks or "全部" in remarks:
            df.at[idx, "available"] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"

        # 3. 職級解析（隊長、副隊長）
        if any(keyword in remarks_upper for keyword in ["隊長", "HEAD", "CAPTAIN", "總隊長"]):
            df.at[idx, "role"] = "Assistant Head Study Prefect"
        elif any(keyword in remarks_upper for keyword in ["副隊長", "ASSISTANT HEAD"]):
            df.at[idx, "role"] = "Assistant Head Study Prefect"

        # 4. 老帶新標記（F.3 學生）
        if "老帶新" in remarks or "帶新" in remarks or "F3" in remarks_upper or "中三" in remarks:
            if pd.isna(df.at[idx, "available"]) or df.at[idx, "available"] == "":
                df.at[idx, "available"] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"

    return df

# ==========================================
# 3. 測試用示範函數（開發時可呼叫）
# ==========================================
def test_ai_parser():
    test_df = pd.DataFrame({
        "name": ["陳卓軒", "李浩然", "張凱傑"],
        "form": ["F.5", "F.5", "F.4"],
        "role": ["Study Prefect", "Study Prefect", "Study Prefect"],
        "fixed_general_duty": ["NONE", "NONE", "NONE"],
        "available": ["", "", ""],
        "history_duties": [12, 10, 9],
        "history_weight": [12.0, 10.0, 13.5],
        "remarks": [
            "固定週一總值班 / 隊長",
            "只可週三和週五",
            "老帶新 / 中三學生優先配對"
        ]
    })
    updated = ai_parse_remarks(test_df)
    print("✅ AI 解析測試結果：")
    print(updated[["name", "fixed_general_duty", "available", "role", "remarks"]])
    return updated

print("✅ ai_parser.py 載入完成 | AI 智能解析 Remarks 功能已就緒")
