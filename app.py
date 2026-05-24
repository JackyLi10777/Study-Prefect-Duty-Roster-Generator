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
# 1. 網頁基礎設定與奢華聖言藍金視覺 UI 注入
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
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; box-shadow: 0 2px 8px rgba(239,68,68,0.1);}
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; color: #92400E; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; box-shadow: 0 2px 8px rgba(245,158,11,0.1);}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 學校行政常數與點數天平配置
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
# 3. Session State 狀態機安全初始化（防 KeyError）
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
# 4. 數據同步回調函數 (Callbacks)
# ==========================================
def sync_students_data():
    if "student_editor_widget" in st.session_state and st.session_state.student_editor_widget:
        st.session_state.students_df = pd.DataFrame(st.session_state.student_editor_widget.get("current_rows", st.session_state.students_df))

def sync_roster_data():
    if "main_roster_editor_widget" in st.session_state and st.session_state.main_roster_editor_widget:
        st.session_state.roster_df = pd.DataFrame(st.session_state.main_roster_editor_widget.get("current_rows", st.session_state.roster_df))

# ==========================================
# 5. 核心寬容型原始名冊導入引擎
# ==========================================
def process_roster_import(uploaded_file):
    try:
        filename = uploaded_file.name
        if filename.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        mapping = {
            '姓名': 'name', 'name': 'name', 'Prefect Name': 'name', '學生姓名': 'name',
            '年級': 'form', 'form': 'form', 'Form': 'form',
            '班別': 'class', 'class': 'class', 'Class': 'class',
            '職級': 'role', 'role': 'role', 'Role': 'role',
            '學年固定總值班': 'fixed_general_duty', 'fixed_general_duty': 'fixed_general_duty', '固定值班': 'fixed_general_duty',
            '可用日子': 'available', 'available': 'available', '可用天數': 'available',
            '歷史累計(次)': 'history_duties', 'history_duties': 'history_duties', '歷史次數': 'history_duties',
            '歷史動態(點)': 'history_weight', 'history_weight': 'history_weight', '歷史點數': 'history_weight', '歷史累積': 'history_weight',
            '備註': 'remarks', 'remarks': 'remarks', 'Remark': 'remarks'
        }
        
        df = df.rename(columns=lambda x: mapping.get(str(x).strip(), str(x).strip()))
        
        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required_cols:
            if col not in df.columns:
                if col == "fixed_general_duty": df[col] = "NONE"
                elif col == "available": df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                elif col == "history_duties": df[col] = 0
                elif col == "history_weight": df[col] = 0.0
                else: df[col] = ""
        
        df = df[required_cols]
        df["name"] = df["name"].astype(str).str.strip()
        df = df[df["name"] != "nan"]
        df = df[df["name"] != ""]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors='coerce').fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors='coerce').fillna(0.0)
        
        st.session_state.students_df = df
        st.sidebar.success(f"🎉 成功導入 {len(df)} 位領袖生名冊！")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 導入失敗，格式不符。錯誤訊息: {str(e)}")

# ==========================================
# 5b. 數據備份導出與還原恢復引擎
# ==========================================
def export_system_backup(master_df):
    backup_data = {
        "master_report": master_df.to_dict(orient="records"),
        "roster_table": st.session_state.roster_df.to_dict(orient="index"),
        "leave_tracker": st.session_state.leave_tracker_input
    }
    return json.dumps(backup_data, ensure_ascii=False, indent=2)

def import_system_backup(uploaded_json_file):
    try:
        data = json.load(uploaded_json_file)
        if "master_report" in data and "roster_table" in data:
            raw_master = pd.DataFrame(data["master_report"])
            
            mapping_reverse = {
                "學生姓名 (Prefect Name)": "name",
                "年級 (Form)": "form",
                "班別 (Class)": "class",
                "職級 (Role)": "role",
                "學年固定總值班": "fixed_general_duty",
                "最終總計值班次數 (次)": "history_duties",
                "最終總計加權負荷 (點)": "history_weight",
                "備註": "remarks"
            }
            
            if "可用日子" not in raw_master.columns:
                raw_master["available"] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                
            renamed_df = raw_master.rename(columns=mapping_reverse)
            required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
            
            for col in required_cols:
                if col not in renamed_df.columns:
                    if col == "fixed_general_duty": renamed_df[col] = "NONE"
                    elif col == "history_duties": renamed_df[col] = 0
                    elif col == "history_weight": renamed_df[col] = 0.0
                    else: renamed_df[col] = ""
            
            st.session_state.students_df = renamed_df[required_cols]
            
            restored_roster = pd.DataFrame.from_dict(data["roster_table"], orient="index")
            st.session_state.roster_df = restored_roster.reindex(index=ROWS_ROSTER, columns=DAYS).fillna("")
            
            st.session_state.leave_tracker_input = data.get("leave_tracker", [])
            
            st.sidebar.success("🔮 備份數據已成功完美還原（已同步校準名冊與值班大表）！")
            st.rerun()
        else:
            st.sidebar.error("❌ 備份檔解析失敗：結構不符合 master_report 規範。")
    except Exception as e:
        st.sidebar.error(f"❌ 備份還原失敗，格式錯誤: {str(e)}")

# ==========================================
# 6. 核心排班演算法
# ==========================================
def generate_roster(students_df: pd.DataFrame, leave_students: list, special_closures: list, seed: int) -> pd.DataFrame:
    if students_df.empty or students_df['name'].str.strip().eq('').all():
        return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    rng = random.Random(seed)
    new_roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    for r in ROWS_ROSTER:
        for d in DAYS:
            if r in st.session_state.roster_df.index and d in st.session_state.roster_df.columns:
                if str(st.session_state.roster_df.at[r, d]).strip().upper() == "X":
                    new_roster.at[r, d] = "X"

    for item in special_closures:
        try:
            day_part, room_part = item.split(" - ")
            for r in ROWS_ROSTER:
                if room_part in r:
                    new_roster.at[r, day_part] = "X"
        except ValueError:
            continue

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
                
                form_str = student_form_map.get(name, "")
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
                if 'Room202' in role or 'Room303' in role:
                    score += -40 if is_senior else 40
                elif 'Room302' in role:
                    score += 40 if is_senior else -40

                total_load = base_historical_weights.get(name, 0) + current_week_weights.get(name, 0)
                score += total_load * 20
                candidates.append((score, name, w))

            if candidates:
                candidates.sort(key=lambda x: x)
                chosen = rng.choice(candidates[:min(2, len(candidates))])
                chosen_name = chosen[1]
                new_roster.at[role, day] = chosen_name
                assigned_today.add(chosen_name)
                current_week_weights[chosen_name] += chosen[2]
                last_duty_day[chosen_name] = d_idx

    return new_roster

# ==========================================
# 7. 全局數據審計與雙軌統計大表計算中心
# ==========================================
def validate_and_compute(roster_df: pd.DataFrame, students_df: pd.DataFrame, leave_students: list):
    # 防 KeyError 保護
    if students_df.empty or "name" not in students_df.columns:
        return False, False, [], [], False, [], False, [], pd.DataFrame()
    
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
                        this_week_weight += WEIGHTS.get(r, 1.0)
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

# ==========================================
# 8. 智慧替補推薦系統
# ==========================================
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

# ==========================================
# 9. A4 橫式高級 PDF 渲染引擎
# ==========================================
def generate_pdf(roster_df, master_report_df, logo_b64=None):
    today = datetime.date.today().strftime("%Y-%m-%d")
    html_table = roster_df.to_html(classes='table')
    report_table = master_report_df[["學生姓名 (Prefect Name)", "年級 (Form)", "班別 (Class)", "職級 (Role)", "當週新增 (次)", "最終總計加權負荷 (點)"]].to_html(index=False, classes='table')
    
    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 20mm; }}
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.4; }}
        .header-container {{ text-align: center; margin-bottom: 25px; }}
        h1 {{ color:#0C2340; font-size: 26px; margin: 5px 0; letter-spacing: 1px; }}
        h2 {{ color:#D4AF37; font-size: 16px; margin: 0 0 10px 0; font-weight: 600; text-transform: uppercase; }}
        .date-sub {{ font-size: 11px; color: #666; margin-bottom: 20px; }}
        h3 {{ color:#0C2340; border-left: 5px solid #D4AF37; padding-left: 10px; margin-top: 30px; font-size: 16px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 11px; }}
        th, td {{ border: 1px solid #D1D5DB; padding: 8px 10px; text-align: center; }}
        th {{ background-color: #0C2340; color: white; font-weight: bold; font-size: 10px; }}
        td {{ font-weight: bold; color: #1F2937; }}
        tr:nth-child(even) td {{ background-color: #F9FAFB; }}
    </style></head><body>
    <div class="header-container">
    """
    if logo_b64:
        html += f'<img src="data:image/png;base64,{logo_b64}" style="height:65px; margin-bottom:10px;">'
    html += f"""
        <h1>Sing Yin Secondary School</h1>
        <h2>Study Prefect Duty Roster & Workload Audit</h2>
        <div class="date-sub">Report Generated Date: {today}</div>
    </div>
    <h3>📅 本週值班表 (Weekly Duty Roster)</h3>
    {html_table}
    <div style="page-break-before: always;"></div>
    <h3>📊 累積動態工作負荷審計表 (Workload Audit Report)</h3>
    {report_table}
    </body></html>
    """
    return HTML(string=html).write_pdf()

# ==========================================
# 10. 側邊欄：大數據維護與「名冊/大表備份雙引導通道」
# ==========================================
with st.sidebar:
    st.markdown("### 🦅 校徽與行政系統")
    uploaded_logo = st.file_uploader("上傳校徽圖片 (PNG)", type=["png"], key="logo_uploader")
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()

    st.write("---")
    st.markdown("### 📥 導入 Prefect 原始名冊")
    uploaded_roster = st.file_uploader("選取常規名冊檔案 (Excel/CSV)：", type=["csv", "xlsx", "xls"], key="roster_importer")
    if uploaded_roster is not None:
        if st.button("確認解析並覆蓋導入", type="primary", use_container_width=True):
            process_roster_import(uploaded_roster)

    st.write("---")
    st.markdown("### 💾 數據備份與還原恢復 (對接大表)")
    
    audit_results_pre = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, st.session_state.leave_tracker_input)
    current_master_df = audit_results_pre["report_df"]
    
    if not current_master_df.empty:
        json_backup_string = export_system_backup(current_master_df)
        st.download_button(
            label="⬇️ 導出當前大表全狀態備份 (JSON)",
            data=json_backup_string,
            file_name=f"SYSS_Master_Roster_Backup_{datetime.date.today().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.button("⬇️ 導出備份 (請先載入名冊)", disabled=True, use_container_width=True)
    
    uploaded_backup = st.file_uploader("上傳大表結構備份數據 (JSON)：", type=["json"], key="backup_restorer")
    if uploaded_backup is not None:
        if st.button("確認從此備份還原系統", type="secondary", use_container_width=True):
            import_system_backup(uploaded_backup)

    st.write("---")
    st.markdown("### 🌟 快速測試通道")
    if st.button("💡 載入 Sing Yin 官方標準示範名冊", use_container_width=True):
        demo_data = [
            {"name": "陳卓軒", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "fixed_general_duty": "MONDAY", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 12, "history_weight": 12.0, "remarks": "固定週一總值班"},
            {"name": "李浩然", "form": "F.5", "class": "5B", "role": "Assistant Head Study Prefect", "fixed_general_duty": "WEDNESDAY", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 10, "history_weight": 10.0, "remarks": "固定週三總值班"},
            {"name": "張凱傑", "form": "F.4", "class": "4A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 9, "history_weight": 13.5, "remarks": ""},
            {"name": "黃子軒", "form": "F.4", "class": "4B", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "TUESDAY,WEDNESDAY,FRIDAY", "history_duties": 8, "history_weight": 12.0, "remarks": ""},
            {"name": "林俊傑", "form": "F.3", "class": "3A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,THURSDAY", "history_duties": 6, "history_weight": 9.0, "remarks": ""},
            {"name": "王偉倫", "form": "F.5", "class": "5C", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,FRIDAY", "history_duties": 7, "history_weight": 10.5, "remarks": ""},
            {"name": "劉家豪", "form": "F.4", "class": "4C", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "TUESDAY,THURSDAY", "history_duties": 5, "history_weight": 7.5, "remarks": ""},
        ]
        st.session_state.students_df = pd.DataFrame(demo_data)
        st.rerun()

    st.write("---")
    st.markdown("### 👥 在線名冊即時維護")
    st.data_editor(
        st.session_state.students_df,
        column_config={
            "name": st.column_config.TextColumn("姓名 *", required=True),
            "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5"]),
            "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"]),
            "fixed_general_duty": st.column_config.SelectboxColumn("學年固定總值班", options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"], default="NONE"),
            "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
            "history_duties": st.column_config.NumberColumn("歷史累計(次)", min_value=0, step=1),
            "history_weight": st.column_config.NumberColumn("歷史動態(點)", min_value=0.0, step=0.5),
            "remarks": st.column_config.TextColumn("備註")
        },
        num_rows="dynamic", use_container_width=True, hide_index=True, 
        key="student_editor_widget", on_change=sync_students_data
    )

    st.write("---")
    st.markdown("### 🛑 突發臨時請假登記")
    valid_names_list = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    
    leave_students = st.multiselect(
        "選取今日請假人員：", 
        options=valid_names_list, 
        key="leave_tracker_input"
    )

# ==========================================
# 11. 主畫面大數據控制中心
# ==========================================
st.markdown('<p class="main-title">🦅 SING YIN STUDY PREFECT ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Smart Scheduling Platform | v15.0 高階跨版本終極整合版</p>', unsafe_allow_html=True)

closure_options = [f"{d} - {room}" for d in DAYS for room in ["Room302", "Room303", "Room202"] if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"])]
selected_closures = st.multiselect("🛠️ 設定本週「特殊不開放」時段（或直接在下方表格內打 X 鎖定）：", options=closure_options, key="special_closures")

btn_col1, btn_col2, btn_col3 = st.columns([2, 1.5, 1.5])

with btn_col1:
    if st.button("🚀 智能計算：生成本週全新公平值班表", type="primary", use_container_width=True):
        with st.spinner("遵守常規不開放與計點規則計算中..."):
            seed = random.randint(10000, 99999)
            st.session_state.roster_df = generate_roster(st.session_state.students_df, leave_students, selected_closures, seed)
            st.success(f"🎉 排班計算成功！動態驗證碼: SY-{seed}")

with btn_col2:
    if st.button("🗑️ 一鍵清空當前排班表", type="secondary", use_container_width=True):
        st.session_state.show_clear_confirm = True

if st.session_state.show_clear_confirm:
    st.markdown('<div class="warning-alert"><b>⚠️ 確定要清除全部排班？此操作將會抹除目前畫面上所有的指派安排！</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("💥 確定清空", type="primary"):
        st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
        st.session_state.show_clear_confirm = False
        st.rerun()
    if c2.button("❌ 取消返回"):
        st.session_state.show_clear_confirm = False
        st.rerun()

audit_results = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
typo_detected, invalid_entries = audit_results["typo"]
vacuum_detected, vacuum_entries = audit_results["vacuum"]
duplicate_detected, duplicate_entries = audit_results["duplicate"]
leave_conflict_detected, leave_conflict_entries = audit_results["leave_conflict"]
master_report_df = audit_results["report_df"]

with btn_col3:
    if PDF_AVAILABLE:
        logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.logo_data else None
        try:
            pdf_bytes = generate_pdf(st.session_state.roster_df, master_report_df, logo_b64)
            st.download_button("📄 導出 A4 橫式公告 PDF", pdf_bytes, f"SYSS_Study_Prefect_Roster.pdf", "application/pdf", use_container_width=True)
        except Exception:
            st.button("📄 PDF 引擎編譯中...", disabled=True, use_container_width=True)
    else:
        st.button("💡 缺少 weasyprint 依賴", disabled=True, use_container_width=True)

# ==========================================
# 12. 智能安全熔斷提示器
# ==========================================
if typo_detected:
    st.markdown('<div class="danger-alert"><b>⚠️ 數據不符警告：</b>手動輸入了名冊之外的姓名。<br>' + '<br>'.join(invalid_entries) + '</div>', unsafe_allow_html=True)
if duplicate_detected:
    st.markdown('<div class="danger-alert"><b>⚠️ 分身重複衝突警告：</b>同名隊員在同日被分配到多個崗位！<br>' + '<br>'.join(duplicate_entries) + '</div>', unsafe_allow_html=True)

if leave_conflict_detected:
    st.markdown('<div class="danger-alert"><b>🛑 請假人員衝突警告：以下同學已請假，但仍殘留於值班表上：</b><br>' + '<br>'.join(leave_conflict_entries) + '</div>', unsafe_allow_html=True)
    if st.button("🩹 一鍵將請假同學從現有值班表中移出 (更換為空白)", type="primary"):
        for d in DAYS:
            for r in ROWS_ROSTER:
                if str(st.session_state.roster_df.at[r, d]).strip() in leave_students:
                    st.session_state.roster_df.at[r, d] = ""
        st.success("✅ 已自動清除請假同學，請利用下方的智慧替補系統補位！")
        st.rerun()
elif vacuum_detected:
    st.markdown('<div class="warning-alert"><b>💡 提示：存在未配對的開門空缺（若手動填寫 X 代表不開放則忽略此訊息）：</b><br>' + '<br>'.join(vacuum_entries) + '</div>', unsafe_allow_html=True)

# ==========================================
# 13. 雙軌呈現中心 (Pandas 奢華著色與 DataEditor 手動校準)
# ==========================================
def apply_cell_style(val, role, day):
    val = str(val).strip()
    if val == "X": return "color: #EF4444; font-weight: bold; text-align: center; background-color: #FEF2F2;"
    if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
        return "background-color: #E5E7EB; color: #9CA3AF; text-align: center; font-style: italic;"
    if val == "": return "background-color: #F9FAFB;"
    base = "font-weight: bold; text-align: center;"
    
    if "Assist" in role: return base + " background-color: #FFF8E1; color: #B45309; border: 1px solid #D4AF37;"
    if "Room302" in role: return base + " background-color: #D1FAE5; color: #166534; border: 1px solid #10B981;"
    if "Room303" in role: return base + " background-color: #FEE2E2; color: #991B1B; border: 1px solid #EF4444;"
    if "Room202" in role: return base + " background-color: #DBEAFE; color: #1E40AF; border: 1px solid #3B82F6;"
    return base

st.write("---")
st.subheader("📅 本週班表狀態與動態調整通道")

# 雙軌化 Tabs
tab_view, tab_edit = st.tabs(["📅 奢華藍金值班表 (視覺公告版)", "✏️ 互動式手動修改 (動態校準版)"])

with tab_view:
    try:
        styled_roster = st.session_state.roster_df.style.apply(
            lambda row: [apply_cell_style(val, row.name, col) for col, val in row.items()], axis=1
        )
        st.dataframe(styled_roster, use_container_width=True, height=260)
    except Exception:
        st.dataframe(st.session_state.roster_df, use_container_width=True, height=260)

with tab_edit:
    st.markdown("<p style='font-size:13px; color:#666;'>💡 您可以直接在下方表格內手動修改或填入人名，輸入 <b>X</b> 代表鎖定該不開放時段：</p>", unsafe_allow_html=True)
    edited_roster_df = st.data_editor(
        st.session_state.roster_df,
        use_container_width=True,
        key="main_roster_editor_widget",
        on_change=sync_roster_data
    )
    if not edited_roster_df.equals(st.session_state.roster_df):
        st.session_state.roster_df = edited_roster_df
        st.rerun()

# ==========================================
# 14. 數據多通道導出板塊
# ==========================================
st.write("---")
st.markdown("### 📊 行政名冊與排班數據多格式導出")
dl_col1, dl_col2 = st.columns(2)

with dl_col1:
    try:
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            st.session_state.roster_df.to_excel(writer, sheet_name='本週值班表')
            master_report_df.to_excel(writer, sheet_name='工作負荷統計', index=False)
        st.download_button(
            label="📊 下載 Excel 行政試算表 (.xlsx)",
            data=output_excel.getvalue(),
            file_name=f"SYSS_Prefect_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    except Exception:
        st.button("📊 Excel 編譯引擎加載中...", disabled=True, use_container_width=True)

with dl_col2:
    try:
        md_data = "### 📅 本週值班表 (Weekly Duty Roster)\n\n" + st.session_state.roster_df.to_markdown() + "\n\n### 📊 累積動態工作負荷審計表\n\n" + master_report_df.to_markdown(index=False)
        st.download_button(
            label="📝 下載 Markdown 簡報純文字 (.md)",
            data=md_data.encode('utf-8'),
            file_name=f"SYSS_Prefect_Roster_{datetime.date.today().strftime('%Y%m%d')}.md",
            mime="text/plain",
            use_container_width=True
        )
    except Exception:
        st.button("📝 Markdown 轉換模組加載中...", disabled=True, use_container_width=True)

# ==========================================
# 15. 工作量公平性數據化審計圖表
# ==========================================
st.write("---")
st.subheader("📊 全體領袖生動態累計工作負荷審計大表")
st.dataframe(master_report_df, use_container_width=True, hide_index=True)

if not master_report_df.empty:
    st.write("---")
    st.subheader("🦅 全體累積工作點數公平性動態監控天平")
    fig = px.bar(
        master_report_df, 
        x='學生姓名 (Prefect Name)', 
        y='最終總計加權負荷 (點)', 
        text_auto='.1f', 
        title="全體領袖生加權工作量天平（點數低者將優先派班）", 
        color='最終總計加權負荷 (點)', 
        color_continuous_scale='gold'
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 16. 智慧替補機制 UI
# ==========================================
st.write("---")
st.subheader("🔍 臨時請假？智慧替補候選人精準建議")

sub_col1, sub_col2 = st.columns(2)
with sub_col1:
    chosen_day = st.selectbox("請假或替換日期 (星期)", DAYS, index=0, key="sub_day_selector")
with sub_col2:
    chosen_role = st.selectbox("請假或替換職位/房間", ROWS_ROSTER, index=0, key="sub_role_selector")

current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
st.text_input("📍 目前該時段排定之人員", value=current_person if current_person not in ["", "X"] else "（當前為空白或特殊不開放時段）", disabled=True)

if st.button("🔮 執行篩選並推薦最優替補人員", type="secondary", use_container_width=True):
    sub_df, error_msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
    if sub_df is not None:
        st.success("📋 媒合成功！已依據「最終總計加權負荷」由低到高為您排序推薦合格替補人員：")
        st.dataframe(sub_df, use_container_width=True, hide_index=True)
    else:
        st.warning(error_msg)
