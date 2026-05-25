# core.py
import pandas as pd
import random
from config import DAYS, ROWS_ROSTER, WEIGHTS

def generate_roster(students_df, leave_students, special_closures, seed):
    """核心公平排班演算法 - 最完整版本"""
    random.seed(seed)
    roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    leave_set = set(str(name).strip() for name in leave_students if str(name).strip())

    student_info = {}
    for _, row in students_df.iterrows():
        name = str(row["name"]).strip()
        if not name or name in leave_set:
            continue
        student_info[name] = {
            "form": str(row.get("form", "")),
            "role": str(row.get("role", "Study Prefect")),
            "fixed": str(row.get("fixed_general_duty", "NONE")).upper(),
            "available": [d.strip().upper() for d in str(row.get("available", "")).split(",") if d.strip()],
            "history_weight": float(row.get("history_weight", 0.0))
        }

    last_duty_day = {name: -1 for name in student_info.keys()}

    for day_idx, day in enumerate(DAYS):
        for role in ROWS_ROSTER:
            if any(f"{day} - {role}" in sc for sc in special_closures):
                roster.at[role, day] = "X"
                continue

            if "Room202" in role and day in ["TUESDAY", "FRIDAY"]:
                roster.at[role, day] = "X"
                continue

            assigned = False
            for name, info in student_info.items():
                if info["fixed"] == day and name not in leave_set:
                    roster.at[role, day] = name
                    last_duty_day[name] = day_idx
                    assigned = True
                    break

            if assigned:
                continue

            candidates = []
            for name, info in student_info.items():
                if name in leave_set:
                    continue
                if day not in info["available"]:
                    continue
                if last_duty_day.get(name, -1) == day_idx - 1:
                    continue

                is_junior = info["form"] == "F.3"
                score = info["history_weight"] + random.uniform(0, 0.3)

                if "Assist" in role and info["role"] == "Assistant Head Study Prefect":
                    score -= 5.0

                candidates.append((score, name, is_junior))

            if not candidates:
                roster.at[role, day] = ""
                continue

            candidates.sort(key=lambda x: (x[0], -x[2]))
            chosen = candidates[0][1]

            roster.at[role, day] = chosen
            last_duty_day[chosen] = day_idx

    return roster


def validate_and_compute(roster_df, students_df, leave_students, manual_weights):
    """完整驗證 + 計算累計負荷"""
    errors = {
        "typo": (False, []),
        "duplicate": (False, []),
        "leave_conflict": (False, []),
        "vacuum": (False, [])
    }

    valid_names = set(str(row["name"]).strip() for _, row in students_df.iterrows() if str(row["name"]).strip())

    for day in DAYS:
        for role in ROWS_ROSTER:
            person = str(roster_df.at[role, day]).strip()
            if person and person != "X" and person not in valid_names:
                errors["typo"][1].append(f"{day} - {role}: {person}（姓名不在名冊中）")
                errors["typo"] = (True, errors["typo"][1])

    assigned = {}
    for day in DAYS:
        for role in ROWS_ROSTER:
            person = str(roster_df.at[role, day]).strip()
            if person and person != "X":
                if person in assigned:
                    errors["duplicate"][1].append(f"{person} 同時出現在 {assigned[person]} 和 {day}-{role}")
                    errors["duplicate"] = (True, errors["duplicate"][1])
                else:
                    assigned[person] = f"{day}-{role}"

    leave_set = set(str(name).strip() for name in leave_students if str(name).strip())
    for day in DAYS:
        for role in ROWS_ROSTER:
            person = str(roster_df.at[role, day]).strip()
            if person in leave_set:
                errors["leave_conflict"][1].append(f"{day} - {role}: {person} 已請假但仍排班")
                errors["leave_conflict"] = (True, errors["leave_conflict"][1])

    for day in DAYS:
        for role in ROWS_ROSTER:
            if str(roster_df.at[role, day]).strip() == "":
                if not (role == "Room202" and day in ["TUESDAY", "FRIDAY"]):
                    errors["vacuum"][1].append(f"{day} - {role} 尚未排班")
                    errors["vacuum"] = (True, errors["vacuum"][1])

    report = []
    for _, row in students_df.iterrows():
        name = str(row["name"]).strip()
        if not name:
            continue

        total_weight = float(row.get("history_weight", 0.0))
        this_week = 0.0

        for day in DAYS:
            for role in ROWS_ROSTER:
                if str(roster_df.at[role, day]).strip() == name:
                    added = float(manual_weights.at[role, day])
                    total_weight += added
                    this_week += added

        report.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": row.get("form", ""),
            "班別 (Class)": row.get("class", ""),
            "職級 (Role)": row.get("role", ""),
            "當週新增 (次)": round(this_week, 1),
            "最終總計加權負荷 (點)": round(total_weight, 1)
        })

    report_df = pd.DataFrame(report)
    if not report_df.empty:
        report_df = report_df.sort_values(by="最終總計加權負荷 (點)", ascending=True)

    return {
        "report_df": report_df,
        "typo": errors["typo"],
        "duplicate": errors["duplicate"],
        "leave_conflict": errors["leave_conflict"],
        "vacuum": errors["vacuum"]
    }


def recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    """智慧替補推薦"""
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if not current_person or current_person == "X":
        return None, "該時段目前無人值班"

    subs = []
    for _, rec in students_df.iterrows():
        name = str(rec["name"]).strip()
        if not name or name == current_person:
            continue
        if chosen_day not in str(rec.get("available", "")).upper():
            continue
        if rec.get("role") == "Assistant Head Study Prefect" and "Assist" not in chosen_role:
            continue

        subs.append({
            "姓名": name,
            "年級": rec.get("form", ""),
            "當前總點數": float(rec.get("history_weight", 0.0))
        })

    if not subs:
        return None, "找不到合適替補人員"

    sub_df = pd.DataFrame(subs).sort_values(by="當前總點數")
    return sub_df, None