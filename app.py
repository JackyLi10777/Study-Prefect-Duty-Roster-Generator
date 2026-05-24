import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
import datetime
import io
import json

# ==========================================
# 0. PDF 支援與環境強固檢查
# ==========================================
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False

# ==========================================
# 1. 網頁基礎設定與奢華藍金 UI
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
    .main-subtitle { color: #D4AF37; font-size: 15px; font-weight: 600; margin-bottom: 25px; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { height: 3.2rem; font-weight: bold; border-radius: 10px; width: 100% !important; transition: all 0.3s; }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; }
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; color: #92400E; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; }
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
# 3. Session State 安全初始化
# ==========================================
if 'students_df' not in st.session_state or st.session_state.students_df is None:
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
# 4. 數據同步回調
# ==========================================
def sync_students_data():
    if "student_editor_widget" in st.session_state and st.session_state.student_editor_widget:
        st.session_state.students_df = pd.DataFrame(st.session_state.student_editor_widget.get("current_rows", st.session_state.students_df))

def sync_roster_data():
    if "main_roster_editor_widget" in st.session_state and st.session_state.main_roster_editor_widget:
        st.session_state.roster_df = pd.DataFrame(st.session_state.main_roster_editor_widget.get("current_rows", st.session_state.roster_df))

# ==========================================
# 5. 名冊導入引擎
# ==========================================
def process_roster_import(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        mapping = {
            '姓名': 'name', 'name': 'name', 'Prefect Name': 'name', '學生姓名': 'name',
            '年級': 'form', 'form': 'form', 'Form': 'form',
            '班別': 'class', 'class': 'class', 'Class': 'class',
            '職級': 'role', 'role': 'role', 'Role': 'role',
            '學年固定總值班': 'fixed_general_duty', 'fixed_general_duty': 'fixed_general_duty',
            '可用日子': 'available', 'available': 'available',
            '歷史累計(次)': 'history_duties', 'history_duties': 'history_duties',
            '歷史累計(點)': 'history_weight', 'history_weight': 'history_weight',
            '備註': 'remarks', 'remarks': 'remarks'
        }
        df = df.rename(columns=lambda x: mapping.get(str(x).strip(), str(x).strip()))
        required = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required:
            if col not in df.columns:
                df[col] = "" if col not in ["history_duties", "history_weight"] else (0 if col == "history_duties" else 0.0)
        df = df[required]
        df["name"] = df["name"].astype(str).str.strip()
        df = df[df["name"] != ""]
        st.session_state.students_df = df
        st.sidebar.success(f"✅ 成功導入 {len(df)} 位領袖生！")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 導入失敗: {str(e)}")

# ==========================================
# 6. 備份 / 還原
# ==========================================
def export_system_backup():
    audit = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, st.session_state.leave_tracker_input)
    backup_data = {
        "master_report": audit["report_df"].to_dict(orient="records"),
        "roster_table": st.session_state.roster_df.to_dict(orient="index"),
        "leave_tracker": st.session_state.leave_tracker_input
    }
    return json.dumps(backup_data, ensure_ascii=False, indent=2)

def import_system_backup(uploaded_json_file):
    try:
        data = json.load(uploaded_json_file)
        raw_master = pd.DataFrame(data.get("master_report", []))
        mapping_reverse = {
            "學生姓名 (Prefect Name)": "name", "年級 (Form)": "form", "班別 (Class)": "class",
            "職級 (Role)": "role", "學年固定總值班": "fixed_general_duty",
            "最終總計值班次數 (次)": "history_duties", "最終總計加權負荷 (點)": "history_weight",
            "備註": "remarks"
        }
        renamed = raw_master.rename(columns=mapping_reverse)
        required = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required:
            if col not in renamed.columns:
                renamed[col] = "" if col not in ["history_duties", "history_weight"] else (0 if col == "history_duties" else 0.0)
        st.session_state.students_df = renamed[required]
        restored = pd.DataFrame.from_dict(data.get("roster_table", {}), orient="index")
        st.session_state.roster_df = restored.reindex(index=ROWS_ROSTER, columns=DAYS).fillna("")
        st.session_state.leave_tracker_input = data.get("leave_tracker", [])
        st.success("✅ 備份已完美還原！")
        st.rerun()
    except Exception as e:
        st.error(f"還原失敗: {str(e)}")

# ==========================================
# 7. 核心排班演算法（完整無省略）
# ==========================================
def generate_roster(students_df: pd.DataFrame, leave_students: list, special_closures: list, seed: int) -> pd.DataFrame:
    if students_df.empty or students_df['name'].str.strip().eq('').all():
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
    # 學生快取
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
# 8. 驗證與統計（永遠回傳 dict）
# ==========================================
def validate_and_compute(roster_df: pd.DataFrame, students_df: pd.DataFrame, leave_students: list):
    if students_df.empty or "name" not in students_df.columns:
        return {
            "typo": (False, []), "vacuum": (False, []), "duplicate": (False, []), "leave_conflict": (False, []),
            "report_df": pd.DataFrame()
        }
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

# ==========================================
# 9. 智慧替補推薦
# ==========================================
def recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if current_person in ["", "X"]:
        return None, "該時段無需替補"
    audit = validate_and_compute(roster_df, students_df, [])
    master_df = audit["report_df"]
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
        if chosen_day not in str(rec.get("可用日子 (Available Days)", "")).upper():
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
# 10. PDF 生成（已完美修復中文方格問題）
# ==========================================
def generate_pdf(roster_df, master_report_df, logo_b64=None):
    today = datetime.date.today().strftime("%Y-%m-%d")
    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 20mm; }}
        body {{ 
            font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", "Arial Unicode MS", sans-serif; 
            font-size: 11pt; 
            line-height: 1.5; 
        }}
        h1 {{color:#0C2340; text-align:center; font-size: 28px;}}
        h2 {{color:#D4AF37; font-size: 18px;}}
        table {{width:100%; border-collapse:collapse; margin:20px 0;}}
        th, td {{border:1px solid #aaa; padding:8px; text-align:center;}}
        th {{background:#0C2340; color:white;}}
        .assist {{background:#FFF8E1;}} 
        .room302 {{background:#D1FAE5;}}
        .room303 {{background:#FEE2E2;}} 
        .room202 {{background:#FEF3C7;}}
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
# 11. 側邊欄
# ==========================================
with st.sidebar:
    st.header("🏫 Sing Yin Secondary School")
    uploaded_logo = st.file_uploader("上傳校徽 (PNG)", type=["png"])
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()
    st.write("---")
    st.header("🗄️ 數據導入")
    uploaded_roster = st.file_uploader("選取名冊 (Excel/CSV)", type=["csv", "xlsx", "xls"])
    if uploaded_roster and st.button("確認導入", use_container_width=True):
        process_roster_import(uploaded_roster)
    if st.button("💡 一鍵載入 Sing Yin 示範數據", use_container_width=True):
        demo_data = [
            {"name": "陳卓軒", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "fixed_general_duty": "MONDAY", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 12, "history_weight": 12.0, "remarks": "隊長"},
            {"name": "李浩然", "form": "F.5", "class": "5B", "role": "Assistant Head Study Prefect", "fixed_general_duty": "WEDNESDAY", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 10, "history_weight": 10.0, "remarks": ""},
            {"name": "張凱傑", "form": "F.4", "class": "4A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 9, "history_weight": 13.5, "remarks": ""},
            {"name": "黃子軒", "form": "F.4", "class": "4B", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "TUESDAY,WEDNESDAY,FRIDAY", "history_duties": 8, "history_weight": 12.0, "remarks": ""},
            {"name": "林俊傑", "form": "F.3", "class": "3A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,THURSDAY", "history_duties": 6, "history_weight": 9.0, "remarks": ""},
            {"name": "王偉倫", "form": "F.5", "class": "5C", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,FRIDAY", "history_duties": 7, "history_weight": 10.5, "remarks": ""},
            {"name": "劉家豪", "form": "F.4", "class": "4C", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "TUESDAY,THURSDAY", "history_duties": 5, "history_weight": 7.5, "remarks": ""},
        ]
        st.session_state.students_df = pd.DataFrame(demo_data)
        st.success("✅ 示範數據已載入")
        st.rerun()
    st.write("---")
    st.header("👥 在線名冊編輯")
    edited_df = st.data_editor(
        st.session_state.students_df,
        column_config={
            "name": st.column_config.TextColumn("姓名 *", required=True),
            "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5"]),
            "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"]),
            "fixed_general_duty": st.column_config.SelectboxColumn("固定總值班", options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]),
            "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
            "history_duties": st.column_config.NumberColumn("歷史累計(次)", disabled=True),
            "history_weight": st.column_config.NumberColumn("歷史累計(點)", disabled=True),
        },
        num_rows="dynamic", use_container_width=True, hide_index=True,
        key="student_editor_widget", on_change=sync_students_data
    )
    st.session_state.students_df = edited_df
    st.write("---")
    st.header("🛑 突發請假名單")
    valid_names_list = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    leave_students = st.multiselect("全天請假同學", options=valid_names_list, default=st.session_state.leave_tracker_input, key="leave_tracker_input")
    st.write("---")
    st.header("💾 Cloud 備份系統")
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
# 主畫面
# ==========================================
st.markdown('<p class="main-title">🦅 SING YIN STUDY PREFECT ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | v15.2 終極完整版</p>', unsafe_allow_html=True)

closure_options = [f"{d} - {room}" for d in DAYS for room in ["Room302", "Room303", "Room202"] if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"])]
selected_closures = st.multiselect("🛠️ 設定本週特殊不開放時段", options=closure_options)

col1, col2, col3 = st.columns([2, 1.5, 1.5])
with col1:
    if st.button("🚀 生成本週全新值班表", type="primary", use_container_width=True):
        with st.spinner("智慧排班計算中..."):
            seed = random.randint(10000, 99999)
            st.session_state.roster_df = generate_roster(st.session_state.students_df, leave_students, selected_closures, seed)
            st.success(f"✅ 排班完成！種子碼: {seed}")

with col2:
    if st.button("🗑️ 一鍵清空本週排班", type="secondary", use_container_width=True):
        st.session_state.show_clear_confirm = True

if st.session_state.show_clear_confirm:
    st.markdown('<div class="warning-alert"><b>⚠️ 確定要清除全部排班？此操作無法復原！</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("確定清空", type="primary"):
        st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
        st.session_state.show_clear_confirm = False
        st.rerun()
    if c2.button("取消"):
        st.session_state.show_clear_confirm = False
        st.rerun()

with col3:
    if st.button("📄 匯出 PDF 列印版", type="primary", use_container_width=True):
        audit = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
        if audit["typo"][0]:
            st.error("請先修正姓名錯誤")
        elif PDF_AVAILABLE:
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.logo_data else None
            pdf_bytes = generate_pdf(st.session_state.roster_df, audit["report_df"], logo_b64)
            st.download_button("💾 下載 PDF", pdf_bytes, f"SYSS_Roster_{datetime.date.today()}.pdf", "application/pdf", use_container_width=True)
        else:
            st.info("💡 PDF 功能需 weasyprint 支援")

# ==========================================
# 驗證、Tabs、替補、圖表
# ==========================================
audit = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
typo_detected, invalid_entries = audit["typo"]
vacuum_detected, vacuum_entries = audit["vacuum"]
duplicate_detected, duplicate_entries = audit["duplicate"]
leave_conflict_detected, leave_conflict_entries = audit["leave_conflict"]
master_report_df = audit["report_df"]

if typo_detected:
    st.markdown(f'<div class="danger-alert"><b>⚠️ 偵測到無效姓名：</b><br>' + '<br>'.join(invalid_entries) + '</div>', unsafe_allow_html=True)
elif vacuum_detected:
    st.markdown(f'<div class="warning-alert"><b>💡 存在未排班的開放時段：</b><br>' + '<br>'.join(vacuum_entries) + '</div>', unsafe_allow_html=True)

if duplicate_detected:
    st.markdown(f'<div class="danger-alert"><b>⚠️ 重複分配警告：</b><br>' + '<br>'.join(duplicate_entries) + '</div>', unsafe_allow_html=True)

if leave_conflict_detected:
    st.markdown(f'<div class="danger-alert"><b>🛑 請假衝突：</b><br>' + '<br>'.join(leave_conflict_entries) + '</div>', unsafe_allow_html=True)
    if st.button("🩹 一鍵清除請假人員", type="primary"):
        for d in DAYS:
            for r in ROWS_ROSTER:
                if str(st.session_state.roster_df.at[r, d]).strip() in leave_students:
                    st.session_state.roster_df.at[r, d] = ""
        st.success("✅ 已清除請假人員")
        st.rerun()

tab_edit, tab_view = st.tabs(["✏️ 互動微調模式", "🎨 彩色列印預覽"])
with tab_edit:
    updated_df = st.data_editor(st.session_state.roster_df, use_container_width=True, height=320, key="main_roster_editor_widget", on_change=sync_roster_data)
    st.session_state.roster_df = updated_df
with tab_view:
    styled = st.session_state.roster_df.style.apply(lambda col: ["color: #EF4444; font-weight: bold;" if v == "X" else "" for v in col], axis=0)
    st.dataframe(styled, use_container_width=True, height=320)

# 智慧替補
st.write("---")
st.subheader("🔄 突發請假？智慧替補推薦系統")
c1, c2 = st.columns(2)
with c1:
    chosen_day = st.selectbox("請假日期", DAYS)
with c2:
    chosen_role = st.selectbox("請假崗位", ROWS_ROSTER)
current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
st.text_input("目前該時段人員", value=current_person if current_person not in ["", "X"] else "（無人）", disabled=True)
if st.button("🔍 尋找最優替補", type="primary"):
    sub_df, msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
    if sub_df is not None:
        st.success("📋 推薦替補名單（按總負荷由低到高排序）")
        st.dataframe(sub_df, use_container_width=True, hide_index=True)
    else:
        st.warning(msg)

# 公平性圖表
if not master_report_df.empty:
    st.write("---")
    st.subheader("📊 全體工作量公平性監控")
    fig = px.bar(master_report_df, x='學生姓名 (Prefect Name)', y='最終總計加權負荷 (點)', text_auto='.1f', color_continuous_scale='YlOrBr')
    st.plotly_chart(fig, use_container_width=True)

st.caption("Sing Yin Secondary School Study Prefect Platform | v15.2 終極完整穩定版（PDF 中文已完美修正）")
