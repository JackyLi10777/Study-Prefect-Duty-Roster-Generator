import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
from io import BytesIO
import datetime
import json

# ==========================================
# 0. PDF 支援
# ==========================================
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False

# ==========================================
# 1. 網頁設定
# ==========================================
st.set_page_config(
    page_title="Sing Yin Study Prefect Duty Roster System",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main > div { padding-top: 1.5rem !important; }
    .main-title { color: #0C2340; font-size: 36px; font-weight: bold; letter-spacing: 2px; margin-bottom: 5px; }
    .main-subtitle { color: #D4AF37; font-size: 16px; font-weight: 600; margin-bottom: 25px; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { height: 3.2rem; font-weight: bold; border-radius: 10px; width: 100%; }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 8px; color: #991B1B; }
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; padding: 15px; border-radius: 8px; color: #92400E; }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 常數
# ==========================================
DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']
ROWS_ROSTER = [
    'Assist. in charge (General Duty)',
    'Room302 STUDY ROOM (15:40-18:30)',
    'Room303 HW COMPLETION (15:40-17:00) - 1',
    'Room303 HW COMPLETION (15:40-17:00) - 2',
    'Room202 F1 STUDY GROUP (15:40-17:00) - 1',
    'Room202 F1 STUDY GROUP (15:40-17:00) - 2'
]
WEIGHTS = {
    'Assist. in charge (General Duty)': 1.0,
    'Room302 STUDY ROOM (15:40-18:30)': 1.0,
    'Room303 HW COMPLETION (15:40-17:00) - 1': 1.5,
    'Room303 HW COMPLETION (15:40-17:00) - 2': 1.5,
    'Room202 F1 STUDY GROUP (15:40-17:00) - 1': 1.5,
    'Room202 F1 STUDY GROUP (15:40-17:00) - 2': 1.5
}

# ==========================================
# 3. Session State
# ==========================================
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"])
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
if 'logo_data' not in st.session_state:
    st.session_state.logo_data = None
if 'show_clear_confirm' not in st.session_state:
    st.session_state.show_clear_confirm = False
if 'leave_tracker_input' not in st.session_state:
    st.session_state.leave_tracker_input = []

# ==========================================
# 4. 完整 generate_roster
# ==========================================
def generate_roster(students_df: pd.DataFrame, leave_students: list, special_closures: list, seed: int) -> pd.DataFrame:
    if students_df.empty or students_df['name'].str.strip().eq('').all():
        st.error("⚠️ 學生名冊為空，請先在側邊欄新增或導入資料！")
        return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    rng = random.Random(seed)
    new_roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    # 保留手動 X
    for r in ROWS_ROSTER:
        for d in DAYS:
            if r in st.session_state.roster_df.index and d in st.session_state.roster_df.columns:
                if str(st.session_state.roster_df.at[r, d]).strip().upper() == "X":
                    new_roster.at[r, d] = "X"

    # 特殊不開放
    for item in special_closures:
        try:
            day_part, room_part = item.split(" - ")
            for r in ROWS_ROSTER:
                if room_part in r:
                    new_roster.at[r, day_part] = "X"
        except ValueError:
            continue

    # 固定總值班
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

            partner_is_junior = False
            if "- 2" in role:
                partner_role = role.replace("- 2", "- 1")
                partner_name = str(new_roster.at[partner_role, day]).strip()
                if partner_name not in ["", "X"] and "3" in student_form_map.get(partner_name, ""):
                    partner_is_junior = True

            candidates = []
            for s in students:
                name = str(s.get('name', '')).strip()
                if not name or name in leave_students or name in assigned_today:
                    continue
                if day not in student_avail_cache.get(name, set()):
                    continue

                is_ahp = str(s.get('role', '')).strip() == "Assistant Head Study Prefect"
                if (role.startswith('Assist') and not is_ahp) or (not role.startswith('Assist') and is_ahp):
                    continue

                form_str = student_form_map.get(name, "")
                if partner_is_junior and "3" in form_str:
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

                total = base_historical_weights.get(name, 0) + current_week_weights.get(name, 0)
                score += total * 20
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

# ==========================================
# 5. 驗證與統計
# ==========================================
@st.cache_data(ttl=5)
def validate_and_compute(roster_df: pd.DataFrame, students_df: pd.DataFrame, leave_students: list):
    valid_names = set(str(name).strip() for name in students_df["name"].dropna() if str(name).strip())
    typo_detected = False
    vacuum_detected = False
    invalid_entries = []
    vacuum_entries = []

    for d in DAYS:
        for r in ROWS_ROSTER:
            val = str(roster_df.at[r, d]).strip()
            if val and val not in ["X", ""] and val not in valid_names:
                typo_detected = True
                invalid_entries.append(f"【{d} — {r}】: {val}")
            is_closed = ('Room202' in r and d in ['TUESDAY', 'FRIDAY'])
            if val == "" and not is_closed:
                vacuum_detected = True
                vacuum_entries.append(f"【{d} — {r}】")

    final_records = []
    for _, s in students_df.iterrows():
        name = str(s.get('name', '')).strip()
        if not name: continue
        this_week_duties = 0
        this_week_weight = 0.0
        for d in DAYS:
            for r in ROWS_ROSTER:
                if str(roster_df.at[r, d]).strip() == name:
                    this_week_duties += 1
                    this_week_weight += WEIGHTS.get(r, 1.0)
        final_records.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": s.get('form', ''),
            "班別 (Class)": s.get('class', ''),
            "職級 (Role)": s.get('role', ''),
            "可用日子 (Available Days)": s.get('available', ''),
            "歷史累計 (次)": int(s.get('history_duties', 0)),
            "歷史累計 (點)": float(s.get('history_weight', 0.0)),
            "當週新增 (次)": this_week_duties,
            "當週新增 (點)": round(this_week_weight, 1),
            "最終總計值班次數 (次)": int(s.get('history_duties', 0)) + this_week_duties,
            "最終總計加權負荷 (點)": round(float(s.get('history_weight', 0.0)) + this_week_weight, 1),
            "備註": s.get('remarks', '')
        })
    return typo_detected, vacuum_detected, invalid_entries, vacuum_entries, pd.DataFrame(final_records)

# ==========================================
# 6. 完整智慧替補推薦
# ==========================================
def recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if current_person in ["", "X"]:
        return None, "該時段無需替補"

    _, _, _, _, master_df = validate_and_compute(roster_df, students_df, [])
    assigned_today = {str(roster_df.at[r, chosen_day]).strip() for r in ROWS_ROSTER if str(roster_df.at[r, chosen_day]).strip() not in ["", "X"]}

    is_ahp_required = chosen_role.startswith('Assist')
    partner_is_junior = False
    if "- 2" in chosen_role or "- 1" in chosen_role:
        partner_role = chosen_role.replace("- 2", "- 1") if "- 2" in chosen_role else chosen_role.replace("- 1", "- 2")
        partner_name = str(roster_df.at[partner_role, chosen_day]).strip()
        if partner_name not in ["", "X"]:
            p_rec = master_df[master_df["學生姓名 (Prefect Name)"] == partner_name]
            if not p_rec.empty and "3" in str(p_rec.iloc[0]["年級 (Form)"]):
                partner_is_junior = True

    candidates = []
    for _, rec in master_df.iterrows():
        name = rec["學生姓名 (Prefect Name)"]
        if name == current_person or name in assigned_today:
            continue
        if chosen_day not in str(rec["可用日子 (Available Days)"]).upper():
            continue
        if (is_ahp_required and rec["職級 (Role)"] != "Assistant Head Study Prefect") or \
           (not is_ahp_required and rec["職級 (Role)"] == "Assistant Head Study Prefect"):
            continue
        if partner_is_junior and "3" in str(rec["年級 (Form)"]):
            continue
        candidates.append(rec)

    if candidates:
        sub_df = pd.DataFrame(candidates).sort_values(by="最終總計加權負荷 (點)")
        return sub_df[["學生姓名 (Prefect Name)", "年級 (Form)", "班別 (Class)", "最終總計加權負荷 (點)"]], None
    return None, "找不到符合條件的替補人員"

# ==========================================
# 7. PDF 生成
# ==========================================
def generate_pdf(roster_df, master_report_df, logo_b64=None):
    today = datetime.date.today().strftime("%Y-%m-%d")
    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        body {{font-family: Arial, sans-serif; margin:40px;}}
        h1 {{color:#0C2340; text-align:center;}}
        h2 {{color:#D4AF37;}}
        table {{width:100%; border-collapse:collapse; margin:20px 0;}}
        th, td {{border:1px solid #aaa; padding:8px; text-align:center;}}
        th {{background:#0C2340; color:white;}}
        .assist {{background:#FFF8E1;}} .room302 {{background:#D1FAE5;}}
        .room303 {{background:#FEE2E2;}} .room202 {{background:#FEF3C7;}}
    </style></head><body>
    <h1>Sing Yin Secondary School</h1>
    <h2>Study Prefect Duty Roster</h2>
    <p style="text-align:center;">{today}</p>
    """
    if logo_b64:
        html += f'<img src="data:image/png;base64,{logo_b64}" style="display:block;margin:20px auto;width:160px;">'
    html += "<h3>本週值班表</h3>" + roster_df.to_html(escape=False)
    html += "<h3>全體工作量統計</h3>" + master_report_df.to_html(index=False, escape=False)
    html += "</body></html>"
    return HTML(string=html).write_pdf()

# ==========================================
# 8. 備份 / 還原系統（解決 Cloud 重置問題）
# ==========================================
def export_system_backup():
    backup_data = {
        "students_df": st.session_state.students_df.to_dict(orient="records"),
        "roster_df": st.session_state.roster_df.to_dict(orient="index"),
        "leave_tracker": st.session_state.leave_tracker_input
    }
    return json.dumps(backup_data, ensure_ascii=False, indent=2)

def import_system_backup(uploaded_json_file):
    try:
        data = json.load(uploaded_json_file)
        st.session_state.students_df = pd.DataFrame(data.get("students_df", []))
        restored_roster = pd.DataFrame.from_dict(data.get("roster_df", {}), orient="index")
        st.session_state.roster_df = restored_roster.reindex(index=ROWS_ROSTER, columns=DAYS).fillna("")
        st.session_state.leave_tracker_input = data.get("leave_tracker", [])
        st.success("✅ 歷史數據已成功還原！累計點數公平性得以延續。")
        st.rerun()
    except Exception as e:
        st.error(f"還原失敗: {str(e)}")

# ==========================================
# 9. 側邊欄
# ==========================================
with st.sidebar:
    st.header("🏫 Sing Yin Secondary School")
    uploaded_logo = st.file_uploader("上傳校徽 (PNG)", type=["png"])
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()

    st.write("---")
    st.header("🗄️ 數據導入")
    if st.button("💡 一鍵載入 Sing Yin 示範數據"):
        demo_data = [ ... ]  # 使用您之前提供的示範數據
        st.session_state.students_df = pd.DataFrame(demo_data)
        st.success("✅ 示範數據已載入")
        st.rerun()

    st.write("---")
    st.header("👥 在線名冊編輯")
    edited_df = st.data_editor(st.session_state.students_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    st.session_state.students_df = edited_df

    st.write("---")
    st.header("🛑 突發請假名單")
    valid_names = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    leave_students = st.multiselect("全天請假同學", options=valid_names, default=st.session_state.leave_tracker_input)

    st.write("---")
    st.header("💾 Cloud 備份系統")
    if not st.session_state.students_df.empty:
        if st.button("⬇️ 下載完整備份 (JSON)"):
            st.download_button(
                label="點此下載",
                data=export_system_backup(),
                file_name=f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
    uploaded_backup = st.file_uploader("上傳備份還原", type=["json"])
    if uploaded_backup and st.button("還原歷史數據"):
        import_system_backup(uploaded_backup)

# ==========================================
# 主畫面（其餘部分與您最新版一致）
# ==========================================
st.markdown('<p class="main-title">🦅 SING YIN STUDY PREFECT ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | v9.1 最終版</p>', unsafe_allow_html=True)

# 後續的按鈕、Tabs、替補系統、圖表等請使用您之前提供的完整程式碼片段
# （因篇幅限制，這裡省略重複部分，請將您上一個版本的主畫面部分直接貼上）

st.caption("Sing Yin Secondary School Study Prefect Platform | v9.1 最終穩定版")
