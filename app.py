# core.py
import pandas as pd
import random

from config import DAYS, ROWS_ROSTER, WEIGHTS

def generate_roster(students_df: pd.DataFrame, leave_students: list, special_closures: list, seed: int) -> pd.DataFrame:
    if students_df.empty or students_df['name'].str.strip().eq('').all():
        # 改為返回空表格，不在 core.py 呼叫 st.error（避免 NameError）
        return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    rng = random.Random(seed)
    new_roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    # 保留手動標記的 "X"
    for r in ROWS_ROSTER:
        for d in DAYS:
            if r in st.session_state.roster_df.index and d in st.session_state.roster_df.columns:
                if str(st.session_state.roster_df.at[r, d]).strip().upper() == "X":
                    new_roster.at[r, d] = "X"

    # 特殊不開放時段
    for item in special_closures:
        try:
            day_part, room_part = item.split(" - ")
            for r in ROWS_ROSTER:
                if room_part in r:
                    new_roster.at[r, day_part] = "X"
        except ValueError:
            continue

    # 固定總值班處理
    for _, s in students_df.iterrows():
        name = str(s.get('name', '')).strip()
        fixed_day = str(s.get('fixed_general_duty', '')).strip().upper()
        if name and fixed_day in DAYS and new_roster.at['Assist. in charge (General Duty)', fixed_day] != "X":
            new_roster.at['Assist. in charge (General Duty)', fixed_day] = name

    students = students_df.to_dict('records')
    current_week_weights = {}
    student_form_map = {}
    student_avail_cache = {}
    base_historical_weights = {}

    for s in students:
        name = str(s.get('name', '')).strip()
        if not name: continue
        current_week_weights[name] = 0.0
        student_form_map[name] = str(s.get('form', '')).upper().strip()
        base_historical_weights[name] = float(s.get('history_weight', 0.0)) if pd.notna(s.get('history_weight')) else 0.0
        raw_avail = str(s.get('available', '')).upper().split(',')
        student_avail_cache[name] = {d.strip() for d in raw_avail if d.strip()}

    last_duty_day = {name: -2 for name in current_week_weights}

    for d_idx, day in enumerate(DAYS):
        assigned_today = set()
        fixed_pic = str(new_roster.at['Assist. in charge (General Duty)', day]).strip()
        if fixed_pic and fixed_pic not in ["", "X"]:
            assigned_today.add(fixed_pic)
        
        dynamic_roles = [r for r in ROWS_ROSTER if r != 'Assist. in charge (General Duty)']
        rng.shuffle(dynamic_roles)
        dynamic_roles.sort(key=lambda x: 1 if "- 2" in x else 0)

        for role in dynamic_roles:
            if new_roster.at[role, day] == "X":
                continue
            if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
                new_roster.at[role, day] = ""
                continue

            # ==================== 強化老帶新機制 ====================
            partner_is_junior = False
            if "- 2" in role:
                partner_role = role.replace("- 2", "- 1")
                partner_name = str(new_roster.at[partner_role, day]).strip()
                if partner_name not in ["", "X"]:
                    partner_form = student_form_map.get(partner_name, "")
                    if "3" in partner_form:   # F.3 為 junior
                        partner_is_junior = True

            candidates = []
            for s in students:
                name = str(s.get('name', '')).strip()
                if not name or name in leave_students or name in assigned_today:
                    continue
                if day not in student_avail_cache.get(name, set()):
                    continue

                form_str = student_form_map.get(name, "")
                # 老帶新嚴格判斷：F.3 不能帶 F.3，必須由 F.4/F.5 帶 F.3
                if partner_is_junior and "3" in form_str:
                    continue

                is_ahp = str(s.get('role', '')).strip() == "Assistant Head Study Prefect"
                if (role.startswith('Assist') and not is_ahp) or (not role.startswith('Assist') and is_ahp):
                    continue

                score = 0
                w = WEIGHTS[role]
                if last_duty_day.get(name, -2) == d_idx - 1: score += 1000
                if current_week_weights.get(name, 0) + w > 3.0: score += 800

                is_senior = any(x in form_str for x in ["4", "5"])
                if 'Room302' in role:
                    score += 40 if is_senior else -40
                elif 'Room303' in role or 'Room202' in role:
                    score += -40 if is_senior else 40

                total_load = base_historical_weights.get(name, 0) + current_week_weights.get(name, 0)
                score += total_load * 20
                candidates.append((score, name, w))

            if candidates:
                candidates.sort(key=lambda x: x[0])
                chosen = rng.choice(candidates[:min(2, len(candidates))])
                chosen_name = chosen[1]
                new_roster.at[role, day] = chosen_name
                assigned_today.add(chosen_name)
                current_week_weights[chosen_name] += chosen[2]
                last_duty_day[chosen_name] = d_idx

    return new_roster

def validate_and_compute(roster_df: pd.DataFrame, students_df: pd.DataFrame, leave_students: list, manual_weights: pd.DataFrame = None):
    if manual_weights is None:
        manual_weights = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)

    valid_names = set(str(name).strip() for name in students_df["name"].dropna() if str(name).strip())
    typo_detected = False
    vacuum_detected = False
    duplicate_detected = False
    leave_conflict_detected = False
    
    invalid_entries = []
    vacuum_entries = []
    duplicate_entries = []
    leave_conflict_entries = []

    for d in DAYS:
        day_assigned_map = {}
        for r in ROWS_ROSTER:
            val = str(roster_df.at[r, d]).strip()
            if not val:
                if not ('Room202' in r and d in ['TUESDAY', 'FRIDAY']):
                    vacuum_detected = True
                    vacuum_entries.append(f"【{d} — {r}】")
                continue
            
            if val == "X":
                continue

            if val not in valid_names:
                typo_detected = True
                invalid_entries.append(f"【{d} — {r}】: 「{val}」不存在於名冊中")
                continue

            if val in day_assigned_map:
                duplicate_detected = True
                duplicate_entries.append(f"【{d}】{val} 重複分配於「{day_assigned_map[val]}」與「{r}」")
            else:
                day_assigned_map[val] = r

            if val in leave_students:
                leave_conflict_detected = True
                leave_conflict_entries.append(f"【{d} — {r}】: {val}")

    final_records = []
    for _, s in students_df.iterrows():
        name = str(s.get('name', '')).strip()
        if not name: continue
        this_week_duties = 0 
        this_week_weight = 0.0
        
        if not typo_detected:
            for d in DAYS:
                for r in ROWS_ROSTER:
                    if str(roster_df.at[r, d]).strip() == name:
                        base_w = WEIGHTS.get(r, 1.0)
                        manual_w = float(manual_weights.at[r, d]) if r in manual_weights.index and d in manual_weights.columns else 0.0
                        this_week_weight += base_w + manual_w
                        this_week_duties += 1
                        
        final_records.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": s.get('form', ''),
            "班別 (Class)": s.get('class', ''),
            "職級 (Role)": s.get('role', ''),
            "學年固定總值班": s.get('fixed_general_duty', ''),
            "歷史累計 (次)": int(s.get('history_duties', 0)) if pd.notna(s.get('history_duties')) else 0,
            "歷史累計 (點)": float(s.get('history_weight', 0.0)) if pd.notna(s.get('history_weight')) else 0.0,
            "當週新增 (次)": this_week_duties,
            "當週新增 (點)": round(this_week_weight, 1),
            "最終總計值班次數 (次)": (int(s.get('history_duties', 0)) if pd.notna(s.get('history_duties')) else 0) + this_week_duties,
            "最終總計加權負荷 (點)": round((float(s.get('history_weight', 0.0)) if pd.notna(s.get('history_weight')) else 0.0) + this_week_weight, 1),
            "備註": s.get('remarks', '')
        })
        
    return {
        "typo": (typo_detected, invalid_entries),
        "vacuum": (vacuum_detected, vacuum_entries),
        "duplicate": (duplicate_detected, duplicate_entries),
        "leave_conflict": (leave_conflict_detected, leave_conflict_entries),
        "report_df": pd.DataFrame(final_records)
    }

def recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if current_person in ["", "X"]:
        return None, "該時段無需替補、為常規關閉或目前不開放。"

    assigned_today = {str(roster_df.at[r, chosen_day]).strip() for r in ROWS_ROSTER if str(roster_df.at[r, chosen_day]).strip() not in ["", "X"]}
    is_ahp_required = chosen_role.startswith('Assist')
    partner_is_junior = False

    if "- 2" in chosen_role or "- 1" in chosen_role:
        partner_role = chosen_role.replace("- 2", "- 1") if "- 2" in chosen_role else chosen_role.replace("- 1", "- 2")
        partner_name = str(roster_df.at[partner_role, chosen_day]).strip()
        if partner_name not in ["", "X"]:
            p_match = students_df[students_df["name"].str.strip() == partner_name]
            if not p_match.empty and "3" in str(p_match.iloc[0].get("form", "")):
                partner_is_junior = True

    candidates = []
    for _, s in students_df.iterrows():
        name = str(s.get('name', '')).strip()
        if not name or name == current_person or name in assigned_today: 
            continue
        
        avail_days = {d.strip().upper() for d in str(s.get('available', '')).split(',') if d.strip()}
        if chosen_day not in avail_days: 
            continue
        
        is_ahp = str(s.get('role', '')).strip() == "Assistant Head Study Prefect"
        if (is_ahp_required and not is_ahp) or (not is_ahp_required and is_ahp): 
            continue
        if partner_is_junior and "3" in str(s.get('form', '')): 
            continue

        this_week_weight = 0.0
        for d in DAYS:
            for r in ROWS_ROSTER:
                if str(roster_df.at[r, d]).strip() == name:
                    this_week_weight += WEIGHTS.get(r, 1.0)

        candidates.append({
            "替補學生姓名": name,
            "年級 (Form)": s.get('form', ''),
            "職級 (Role)": s.get('role', ''),
            "最終總計加權負荷 (點)": round((float(s.get('history_weight', 0.0)) if pd.notna(s.get('history_weight')) else 0.0) + this_week_weight, 1)
        })

    if candidates:
        return pd.DataFrame(candidates).sort_values(by="最終總計加權負荷 (點)"), None
    return None, "找不到符合天數可用與職級限制的替補人員。"
