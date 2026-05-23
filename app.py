import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
import datetime

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
# 2. 學校行政核心常數與點數天平配置
# ==========================================
DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']
ROWS_ROSTER = [
    'Assist. in charge (General Duty)',          # 每日 1 人編制 (總值班學年固定，不計點 = 0.0)
    'Room302 STUDY ROOM (15:40-18:30)',          # 每日 1 人編制 (常規自修最輕鬆，點數 = 1.0)
    'Room303 HW COMPLETION (15:40-17:00) - 1',    # 每日 2 人編制位 1 (留堂功課較辛苦，點數 = 2.0)
    'Room303 HW COMPLETION (15:40-17:00) - 2',    # 每日 2 人編制位 2 (留堂功課較辛苦，點數 = 2.0)
    'Room202 F1 STUDY GROUP (15:40-17:00) - 1',   # 每日 2 人編制位 1 (中一強制較辛苦，點數 = 2.0)
    'Room202 F1 STUDY GROUP (15:40-17:00) - 2'    # 每日 2 人編制位 2 (中一強制較辛苦，點數 = 2.0)
]

WEIGHTS = {
    'Assist. in charge (General Duty)': 0.0,
    'Room302 STUDY ROOM (15:40-18:30)': 1.0,
    'Room303 HW COMPLETION (15:40-17:00) - 1': 2.0,
    'Room303 HW COMPLETION (15:40-17:00) - 2': 2.0,
    'Room202 F1 STUDY GROUP (15:40-17:00) - 1': 2.0,
    'Room202 F1 STUDY GROUP (15:40-17:00) - 2': 2.0
}

# ==========================================
# 3. Session State 狀態機安全初始化
# ==========================================
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=["name", "form", "class", "role", "fixed_general_duty", "available", "history_weight", "remarks"])
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
if 'logo_data' not in st.session_state:
    st.session_state.logo_data = None

# ==========================================
# 4. 數據同步回調函數 (Callbacks) - 徹底終結隨機重置
# ==========================================
def sync_students_data():
    if "student_editor_widget" in st.session_state and st.session_state.student_editor_widget:
        st.session_state.students_df = pd.DataFrame(st.session_state.student_editor_widget.get("current_rows", st.session_state.students_df))

def sync_roster_data():
    if "main_roster_editor_widget" in st.session_state and st.session_state.main_roster_editor_widget:
        st.session_state.roster_df = pd.DataFrame(st.session_state.main_roster_editor_widget.get("current_rows", st.session_state.roster_df))

# ==========================================
# 5. 核心排班演算法 (常規留空 + 特殊關閉熔斷 + 老帶新過濾)
# ==========================================
def generate_roster(students_df: pd.DataFrame, leave_students: list, special_closures: list, seed: int) -> pd.DataFrame:
    if students_df.empty or students_df['name'].str.strip().eq('').all():
        return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    rng = random.Random(seed)
    new_roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    # Step 1: 優先鎖定並橫向填入「學年固定總值班」
    for _, s in students_df.iterrows():
        name = str(s.get('name', '')).strip()
        fixed_day = str(s.get('fixed_general_duty', '')).strip().upper()
        if name and fixed_day in DAYS:
            new_roster.at['Assist. in charge (General Duty)', fixed_day] = name

    # Step 2: 注入全局控制組件設定的「突發特殊不開放 (X)」
    for item in special_closures:
        try:
            day_part, room_part = item.split(" - ")
            for r in ROWS_ROSTER:
                if room_part in r:
                    new_roster.at[r, day_part] = "X"
        except ValueError:
            continue

    # Step 3: 基礎數據預加載快取
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
        base_historical_weights[name] = float(s.get('history_weight', 0.0))
        raw_avail = str(s.get('available', '')).upper().split(',')
        student_avail_cache[name] = {d.strip() for d in raw_avail if d.strip()}

    last_duty_day = {name: -2 for name in current_week_weights}

    # Step 4: 執行精密排班矩陣計算
    for d_idx, day in enumerate(DAYS):
        # 收集當天已經因為固定總值班而被佔用的人員，防止同日重複指派
        assigned_today = set()
        fixed_pic = str(new_roster.at['Assist. in charge (General Duty)', day]).strip()
        if fixed_pic and fixed_pic not in ["", "X"]:
            assigned_today.add(fixed_pic)
        
        dynamic_roles = [r for r in ROWS_ROSTER if r != 'Assist. in charge (General Duty)']
        rng.shuffle(dynamic_roles)
        # 確保同房間的位元 2 較晚處理，以便精確執行老帶新與同日查重
        dynamic_roles.sort(key=lambda x: 1 if "- 2" in x else 0)

        for role in dynamic_roles:
            if new_roster.at[role, day] == "X":
                continue

            # === 【核心常規不開放規則】Room 202 星期二和星期五為常規不開放 -> 嚴格留空白 ===
            if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
                new_roster.at[role, day] = ""
                continue

            # 雙人編制老帶新限制：避免兩名中三 Prefect 同時分在同一個 202 或 303 辛苦房間
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

                score = 0
                w = WEIGHTS[role]
                # 連續值班懲罰
                if last_duty_day.get(name, -2) == d_idx - 1: score += 1000
                # 超出本週單人負荷閾值（4.0點）懲罰
                if current_week_weights.get(name, 0) + w > 4.0: score += 800

                # 聖言年級傾斜：202與303優先派中四中五資深師兄；輕鬆的 302 自修室留給中三新手
                is_senior = any(x in form_str for x in ["4", "5"])
                if 'Room202' in role or 'Room303' in role:
                    score += -60 if is_senior else 60
                elif 'Room302' in role:
                    score += 40 if is_senior else -40

                # 依據歷史和當週累積點數進行公平調配
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

# ==========================================
# 6. 全局數據審計與統計系統 (過濾固定總值班次數干擾)
# ==========================================
def validate_and_compute(roster_df: pd.DataFrame, students_df: pd.DataFrame, leave_students: list):
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
                # 排除 Room 202 週二週五常規不開放，其餘留空才觸發真空警報
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
                duplicate_entries.append(f"【{d}】{val} 同日同時分配於「{day_assigned_map[val]}」與「{r}」")
            else:
                day_assigned_map[val] = r

            if val in leave_students:
                leave_conflict_detected = True
                leave_conflict_entries.append(f"【{d} — {r}】: {val} 已請假")

    final_records = []
    for _, s in students_df.iterrows():
        name = str(s.get('name', '')).strip()
        if not name: continue
        this_week_rooms_duties = 0 
        this_week_weight = 0.0
        
        if not typo_detected:
            for d in DAYS:
                for r in ROWS_ROSTER:
                    if str(roster_df.at[r, d]).strip() == name:
                        this_week_weight += WEIGHTS.get(r, 0.0)
                        # 【數據去噪】如果不是學年固定總值班，才計入動態輪替房間次數
                        if r != 'Assist. in charge (General Duty)':
                            this_week_rooms_duties += 1
                        
        final_records.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": s.get('form', ''),
            "班別 (Class)": s.get('class', ''),
            "職級 (Role)": s.get('role', ''),
            "學年固定總值班": s.get('fixed_general_duty', ''),
            "歷史動態累計 (點)": float(s.get('history_weight', 0.0)),
            "當週新增房間值班 (次)": this_week_rooms_duties,
            "當週新增負荷 (點)": round(this_week_weight, 1),
            "最終動態總加權負荷 (點)": round(float(s.get('history_weight', 0.0)) + this_week_weight, 1),
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
# 7. 智慧替補推薦系統
# ==========================================
def recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if current_person in ["", "X"]:
        return None, "該時段無需替補、為常規關閉或目前不開放。"

    assigned_today = {str(roster_df.at[r, chosen_day]).strip() for r in ROWS_ROSTER if str(roster_df.at[r, chosen_day]).strip() not in ["", "X"]}
    is_general_duty_selected = (chosen_role == 'Assist. in charge (General Duty)')
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
        if (is_general_duty_selected and not is_ahp) or (not is_general_duty_selected and is_ahp): 
            continue
        if partner_is_junior and "3" in str(s.get('form', '')): 
            continue

        this_week_weight = 0.0
        for d in DAYS:
            for r in ROWS_ROSTER:
                if str(roster_df.at[r, d]).strip() == name:
                    this_week_weight += WEIGHTS.get(r, 0.0)

        candidates.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": s.get('form', ''),
            "最終動態總加權負荷 (點)": round(float(s.get('history_weight', 0.0)) + this_week_weight, 1)
        })

    if candidates:
        return pd.DataFrame(candidates).sort_values(by="最終動態總加權負荷 (點)"), None
    return None, "找不到符合天數可用與職級限制的替補人員。"

# ==========================================
# 8. A4 橫式高級 PDF 渲染引擎
# ==========================================
def generate_pdf(roster_df, master_report_df, logo_b64=None):
    today = datetime.date.today().strftime("%Y-%m-%d")
    html_table = roster_df.to_html(classes='table')
    report_table = master_report_df[["學生姓名 (Prefect Name)", "年級 (Form)", "班別 (Class)", "職級 (Role)", "當週新增房間值班 (次)", "最終動態總加權負荷 (點)"]].to_html(index=False, classes='table')
    
    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 20mm; }}
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; line-height: 1.4; }}
        .header-container {{ text-align: center; margin-bottom: 25px; }}
        h1 {{ color:#0C2340; font-size: 26px; margin: 5px 0; letter-spacing: 1px; }}
        h2 {{ color:#D4AF37; font-size: 16px; margin: 0 0 10px 0; font-weight: 600; text-transform: uppercase; }}
        .date-sub {{ font-size: 11px; color: #666; margin-bottom: 20px; }}
        h3 {{ color:#0C2340; border-left: 5px solid #D4AF37; padding-left: 10px; margin-top: 30px; font-size: 16px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 11px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        th, td {{ border: 1px solid #D1D5DB; padding: 8px 10px; text-align: center; }}
        th {{ background-color: #0C2340; color: white; font-weight: bold; text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px; }}
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
# 9. 側邊欄大數據維護區 (加入實時 On-Change 與 Key 雙強固)
# ==========================================
with st.sidebar:
    st.markdown("### 🦅 校徽與行政系統")
    uploaded_logo = st.file_uploader("上傳校徽圖片 (PNG)", type=["png"], key="logo_uploader")
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()

    st.write("---")
    st.markdown("### 🗄️ 快速測試通道")
    if st.button("💡 載入 Sing Yin 官方標準示範名冊", use_container_width=True):
        demo_data = [
            {"name": "陳卓軒", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "fixed_general_duty": "MONDAY", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_weight": 0.0, "remarks": "固定週一總值班"},
            {"name": "李浩然", "form": "F.5", "class": "5B", "role": "Assistant Head Study Prefect", "fixed_general_duty": "WEDNESDAY", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", "history_weight": 0.0, "remarks": "固定週三總值班"},
            {"name": "張凱傑", "form": "F.4", "class": "4A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_weight": 14.0, "remarks": ""},
            {"name": "黃子軒", "form": "F.4", "class": "4B", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "TUESDAY,WEDNESDAY,FRIDAY", "history_weight": 12.0, "remarks": ""},
            {"name": "林俊傑", "form": "F.3", "class": "3A", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,TUESDAY,THURSDAY", "history_weight": 6.0, "remarks": ""},
            {"name": "王偉倫", "form": "F.5", "class": "5C", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "MONDAY,WEDNESDAY,FRIDAY", "history_weight": 11.0, "remarks": ""},
            {"name": "劉家豪", "form": "F.4", "class": "4C", "role": "Study Prefect", "fixed_general_duty": "NONE", "available": "TUESDAY,THURSDAY", "history_weight": 8.0, "remarks": ""},
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
            "history_weight": st.column_config.NumberColumn("歷史動態(點)", min_value=0.0, step=0.5),
            "remarks": st.column_config.TextColumn("備註")
        },
        num_rows="dynamic", use_container_width=True, hide_index=True, 
        key="student_editor_widget", on_change=sync_students_data
    )

    st.write("---")
    st.markdown("### 🛑 突發臨時請假登記")
    valid_names_list = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    leave_students = st.multiselect("選取今日請假人員：", options=valid_names_list, default=[], key="leave_tracker")

# ==========================================
# 10. 主畫面大數據控制中心
# ==========================================
st.markdown('<p class="main-title">🦅 SING YIN STUDY PREFECT ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Smart Scheduling Platform | v10.0 終極完全體商用版</p>', unsafe_allow_html=True)

# 💡 全局特殊關閉快捷控制組件（一鍵標記 X 阻斷排班）
closure_options = []
for d in DAYS:
    for room in ["Room302", "Room303", "Room202"]:
        if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"]): 
            closure_options.append(f"{d} - {room}")

selected_closures = st.multiselect(
    "🛠️ 設定本週「突發人手不足/特殊不開放」時段（將自動標記為 X 並阻斷排班）：",
    options=closure_options,
    key="special_closures"
)

btn_col1, btn_col2, btn_col3 = st.columns([2, 1.5, 1.5])

with btn_col1:
    if st.button("🚀 智能計算：生成本週全新公平值班表", type="primary", use_container_width=True):
        with st.spinner("遵守常規不開放與計點規則計算中..."):
            seed = random.randint(10000, 99999)
            st.session_state.roster_df = generate_roster(st.session_state.students_df, leave_students, selected_closures, seed)
            st.success(f"🎉 排班計算成功！動態驗證碼: SY-{seed}")

with btn_col2:
    if st.button("🗑️ 一鍵清空當前排班表", type="secondary", use_container_width=True):
        st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
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
# 11. 智能安全熔斷提示器
# ==========================================
if typo_detected:
    st.markdown('<div class="danger-alert"><b>⚠️ 數據不符警告：</b>手動輸入了名冊之外的姓名。<br>' + '<br>'.join(invalid_entries) + '</div>', unsafe_allow_html=True)
if duplicate_detected:
    st.markdown('<div class="danger-alert"><b>⚠️ 分身重複衝突警告：</b>同名隊員在同日被分配到多個崗位！<br>' + '<br>'.join(duplicate_entries) + '</div>', unsafe_allow_html=True)
if leave_conflict_detected:
    st.markdown('<div class="danger-alert"><b>🛑 請假人員衝突警告：</b>請假同學仍殘留於值班表上！<br>' + '<br>'.join(leave_conflict_entries) + '</div>', unsafe_allow_html=True)

# ==========================================
# 12. 雙軌呈現中心 (色彩渲染隔離學年常規與突發 X)
# ==========================================
def apply_cell_style(val, role, day):
    val = str(val).strip()
    if val == "X": return "color: #EF4444; font-weight: bold; text-align: center; background-color: #FEF2F2;"
    if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
        return "background-color: #E5E7EB; color: #9CA3AF; text-align: center; font-style: italic;"
    if val == "": return "background-color: #F9FAFB;"
    base = "font-weight: bold; text-align: center;"
    
    if "Assist" in role: return base + " background-color: #0C2340; color: #D4AF37; border: 1px solid #D4AF37;"
    if "Room202" in role or "Room303" in role: return base + " background-color: #FEE2E2; color: #991B1B; border: 1px solid #EF4444;"
    if "Room302" in role: return base + " background-color: #D1FAE5; color: #065F46; border: 1px solid #10B981;"
    return base

tab_edit, tab_view = st.tabs(["✏️ 互動式手動微調大表", "🎨 聖言色彩公告預覽"])

with tab_edit:
    st.session_state.roster_df = st.data_editor(
        st.session_state.roster_df, use_container_width=True, height=280, 
        key="main_roster_editor_widget", on_change=sync_roster_data
    )

with tab_view:
    style_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS)
    for d in DAYS:
        for r in ROWS_ROSTER:
            style_df.at[r, d] = apply_cell_style(st.session_state.roster_df.at[r, d], r, d)
    styled_roster = st.session_state.roster_df.style.apply(lambda _: style_df, axis=None)
    st.dataframe(styled_roster, use_container_width=True, height=280)

# ==========================================
# 13. 智慧替補推薦系統 UI
# ==========================================
st.write("---")
st.markdown("### 🔄 突發請假智能補位推薦")
sub_col1, sub_col2, sub_col3 = st.columns([1.5, 1.5, 2])

with sub_col1:
    chosen_day = st.selectbox("請選取目標日期：", DAYS, key="sub_day_sel")
with sub_col2:
    chosen_role = st.selectbox("請選取需要補位的崗位：", ROWS_ROSTER, key="sub_role_sel")
with sub_col3:
    current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
    st.text_input("目前該崗位原定人員：", value=current_person if current_person not in ["", "X"] else "（空缺 / 常規不開放）", disabled=True)

if st.button("🔍 執行智慧替補媒合分析", type="primary"):
    if 'Room202' in chosen_role and chosen_day in ['TUESDAY', 'FRIDAY']:
        st.warning("💡 該日期為 Room 202 常規不開放日，無需安排替補人員。")
    else:
        sub_df, msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
        if sub_df is not None:
            st.success("📋 媒合成功！已依據「累積動態加權總負荷」由低到高為您排序推薦替補人員：")
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
        else:
            st.warning(msg)

# ==========================================
# 14. 工作量公平性數據化審計圖表 (優化過濾總值班干擾)
# ==========================================
if not master_report_df.empty and not typo_detected:
    st.write("---")
    st.markdown("### 📊 全體動態工作量公平性監控審計 (已排除學年固定總值班次數與點數)")
    
    chart_df = master_report_df[master_report_df['最終動態總加權負荷 (點)'] > 0]
    if chart_df.empty:
        chart_df = master_report_df
        
    median_load = chart_df['最終動態總加權負荷 (點)'].median()
    
    fig = px.bar(
        chart_df, 
        x='學生姓名 (Prefect Name)', 
        y='最終動態總加權負荷 (點)', 
        text_auto='.1f', 
        color='最終動態總加權負荷 (點)',
        color_continuous_scale='Reds',
        labels={'最終動態總加權負荷 (點)': '動態房間核心總負荷 (點)'},
        title=f"聖言領袖生房間加權總負載分佈 (真實輪替公平中位線: {median_load:.1f} 點)"
    )
    
    fig.update_layout(
        font=dict(family="Arial", size=12),
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="領袖生姓名",
        yaxis_title="房間點數加權總和 (點)"
    )
    fig.add_hline(y=median_load, line_dash="dash", line_color="#0C2340", annotation_text="真實房間輪替中位線", annotation_position="top left")
    
    st.plotly_chart(fig, use_container_width=True)

st.caption("Sing Yin Secondary School Study Prefect Administration System | Version 10.0 終極完全體商用版")
