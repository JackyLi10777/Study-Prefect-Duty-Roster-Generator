import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
from io import BytesIO
import datetime

# ==========================================
# 0. PDF 支援與環境強固檢查（相容 Streamlit Cloud）
# ==========================================
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False

# ==========================================
# 1. 網頁設定與奢華聖言視覺 UI 注入
# ==========================================
st.set_page_config(
    page_title="Sing Yin Study Prefect Duty Roster",
    page_icon=" 🦅 ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：美化邊框、按鈕、表格、二次確認區與熔斷器警告區
st.markdown("""
<style>
    .main > div { padding-top: 1.5rem !important; }
    .main-title { color: #0C2340; font-size: 38px; font-weight: bold; letter-spacing: 2px; margin-bottom: 5px; }
    .main-subtitle { color: #D4AF37; font-size: 16px; font-weight: 600; margin-bottom: 25px; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { height: 3.2rem; font-weight: bold; border-radius: 10px; width: 100% !important; transition: all 0.3s; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; box-shadow: 0 2px 8px rgba(239,68,68,0.1);}
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; color: #92400E; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; box-shadow: 0 2px 8px rgba(245,158,11,0.1);}
    .confirm-box { background-color: #F8FAFC; border: 2px dashed #CBD5E1; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 學校行政核心常數
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
# 聖言專屬加權：Room302與總值班時間較長或責任重，計1.0點；其餘小組計1.5點
WEIGHTS = {row: 1.0 if 'Room302' in row or 'Assist' in row else 1.5 for row in ROWS_ROSTER}

# ==========================================
# 3. Session State 狀態機安全初始化
# ==========================================
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=["name", "form", "class", "role", "available", "history_duties", "history_weight", "remarks"])
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
if 'logo_data' not in st.session_state:
    st.session_state.logo_data = None
if 'show_clear_confirm' not in st.session_state:
    st.session_state.show_clear_confirm = False

# ==========================================
# 4. 核心排班演算法 (聖言中學專用公平最大化版)
# ==========================================
def generate_roster(students_df: pd.DataFrame, leave_students: list, seed: int) -> pd.DataFrame:
    if students_df.empty or students_df['name'].str.strip().eq('').all():
        st.error(" ⚠️  學生名冊為空，請先在側邊欄新增或導入資料！")
        return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
    rng = random.Random(seed)
    new_roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
    
    # 【防禦機制】保留用戶在互動大表中手動填入的 "X" 不開放標記
    for r in ROWS_ROSTER:
        for d in DAYS:
            if r in st.session_state.roster_df.index and d in st.session_state.roster_df.columns:
                if str(st.session_state.roster_df.at[r, d]).strip().upper() == "X":
                    new_roster.at[r, d] = "X"
                    
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
    
    for d_idx, day in enumerate(DAYS):
        assigned_today = set()
        # 隨機打亂崗位順序，避免排序靠前的房間總是分到特定特徵的同學
        shuffled_roles = list(ROWS_ROSTER)
        rng.shuffle(shuffled_roles)
        # 確保老帶新規則中，"- 2"（副手位）較晚指派，以便偵測 "- 1"（主導位）的年級
        shuffled_roles.sort(key=lambda x: 1 if "- 2" in x else 0)
        
        for role in shuffled_roles:
            if new_roster.at[role, day] == "X":
                continue
            # === 聖言中學行政限制：Room202 週二、週五不開放自修 ===
            if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
                new_roster.at[role, day] = ""
                continue
            
            # 偵測是否觸發老帶新限制（避免 F.3 隊員互相搭配）
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
                # 職務身份隔離：隊長（Assistant Head）專職負責總值班
                is_ahp = str(s.get('role', '')).strip() == "Assistant Head Study Prefect"
                if (role.startswith('Assist') and not is_ahp) or (not role.startswith('Assist') and is_ahp):
                    continue
                form_str = student_form_map.get(name, "")
                if partner_is_junior and "3" in form_str:
                    continue
                
                # 評分機制（Score 越低代表越優先指派）
                score = 0
                w = WEIGHTS[role]
                # 懲罰項：避免連續兩天值班 (加權 1000)
                if last_duty_day.get(name, -2) == d_idx - 1: score += 1000
                # 懲罰項：避免單週負荷過度超出 3.0 點 (加權 800)
                if current_week_weights.get(name, 0) + w > 3.0: score += 800
                # 期望項：高級數（F.4, F.5）優先顧大房，初級數顧小房
                is_senior = any(x in form_str for x in ["4", "5"])
                if 'Room302' in role:
                    score += 40 if is_senior else -40
                elif 'Room303' in role or 'Room202' in role:
                    score += -40 if is_senior else 40
                
                # 公平性核心：累積歷史與當週點數總和越低者，越優先指派
                total_load = base_historical_weights.get(name, 0) + current_week_weights.get(name, 0)
                score += total_load * 20
                candidates.append((score, name, w))
                
            if candidates:
                candidates.sort(key=lambda x: x[0])
                # 引入雙最優隨機挑選，打破死板排班，增加輪替彈性
                chosen = rng.choice(candidates[:min(2, len(candidates))])
                chosen_name = chosen[1]
                new_roster.at[role, day] = chosen_name
                assigned_today.add(chosen_name)
                current_week_weights[chosen_name] += chosen[2]
                last_duty_day[chosen_name] = d_idx
    return new_roster

# ==========================================
# 5. 全域即時審計與數據統計系統 (四軌防呆，含真空時段提示)
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
        day_assigned_map = {}  # 用於追蹤同日內 Prefect 是否分身多地
        for r in ROWS_ROSTER:
            val = str(roster_df.at[r, d]).strip()
            if not val:
                # 檢查是否為正常關閉的時段
                is_closed = ('Room202' in r and d in ['TUESDAY', 'FRIDAY'])
                if not is_closed:
                    vacuum_detected = True
                    vacuum_entries.append(f"【{d} — {r}】")
                continue
                
            if val == "X":
                continue
            # 軌道 1：檢查手動輸入姓名是否存在於名冊中
            if val not in valid_names:
                typo_detected = True
                invalid_entries.append(f"【{d} — {r}】: 填寫的「{val}」不存在於在線名冊中")
                continue
            # 軌道 2：檢查同日重複指派衝突
            if val in day_assigned_map:
                duplicate_detected = True
                duplicate_entries.append(f"【{d}】{val} 同時出現在「{day_assigned_map[val]}」與「{r}」")
            else:
                day_assigned_map[val] = r
            # 軌道 3：檢查請假狀態衝突
            if val in leave_students:
                leave_conflict_detected = True
                leave_conflict_entries.append(f"【{d} — {r}】: {val} 已登記請假，請安排替補")
                
    # 計算本週新增工作量與累積點數
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
                        this_week_duties += 1
                        this_week_weight += WEIGHTS.get(r, 1.0)
                        
        final_records.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": s.get('form', ''),
            "班別 (Class)": s.get('class', ''),
            "職級 (Role)": s.get('role', ''),
            "可用日子 (Available Days)": s.get('available', ''),
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
# 6. 完整智慧替補推薦系統
# ==========================================
def recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if current_person in ["", "X"]:
        return None, "該時段無需替補或目前不開放。"
    # 抓取當天已值班人員，避免重複排班
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
            
        # 計算該候選人目前的臨時總加權
        this_week_weight = 0.0
        for d in DAYS:
            for r in ROWS_ROSTER:
                if str(roster_df.at[r, d]).strip() == name:
                    this_week_weight += WEIGHTS.get(r, 1.0)
                    
        candidates.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": s.get('form', ''),
            "班別 (Class)": s.get('class', ''),
            "最終總計加權負荷 (點)": round((float(s.get('history_weight', 0.0)) if pd.notna(s.get('history_weight')) else 0.0) + this_week_weight, 1)
        })
        
    if candidates:
        return pd.DataFrame(candidates).sort_values(by="最終總計加權負荷 (點)"), None
    return None, "找不到符合天數可用、職級限制、且滿足老帶新規則的替補人員。"

# ==========================================
# 7. A4 橫式高級 PDF 渲染引擎 (含完整校徽圖片嵌入邏輯)
# ==========================================
def generate_pdf(roster_df, master_report_df, logo_b64=None):
    today = datetime.date.today().strftime("%Y-%m-%d")
    html_table = roster_df.to_html(classes='table')
    report_table = master_report_df[["學生姓名 (Prefect Name)", "年級 (Form)", "班別 (Class)", "職級 (Role)", "當週新增 (次)", "最終總計加權負荷 (點)"]].to_html(index=False, classes='table')
    
    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 15mm; }}
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
        html += f'<img src="data:image/png;base64,{logo_b64}" style="height:65px; margin-bottom:10px;"><br>'
    html += f"""
        <h1>Sing Yin Secondary School</h1>
        <h2>Study Prefect Duty Roster & Workload Audit</h2>
        <div class="date-sub">Report Generated Date: {today}</div>
    </div>
    <h3> 📅  本週值班表 (Weekly Duty Roster)</h3>
    {html_table}
    <div style="page-break-before: always;"></div>
    <h3> 📊  累積工作負荷審計表 (Workload Audit Report)</h3>
    {report_table}
    </body></html>
    """
    return HTML(string=html).write_pdf()

# ==========================================
# 8. 側邊欄大數據維護區
# ==========================================
with st.sidebar:
    st.markdown("###  🦅  校徽與行政系統")
    uploaded_logo = st.file_uploader("上傳校徽圖片 (PNG)", type=["png"], key="logo_uploader")
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()
        
    st.write("---")
    st.markdown("###  🗄️  快速測試通道")
    if st.button(" 💡  載入 Sing Yin 官方標準示範名冊", use_container_width=True):
        demo_data = [
            {"name": "陳卓軒", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 12, "history_weight": 12.0, "remarks": "總隊長"},
            {"name": "李浩然", "form": "F.5", "class": "5B", "role": "Assistant Head Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 10, "history_weight": 10.0, "remarks": "副隊長"},
            {"name": "張凱傑", "form": "F.4", "class": "4A", "role": "Study Prefect", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 9, "history_weight": 13.5, "remarks": ""},
            {"name": "黃子軒", "form": "F.4", "class": "4B", "role": "Study Prefect", "available": "TUESDAY,WEDNESDAY,FRIDAY", "history_duties": 8, "history_weight": 12.0, "remarks": ""},
            {"name": "林俊傑", "form": "F.3", "class": "3A", "role": "Study Prefect", "available": "MONDAY,TUESDAY,THURSDAY", "history_duties": 6, "history_weight": 9.0, "remarks": "需學長帶領"},
            {"name": "王偉倫", "form": "F.5", "class": "5C", "role": "Study Prefect", "available": "MONDAY,WEDNESDAY,FRIDAY", "history_duties": 7, "history_weight": 10.5, "remarks": ""},
            {"name": "劉家豪", "form": "F.4", "class": "4C", "role": "Study Prefect", "available": "TUESDAY,THURSDAY", "history_duties": 5, "history_weight": 7.5, "remarks": ""}
        ]
        st.session_state.students_df = pd.DataFrame(demo_data)
        st.success(" ✅  聖言中學標準名冊已載入")
        st.rerun()
        
    st.write("---")
    st.markdown("###  👥  在線名冊即時維護")
    edited_students = st.data_editor(
        st.session_state.students_df,
        column_config={
            "name": st.column_config.TextColumn("姓名 *", required=True),
            "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5"]),
            "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"]),
            "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
            "history_duties": st.column_config.NumberColumn("歷史(次)", min_value=0, step=1),
            "history_weight": st.column_config.NumberColumn("歷史(點)", min_value=0.0, step=0.5),
            "remarks": st.column_config.TextColumn("備註")
        },
        num_rows="dynamic", use_container_width=True, hide_index=True, key="student_editor_widget"
    )
    st.session_state.students_df = edited_students
    
    st.write("---")
    st.markdown("###  🛑  突發臨時請假登記")
    valid_names_list = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    leave_students = st.multiselect("選取今日請假人員：", options=valid_names_list, default=[], key="leave_tracker")

# ==========================================
# 9. 主畫面控制中心
# ==========================================
st.markdown('<p class="main-title"> 🦅  SING YIN STUDY PREFECT ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Smart Scheduling Platform | v9.5 終極行政完美合體完全體</p>', unsafe_allow_html=True)

# 核心數據流：即時進行全域四軌熔斷檢測與統計
audit_results = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
typo_detected, invalid_entries = audit_results["typo"]
vacuum_detected, vacuum_entries = audit_results["vacuum"]
duplicate_detected, duplicate_entries = audit_results["duplicate"]
leave_conflict_detected, leave_conflict_entries = audit_results["leave_conflict"]
master_report_df = audit_results["report_df"]

# 控制按鈕佈局
btn_col1, btn_col2, btn_col3 = st.columns([2, 1.5, 1.5])
with btn_col1:
    if st.button(" 🚀  智能計算：生成本週全新公平值班表", type="primary", use_container_width=True):
        with st.spinner("量子演算法公平配對計算中..."):
            seed = random.randint(10000, 99999)
            st.session_state.roster_df = generate_roster(st.session_state.students_df, leave_students, seed)
            st.success(f" 🎉  排班計算成功！動態驗證碼: SY-{seed}")
            st.rerun()

with btn_col2:
    if st.button(" 🗑️  一鍵清空當前排班表", type="secondary", use_container_width=True):
        st.session_state.show_clear_confirm = True

with btn_col3:
    if PDF_AVAILABLE:
        logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.logo_data else None
        try:
            pdf_bytes = generate_pdf(st.session_state.roster_df, master_report_df, logo_b64)
            st.download_button(" 📄  導出 A4 橫式公告 PDF", pdf_bytes, f"SYSS_Study_Prefect_Roster.pdf", "application/pdf", use_container_width=True)
        except Exception as e:
            st.button(" 📄  PDF 引擎編譯中...", disabled=True, use_container_width=True)
    else:
        st.button(" 💡  缺少 weasyprint 依賴無法導出 PDF", disabled=True, use_container_width=True)

# 【第 5 項回歸：防手滑清空二次確認機制流】
if st.session_state.show_clear_confirm:
    st.markdown('<div class="confirm-box">', unsafe_allow_html=True)
    st.markdown("""<p style="color:#EF4444; font-weight:bold; font-size:16px;">⚠️ 警告：您確定要清除大表上的所有排班數據嗎？手動微調的紀錄也將消失。</p>""", unsafe_allow_html=True)
    conf_c1, conf_c2 = st.columns(2)
    if conf_c1.button("確定清空表格", type="primary", key="confirm_clear_btn"):
        st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
        st.session_state.show_clear_confirm = False
        st.success("✅ 已清空表格！")
        st.rerun()
    if conf_c2.button("取消清除操作", type="secondary", key="cancel_clear_btn"):
        st.session_state.show_clear_confirm = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 10. 智能安全熔斷與行政提示器
# ==========================================
if typo_detected:
    st.markdown('<div class="danger-alert"><b> ⚠️  數據不符警告（已暫停負荷審計）：</b>手動微調輸入了名冊之外的姓名。<br>' + '<br>'.join(invalid_entries) + '</div>', unsafe_allow_html=True)
if duplicate_detected:
    st.markdown('<div class="danger-alert"><b> ⚠️  分身重複衝突警告：</b>同一名隊員在同一天被分配到多個崗位！<br>' + '<br>'.join(duplicate_entries) + '</div>', unsafe_allow_html=True)
if leave_conflict_detected:
    st.markdown('<div class="danger-alert"><b> 🛑  請假人員衝突警告：</b>以下同學已登記請假，但目前仍殘留於值班表上！<br>' + '<br>'.join(leave_conflict_entries) + '</div>', unsafe_allow_html=True)
    if st.button(" 🩹  一鍵自動清除請假人員並釋出空缺"):
        for d in DAYS:
            for r in ROWS_ROSTER:
                if str(st.session_state.roster_df.at[r, d]).strip() in leave_students:
                    st.session_state.roster_df.at[r, d] = ""
        st.success(" ✅  請假人員清除完畢！請使用下方智慧補位系統安排替補。")
        st.rerun()

# 【第 4 項回歸：不小心漏排的空白時段行政提醒（Vacuum Detected）】
if vacuum_detected and not typo_detected:
    st.markdown('<div class="warning-alert"><b> 💡  行政提示（存在未配對空缺）：</b>以下正常開放的時段目前無人值班。若您預計手動填寫 <b>X</b> 代表該時段人手不足不開放，則可忽略此提示。<br>' + '<br>'.join(vacuum_entries) + '</div>', unsafe_allow_html=True)

# ==========================================
# 11. 雙軌呈現中心：手動微調與奢華渲染
# ==========================================
def apply_cell_style(val, role):
    val = str(val).strip()
    if val == "X":
        return "color: #EF4444; font-weight: bold; text-align: center; background-color: #FEF2F2;"
    if val == "":
        return "background-color: #F3F4F6;"
    base = "font-weight: bold; text-align: center;"
    if "Assist" in role:
        return base + " background-color: #FFF8E1; color: #B45309; border: 1px solid #FCD34D;"
    if "Room302" in role:
        return base + " background-color: #D1FAE5; color: #166534; border: 1px solid #6EE7B7;"
    if "Room303" in role:
        return base + " background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5;"
    if "Room202" in role:
        return base + " background-color: #FEF3C7; color: #854D0E; border: 1px solid #FDE68A;"
    return base

tab_edit, tab_view = st.tabs([" ✏️  互動式手動微調大表", " 🎨  聖言色彩公告預覽"])
with tab_edit:
    st.caption(" 💡  提示：您可以直接雙擊表格內格子修改人名、清除人名，或填入 'X' 代表該時段不開放自修室。修改後系統會即時重新計算審計工作量。")
    updated_roster = st.data_editor(st.session_state.roster_df, use_container_width=True, height=280, key="main_roster_editor_widget")
    st.session_state.roster_df = updated_roster

with tab_view:
    styled_roster = st.session_state.roster_df.style.apply(
        lambda col: [apply_cell_style(v, st.session_state.roster_df.index[i]) for i, v in enumerate(col)], axis=0
    )
    st.dataframe(styled_roster, use_container_width=True, height=280)

# ==========================================
# 12. 智慧替補推薦系統 UI
# ==========================================
st.write("---")
st.markdown("###  🔄  突發請假智能補位推薦")
sub_col1, sub_col2, sub_col3 = st.columns([1.5, 1.5, 2])
with sub_col1:
    chosen_day = st.selectbox("請選取目標日期：", DAYS, key="sub_day_sel")
with sub_col2:
    chosen_role = st.selectbox("請選取需要補位的崗位：", ROWS_ROSTER, key="sub_role_sel")
with sub_col3:
    # 【第 2 項回歸：目前原定人員狀態動態提示唯讀輸入框】
    if chosen_role in st.session_state.roster_df.index and chosen_day in st.session_state.roster_df.columns:
        current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
    else:
        current_person = ""
    st.text_input("目前該崗位原定人員：", value=current_person if current_person not in ["", "X"] else "（此時段目前為空缺 / 不開放）", disabled=True, key="current_person_display")

if st.button(" 🔍  執行智慧替補媒合分析", type="primary"):
    sub_df, msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
    if sub_df is not None:
        st.success(" 📋  媒合成功！已為您篩選出當天無值班、符合年級與職級資格，且依據「累積加權總負荷」由低到高排序的推薦人員：")
        st.dataframe(sub_df, use_container_width=True, hide_index=True)
    else:
        st.warning(msg)

# ==========================================
# 13. 工作量公平性數據化審計圖表
# ==========================================
if not master_report_df.empty and not typo_detected:
    st.write("---")
    st.markdown("###  📊  全體工作量公平性監控審計審查 (含跨週歷史累積點數)")
    
    # 【第 3 項回歸：計算全體中位數（Median Load）並繪製公平基準線】
    median_load = master_report_df['最終總計加權負荷 (點)'].median()
    
    fig = px.bar(
        master_report_df, 
        x='學生姓名 (Prefect Name)', 
        y='最終總計加權負荷 (點)', 
        text_auto='.1f', 
        title=f"全體累積工作加權點數監控（當前全隊負荷中位數公平線：{median_load:.1f} 點）", 
        color='最終總計加權負荷 (點)', 
        color_continuous_scale='gold'
    )
    
    # 畫上中位數虛線
    fig.add_hline(
        y=median_load, 
        line_dash="dash", 
        line_color="#EF4444", 
        annotation_text=f"公平基準線 (中位數: {median_load:.1f} 點)", 
        annotation_position="top right"
    )
    
    fig.update_layout(
        xaxis_title="領袖生姓名",
        yaxis_title="總累計點數 (歷史 + 新增)",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 同步輸出完整的大表報告
    st.markdown("####  📋  最終行政監控審計明細數據表")
    st.dataframe(master_report_df, use_container_width=True, hide_index=True)
