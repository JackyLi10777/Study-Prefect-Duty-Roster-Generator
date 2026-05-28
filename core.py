# core.py
import pandas as pd
import random
from typing import List, Optional, Tuple
import streamlit as st
from config import DAYS, ROWS_ROSTER, WEIGHTS, DAILY_VERSES

def generate_roster(
    students_df: pd.DataFrame,
    leave_students: List[str] = None,
    seed: int = 42
) -> pd.DataFrame:
    """核心排班演算法 - 完整版（支援 Room 303 / Room 202 各需 2 人 + Tuesday/Friday Room202 自動留空）"""
    if students_df.empty:
        st.error("❌ 名冊為空，無法生成排班表")
        return pd.DataFrame()

    random.seed(seed)
    if leave_students is None:
        leave_students = []

    roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    # 記錄每人當週已排班次數與最後值班日
    weekly_count = {name: 0 for name in students_df["姓名"].tolist()}
    last_duty_day = {name: -1 for name in students_df["姓名"].tolist()}

    for day_idx, day in enumerate(DAYS):
        assigned_today = set()

        for role in ROWS_ROSTER:
            # Room 202 Tuesday / Friday 自動留空
            if "Room202" in role and day in ["TUESDAY", "FRIDAY"]:
                roster.at[role, day] = "⬜"
                continue

            # 決定該崗位需要的人數
            needed = 2 if any(x in role for x in ["Room303", "Room202"]) else 1

            candidates = []
            for _, rec in students_df.iterrows():
                name = rec["姓名"]
                if name in leave_students or name in assigned_today:
                    continue
                if day not in str(rec["可用日子"]).upper().split(","):
                    continue
                if rec["職級"] == "Assistant Head Study Prefect" and "Assist" not in role:
                    continue
                if rec["職級"] != "Assistant Head Study Prefect" and "Assist" in role:
                    continue

                # 連續值班懲罰 + 總負荷排序
                consecutive_penalty = 10 if last_duty_day[name] == day_idx - 1 else 0
                current_load = weekly_count[name] * 1.2 + rec["歷史動態(點)"]
                score = current_load + consecutive_penalty
                candidates.append((name, score, rec["年級"]))

            # 排序後取前 needed 人
            candidates.sort(key=lambda x: x[1])
            selected = [c[0] for c in candidates[:needed]]

            for name in selected:
                roster.at[role, day] = name
                assigned_today.add(name)
                weekly_count[name] += WEIGHTS.get(role, 1.5)
                last_duty_day[name] = day_idx

            # 若人手不足
            if len(selected) < needed:
                roster.at[role, day] = f"❌ 缺{needed - len(selected)}人"

    return roster


def validate_and_compute(roster_df: pd.DataFrame, students_df: pd.DataFrame, leave_students: List[str]) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """驗證並計算累計負荷"""
    errors = []
    warnings = []

    # 1. 重複值班檢查
    for day in roster_df.columns:
        assigned = roster_df[day].dropna().tolist()
        if len(assigned) != len(set(assigned)):
            errors.append(f"星期{day} 出現重複值班")

    # 2. 空缺檢查
    for role, row in roster_df.iterrows():
        for day, val in row.items():
            if pd.isna(val) or val == "":
                if not ("Room202" in role and day in ["TUESDAY", "FRIDAY"]):
                    warnings.append(f"{role} - {day} 尚有空缺")

    # 3. 生成累計報表
    report = students_df.copy()
    report["本週值班次數"] = 0
    report["本週加權負荷"] = 0.0

    for _, row in roster_df.iterrows():
        for val in row:
            if isinstance(val, str) and val.strip() and val not in ["⬜", "❌"]:
                name = val.strip()
                idx = report[report["姓名"] == name].index
                if not idx.empty:
                    report.loc[idx, "本週值班次數"] += 1
                    role_weight = next((w for r, w in WEIGHTS.items() if r in row.name), 1.5)
                    report.loc[idx, "本週加權負荷"] += role_weight

    report["最終總計加權負荷 (點)"] = report["歷史動態(點)"] + report["本週加權負荷"]
    return report, errors, warnings


def recommend_substitutes(
    roster_df: pd.DataFrame,
    students_df: pd.DataFrame,
    chosen_day: str,
    chosen_role: str
) -> Tuple[Optional[pd.DataFrame], str]:
    """智慧替補推薦 - 按總負荷由低到高排序"""
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if not current_person or current_person in ["⬜", "❌"]:
        return None, "該時段目前無人值班"

    subs = []
    for _, rec in students_df.iterrows():
        name = rec["姓名"]
        if name == current_person:
            continue
        if chosen_day not in str(rec["可用日子"]).upper():
            continue
        if rec["職級"] == "Assistant Head Study Prefect" and "Assist" not in chosen_role:
            continue

        subs.append({
            "姓名": name,
            "年級": rec["年級"],
            "當前總點數": rec["歷史動態(點)"] + 1.0  # 預估本次
        })

    if not subs:
        return None, "找不到合適替補人員"

    sub_df = pd.DataFrame(subs).sort_values(by="當前總點數")
    return sub_df, ""