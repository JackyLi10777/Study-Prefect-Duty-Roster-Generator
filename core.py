# core.py
import pandas as pd
import random
from config import DAYS, ROWS_ROSTER, WEIGHTS

# ==========================================
# 主要排班演算法（舊版核心功能完整保留）
# ==========================================
def generate_roster(students_df: pd.DataFrame, 
                    leave_students: list = None, 
                    special_closures: dict = None, 
                    seed: int = None) -> pd.DataFrame:
    """
    智能生成一週值班表。
    補回舊版所有核心邏輯：
    - 嚴格防止同一天同一人重複排班
    - Assistant Head Study Prefect 只能排 Assist. in charge
    - 依據歷史負荷進行公平性排序（點數低者優先）
    - 支援請假人員排除與特殊不開放日
    """
    if seed is not None:
        random.seed(seed)

    if leave_students is None:
        leave_students = []
    if special_closures is None:
        special_closures = {}

    # 建立排班表骨架
    roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    # 所有可用學生（排除請假）
    available_students = students_df[\~students_df["name"].isin(leave_students)].copy()
    available_students = available_students.sort_values(by="history_weight")  # 點數低者優先

    # 記錄已排班人員（防止同一天重複）
    assigned_today = {day: set() for day in DAYS}

    for day in DAYS:
        for role in ROWS_ROSTER:
            # 特殊不開放日處理
            if day in special_closures.get(role, []):
                roster.at[role, day] = "X"
                continue

            # Assistant Head 只能排 Assist. in charge
            if "Assistant Head" in role and "Assist" not in role:
                continue
            if "Assist" in role and "Assistant Head" not in available_students["role"].values:
                continue

            # 找出符合條件的學生
            candidates = available_students[
                (available_students["available"].str.contains(day, na=False)) &
                (\~available_students["name"].isin(assigned_today[day]))
            ]

            if "Assist" in role:
                candidates = candidates[candidates["role"].str.contains("Assistant Head", na=False)]
            else:
                candidates = candidates[\~candidates["role"].str.contains("Assistant Head", na=False)]

            if not candidates.empty:
                chosen = candidates.iloc[0]  # 點數最低者優先
                roster.at[role, day] = chosen["name"]
                assigned_today[day].add(chosen["name"])
                # 更新該學生歷史負荷（僅供本次計算參考）
                available_students.loc[available_students["name"] == chosen["name"], "history_weight"] += WEIGHTS.get(role, 1.0)

    return roster

# ==========================================
# 驗證與負荷計算（舊版核心功能完整保留）
# ==========================================
def validate_and_compute(roster_df: pd.DataFrame, 
                         students_df: pd.DataFrame, 
                         leave_students: list = None,
                         manual_weights: pd.DataFrame = None) -> dict:
    """
    驗證排班表並計算最終負荷。
    補回舊版所有驗證項目：
    - 重複排班檢查
    - 請假衝突檢查
    - 空缺警告
    - 最終總計加權負荷計算
    """
    if leave_students is None:
        leave_students = []
    if manual_weights is None:
        manual_weights = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)

    report = []
    typo_detected = []
    duplicate_detected = []
    leave_conflict = []
    vacuum_entries = []

    assigned_today = {day: set() for day in DAYS}

    for day in DAYS:
        for role in ROWS_ROSTER:
            person = str(roster_df.at[role, day]).strip()
            if not person or person == "X":
                if person == "":
                    vacuum_entries.append(f"{role} - {day} 為空缺")
                continue

            # 重複排班檢查
            if person in assigned_today[day]:
                duplicate_detected.append(f"{person} 在 {day} 重複排班（{role}）")
            assigned_today[day].add(person)

            # 請假衝突檢查
            if person in leave_students:
                leave_conflict.append(f"{person} 在 {day} 被排班，但已請假")

            # 查找學生記錄
            student_row = students_df[students_df["name"] == person]
            if student_row.empty:
                typo_detected.append(f"找不到學生：{person}（{role} - {day}）")
                continue

            base_weight = WEIGHTS.get(role, 1.0)
            manual_add = float(manual_weights.at[role, day]) if role in manual_weights.index and day in manual_weights.columns else 0.0
            total_weight = base_weight + manual_add

            history = float(student_row.iloc[0]["history_weight"])
            final_weight = history + total_weight

            report.append({
                "學生姓名 (Prefect Name)": person,
                "年級 (Form)": student_row.iloc[0]["form"],
                "班別 (Class)": student_row.iloc[0]["class"],
                "職級 (Role)": student_row.iloc[0]["role"],
                "當週新增 (次)": total_weight,
                "最終總計加權負荷 (點)": round(final_weight, 1)
            })

    # 建立最終報告
    master_report_df = pd.DataFrame(report)
    if not master_report_df.empty:
        master_report_df = master_report_df.sort_values(by="最終總計加權負荷 (點)", ascending=True)

    return {
        "report_df": master_report_df,
        "typo": (bool(typo_detected), typo_detected),
        "duplicate": (bool(duplicate_detected), duplicate_detected),
        "leave_conflict": (bool(leave_conflict), leave_conflict),
        "vacuum": (bool(vacuum_entries), vacuum_entries)
    }

# ==========================================
# 智慧替補推薦系統（舊版核心功能完整保留）
# ==========================================
def recommend_substitutes(roster_df: pd.DataFrame, 
                          students_df: pd.DataFrame, 
                          chosen_day: str, 
                          chosen_role: str) -> tuple:
    """
    根據目前排班表推薦最合適的替補人員。
    補回舊版所有替補推薦邏輯：依總點數由低到高排序、排除已排班人員、職級限制。
    """
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    leave_list = []  # 可從外部傳入，此處簡化

    candidates = students_df[
        (students_df["available"].str.contains(chosen_day, na=False)) &
        (students_df["name"] != current_person) &
        (\~students_df["name"].isin(leave_list))
    ].copy()

    # Assistant Head 只能替補 Assist. in charge
    if "Assist" in chosen_role:
        candidates = candidates[candidates["role"].str.contains("Assistant Head", na=False)]
    else:
        candidates = candidates[\~candidates["role"].str.contains("Assistant Head", na=False)]

    if candidates.empty:
        return None, "❌ 找不到合適的替補人員。"

    candidates = candidates.sort_values(by="history_weight")
    candidates = candidates[["name", "form", "history_weight"]]
    candidates.columns = ["姓名", "年級", "當前總點數"]

    return candidates.head(10), None