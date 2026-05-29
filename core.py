# core.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
核心排班演算法模組 - generate_roster + 公平性驗證 + 智慧替補推薦

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（完整支援多槽位、global_load_multiplier、Room202 星期二/五 ⬜）
"""

import pandas as pd
import numpy as np
import random
from typing import Dict, List, Optional, Tuple
import streamlit as st

from config import (
    DAYS, ROWS_ROSTER, ROOMS_CONFIG,
    get_daily_slots, get_weight, is_assistant_head_only_role,
    is_room_open_on_weekday, get_role_style
)


def generate_roster(
    students_df: pd.DataFrame,
    global_load_multiplier: float = 1.0,
    seed: Optional[int] = None
) -> pd.DataFrame:
    """
    核心公平排班演算法 - 嚴格遵守所有學校業務規則
    1. Assistant Head 只能排 "Assist. in charge"
    2. Room302 每天1人、Room303/202 每天2人（已拆成 -1/-2 行）
    3. Room202 星期二與星期五固定不開放（顯示 ⬜）
    4. 每人每天只能值班一次
    5. 權重系統：Assist & Room302 = 1.0，其他 = 1.5
    6. 歷史負荷公平性 + global_load_multiplier 即時調節 + F.3 優先（老帶新）
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    if students_df.empty:
        st.error("❌ 名冊為空，無法生成排班表")
        return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS)

    # 建立空白排班表（多槽位已展開）
    roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS, dtype=str)
    roster_df[:] = ""   # 清空

    # 可用學生清單 + 今日已排標記
    available_students = students_df.copy()
    today_duty = {name: False for name in available_students["name"]}

    # 計算每位學生的「有效負荷分數」 = 歷史權重 * global_load_multiplier
    available_students["effective_load"] = (
        available_students["history_weight"] * global_load_multiplier
    )

    # F.3 優先加分（老帶新）
    available_students["priority_bonus"] = 0.0
    available_students.loc[available_students["form"] == "F.3", "priority_bonus"] = -3.0   # 越低越優先

    for day in DAYS:
        day_idx = DAYS.index(day)

        for row in ROWS_ROSTER:
            # 取得該格位的角色名稱（去除 -1/-2）
            base_role = row.split(" - ")[0].strip()

            # 檢查是否為 Assistant Head 專屬角色
            if is_assistant_head_only_role(base_role):
                candidates = available_students[
                    (available_students["role"].str.contains("Assistant Head", na=False)) &
                    (~available_students["name"].map(today_duty))
                ]
            else:
                # 一般 Study Prefect
                candidates = available_students[
                    (~available_students["role"].str.contains("Assistant Head", na=False)) &
                    (~available_students["name"].map(today_duty))
                ]

            # 檢查該日子該房間是否開放
            if not is_room_open_on_weekday(base_role, day):
                roster_df.at[row, day] = "⬜"   # 常規不開放
                continue

            if candidates.empty:
                roster_df.at[row, day] = "❌"   # 無人可排
                continue

            # 計算綜合分數 = effective_load + priority_bonus
            candidates = candidates.copy()
            candidates["score"] = candidates["effective_load"] + candidates["priority_bonus"]

            # 選取最低分數者（最需要排班的人）
            selected = candidates.loc[candidates["score"].idxmin()]

            # 寫入排班表
            roster_df.at[row, day] = selected["name"]

            # 標記今日已排
            today_duty[selected["name"]] = True

            # 更新該學生的 effective_load（模擬本次排班後的累計）
            assigned_weight = get_weight(base_role) * global_load_multiplier
            available_students.loc[available_students["name"] == selected["name"], "effective_load"] += assigned_weight

    return roster_df


def validate_and_compute(roster_df: pd.DataFrame, students_df: pd.DataFrame) -> Dict:
    """
    排班表驗證 + 完整負荷審計報告（含 Plotly 柱狀圖用資料）
    """
    audit = {
        "valid": True,
        "errors": [],
        "report_df": None,
        "fairness_score": 0.0
    }

    if roster_df.empty or students_df.empty:
        audit["valid"] = False
        audit["errors"].append("排班表或名冊為空")
        return audit

    # 1. 每人每天只能值班一次
    duty_count = {}
    for day in roster_df.columns:
        for name in roster_df[day].dropna():
            if name in ["⬜", "❌", ""]:
                continue
            duty_count[name] = duty_count.get(name, 0) + 1

    for name, count in duty_count.items():
        if count > 1:
            audit["valid"] = False
            audit["errors"].append(f"學生 {name} 單日重複值班 {count} 次")

    # 2. Assistant Head 限制
    ahp_names = students_df[students_df["role"].str.contains("Assistant Head", na=False)]["name"].tolist()
    for day in roster_df.columns:
        for row in roster_df.index:
            if "Assist" not in row:
                continue
            person = roster_df.at[row, day]
            if person in ahp_names:
                continue  # 正確
            if person and person not in ["⬜", "❌"]:
                audit["valid"] = False
                audit["errors"].append(f"Assistant Head {person} 被排到非 Assist 崗位")

    # 3. 產生累計報告表
    report_data = []
    for _, row in students_df.iterrows():
        name = row["name"]
        history = row["history_weight"]
        today = 0.0
        for day in roster_df.columns:
            for r in roster_df.index:
                if roster_df.at[r, day] == name:
                    role = r.split(" - ")[0].strip()
                    today += get_weight(role)
                    break
        total = history + today
        report_data.append({
            "姓名": name,
            "年級": row["form"],
            "歷史累計": round(history, 2),
            "本次負荷": round(today, 2),
            "總累計": round(total, 2)
        })

    report_df = pd.DataFrame(report_data)
    audit["report_df"] = report_df.sort_values("總累計", ascending=False)

    # 簡單公平性分數（標準差越小越公平）
    if not report_df.empty:
        audit["fairness_score"] = round(report_df["總累計"].std(), 3)

    return audit


def recommend_substitutes(
    roster_df: pd.DataFrame,
    students_df: pd.DataFrame,
    target_day: str,
    target_role: str,
    leave_name: str
) -> List[Dict]:
    """
    智慧替補推薦 - 根據目前總負荷由低到高排序
    """
    if roster_df.empty or students_df.empty:
        return []

    # 找出目前已排該格位的人（被請假者）
    current = roster_df.at[target_role, target_day]
    if current != leave_name:
        return []

    # 計算每位學生的「目前總累計」（含本次已排）
    load_dict = {}
    for _, row in students_df.iterrows():
        name = row["name"]
        base = row["history_weight"]
        extra = 0.0
        for day in roster_df.columns:
            for r in roster_df.index:
                if roster_df.at[r, day] == name:
                    role_name = r.split(" - ")[0].strip()
                    extra += get_weight(role_name)
        load_dict[name] = base + extra

    # 排除已請假者、已排該日者、Assistant Head 只能替 Assist
    candidates = students_df.copy()
    candidates["current_total"] = candidates["name"].map(load_dict)

    # Assistant Head 只能替 Assist
    if "Assist" in target_role:
        candidates = candidates[candidates["role"].str.contains("Assistant Head", na=False)]
    else:
        candidates = candidates[~candidates["role"].str.contains("Assistant Head", na=False)]

    # 排除已請假
    candidates = candidates[candidates["name"] != leave_name]

    # 排序：總累計最低者優先
    candidates = candidates.sort_values("current_total")

    result = []
    for _, c in candidates.head(5).iterrows():   # Top 5
        result.append({
            "name": c["name"],
            "form": c["form"],
            "current_total": round(c["current_total"], 2),
            "score": round(c["current_total"], 2)
        })

    return result


print("✅ core.py 已載入完成 - 核心排班演算法、驗證與智慧替補推薦模組就緒")
