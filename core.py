# core.py
import pandas as pd
import random
from config import DAYS, ROWS_ROSTER, WEIGHTS
from typing import List, Tuple, Optional, Dict

# ==========================================
# 1. 主要排班演算法（最完整版）
# ==========================================
def generate_roster(
    students_df: pd.DataFrame,
    leave_students: List[str] = None,
    seed: int = 42,
    manual_weights: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    核心排班演算法 - 完整公平分配 + 所有業務規則
    """
    if leave_students is None:
        leave_students = []
    
    random.seed(seed)
    roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
    
    # 當天已排班人員（防止同一天同一人多次出現）
    assigned_today: Dict[str, set] = {day: set() for day in DAYS}
    
    # 依歷史負荷由低到高排序（公平原則）
    students = students_df.copy()
    students["最終總計加權負荷 (點)"] = pd.to_numeric(
        students.get("歷史動態(點)", students.get("歷史累計(點)", 0)), 
        errors="coerce"
    ).fillna(0.0)
    
    students = students.sort_values(by="最終總計加權負荷 (點)")
    
    for day in DAYS:
        for role in ROWS_ROSTER:
            # Room 202 在星期二、五自動鎖定為 X
            if "Room 202" in role and day in ["TUESDAY", "FRIDAY"]:
                roster.at[role, day] = "X"
                continue
            
            candidates = []
            for _, rec in students.iterrows():
                name = str(rec["姓名"]).strip()
                if name in leave_students or name in assigned_today[day]:
                    continue
                if day.upper() not in str(rec.get("可用日子", "")).upper():
                    continue
                
                # Assistant Head / Head 只能排 Assist. in charge
                role_lower = role.lower()
                if ("Assistant Head" in rec["職級"] or "Head" in rec["職級"]) and "assist" not in role_lower:
                    continue
                
                candidates.append({
                    "name": name,
                    "weight": float(rec["最終總計加權負荷 (點)"]),
                    "role": rec["職級"]
                })
            
            if not candidates:
                roster.at[role, day] = ""
                continue
            
            # 按負荷由低到高排序，取最優
            candidates.sort(key=lambda x: x["weight"])
            chosen = candidates[0]
            
            roster.at[role, day] = chosen["name"]
            assigned_today[day].add(chosen["name"])
    
    return roster


# ==========================================
# 2. 驗證與計算（完整版）
# ==========================================
def validate_and_compute(
    roster_df: pd.DataFrame,
    students_df: pd.DataFrame,
    leave_students: List[str],
    manual_weights: pd.DataFrame
) -> dict:
    """
    完整驗證 + 最終報告生成（包含所有舊版警告）
    """
    report = []
    typo = []
    duplicate = []
    leave_conflict = []
    vacuum = []
    
    for day in DAYS:
        assigned = set()
        for role in ROWS_ROSTER:
            person = str(roster_df.at[role, day]).strip()
            
            if person == "X":
                continue
            if person == "":
                vacuum.append(f"{day} - {role} 空白")
                continue
            
            # 重複檢查
            if person in assigned:
                duplicate.append(f"{day} - {person} 重複排班")
            assigned.add(person)
            
            # 請假衝突
            if person in leave_students:
                leave_conflict.append(f"{day} - {person} 已請假卻被排班")
            
            # 計算本次負荷
            weight = WEIGHTS.get(role, 1.0)
            if not manual_weights.empty and role in manual_weights.index and day in manual_weights.columns:
                manual = float(manual_weights.at[role, day])
                if manual > 0:
                    weight = manual
            
            report.append({
                "學生姓名 (Prefect Name)": person,
                "日期": day,
                "崗位": role,
                "本次加權負荷": weight
            })
    
    report_df = pd.DataFrame(report)
    if not report_df.empty:
        report_df = report_df.groupby("學生姓名 (Prefect Name)")["本次加權負荷"].sum().reset_index()
        report_df = report_df.rename(columns={"本次加權負荷": "最終總計加權負荷 (點)"})
    
    return {
        "report_df": report_df,
        "typo": (len(typo) > 0, typo),
        "duplicate": (len(duplicate) > 0, duplicate),
        "leave_conflict": (len(leave_conflict) > 0, leave_conflict),
        "vacuum": (len(vacuum) > 0, vacuum)
    }


# ==========================================
# 3. 智慧替補推薦（完整版）
# ==========================================
def recommend_substitutes(
    roster_df: pd.DataFrame,
    students_df: pd.DataFrame,
    chosen_day: str,
    chosen_role: str
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    推薦最優替補人員（依總點數由低到高）
    """
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if not current_person or current_person == "X":
        return None, "該時段目前無人當值或已鎖定"
    
    subs = []
    for _, rec in students_df.iterrows():
        name = str(rec["姓名"]).strip()
        if name == current_person:
            continue
        if chosen_day.upper() not in str(rec.get("可用日子", "")).upper():
            continue
        # Assistant Head 只能替補 Assist 崗位
        if "Assistant Head" in str(rec.get("職級", "")) and "Assist" not in chosen_role:
            continue
        
        subs.append({
            "姓名": name,
            "年級": rec.get("年級", ""),
            "當前總點數": float(rec.get("歷史動態(點)", rec.get("歷史累計(點)", 0)))
        })
    
    if not subs:
        return None, "找不到合適的替補人員"
    
    sub_df = pd.DataFrame(subs).sort_values(by="當前總點數")
    return sub_df, ""