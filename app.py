import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
from io import BytesIO
import datetime

# ==========================================
# 0. PDF 支援（Streamlit Cloud 強固相容版）
# ==========================================
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False

# ==========================================
# 1. 網頁設定與奢華 UI 注入
# ==========================================
st.set_page_config(
    page_title="Sing Yin Study Prefect Duty Roster",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main > div { padding-top: 1.5rem !important; }
    .main-title { color: #0C2340; font-size: 36px; font-weight: bold; letter-spacing: 2px; }
    .main-subtitle { color: #D4AF37; font-size: 16px; font-weight: 600; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { height: 3.2rem; font-weight: bold; border-radius: 10px; width: 100% !important; }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px;}
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; color: #92400E; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 學校行政常數
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
WEIGHTS = {row: 1.0 if 'Room302' in row or 'Assist' in row else 1.5 for row in ROWS_ROSTER}

# ==========================================
# 3. Session State 安全初始化
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
# 4. 核心排班演算法 (聖言中學專用優化版)
# ==========================================
def generate_roster(students_df: pd.DataFrame, leave_students: list, seed: int) -> pd.DataFrame:
    if students_df.empty or students_df['name'].str.strip().eq('').all():
        st.error("⚠️ 學生名冊為空，請先在側邊欄新增或導入資料！")
        return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    rng = random.Random(seed)
    new_roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    # 保留手動微調填入的 "X" 不開放標記
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
        
        # 打亂崗位順序，避免優先指派特定房間
        shuffled_roles = list(ROWS_ROSTER)
        rng.shuffle(shuffled_roles)
        shuffled_roles.sort(key=lambda x: 1 if "- 2" in x else 0)

        for role in shuffled_roles:
            if new_roster.at[role, day] == "X":
                continue

            # === Sing Yin 實際開放規則：Room202 週二五不開放 ===
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
# 5. 驗證與數據統計系統（高相容快取）
# ==========================================
@st.cache_data(ttl=2)
def validate_and_compute(roster_df: pd.DataFrame, students_df: pd.DataFrame):
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
                invalid_entries.append(f"【{d} - {r}】: {val}")
            is_closed = ('Room202' in r and d in ['TUESDAY', 'FRIDAY'])
            if val == "" and not is_closed:
                vacuum_detected = True
                vacuum_entries.append(f"【{d} - {r}】")

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
# 6. 完整智慧替補推薦系統
# ==========================================
def recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    current_person = str(roster_df.at[chosen_role, chosen_day]).strip()
    if current_person in ["", "X"]:
        return None, "該時段無需替補"

    # 使用無快取的純淨數據集計算，杜絕迴圈相依
    valid_names = set(str(name).strip() for name in students_df["name"].dropna() if str(name).strip())
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
        if not name or name == current_person or name in assigned_today: continue
        
        avail_days = {d.strip().upper() for d in str(s.get('available', '')).split(',') if d.strip()}
        if chosen_day not in avail_days: continue
        
        is_ahp = str(s.get('role', '')).strip() == "Assistant Head Study Prefect"
        if (is_ahp_required and not is_ahp) or (not is_ahp_required and is_ahp): continue
        if partner_is_junior and "3" in str(s.get('form', '')): continue

        # 計算目前臨時總加權
        this_week_weight = 0.0
        for d in DAYS:
            for r in ROWS_ROSTER:
                if str(roster_df.at[r, d]).strip() == name:
                    this_week_weight += WEIGHTS.get(r, 1.0)

        candidates.append({
            "學生姓名 (Prefect Name)": name,
            "年級 (Form)": s.get('form', ''),
            "班別 (Class)": s.get('class', ''),
            "最終總計加權負荷 (點)": round(float(s.get('history_weight', 0.0)) + this_week_weight, 1)
        })

    if candidates:
        sub_df = pd.DataFrame(candidates).sort_values(by="最終總計加權負荷 (點)")
        return sub_df, None
    return None, "找不到符合天數、職級及老帶新條件的替補人員"

# ==========================================
# 7. 高級 PDF 渲染引擎
# ==========================================
def generate_pdf(roster_df, master_report_df, logo_b64=None):
    today = datetime.date.today().strftime("%Y-%m-%d")
    html_table = roster_df.to_html(classes='table')
    report_table = master_report_df[["學生姓名 (Prefect Name)", "年級 (Form)", "班別 (Class)", "職級 (Role)", "當週新增 (次)", "最終總計加權負荷 (點)"]].to_html(index=False, classes='table')
    
    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        body {{font-family: Arial, sans-serif; margin:30px; color: #333;}}
        h1 {{color:#0C2340; text-align:center; margin-bottom:5px;}}
        h2 {{color:#D4AF37; text-align:center; margin-top:0; font-size:18px; font-weight:600;}}
        h3 {{color:#0C2340; border-left: 5px solid #D4AF37; padding-left: 8px; margin-top: 30px;}}
        table {{width:100%; border-collapse:collapse; margin:15px 0; font-size:12px;}}
        th, td {{border:1px solid #BDC3C7; padding:10px; text-align:center;}}
        th {{background:#0C2340; color:white; font-weight:bold;}}
        td {{font-weight: bold;}}
    </style></head><body>
    """
    if logo_b64:
        html += f'<img src="data:image/png;base64,{logo_b64}" style="display:block;margin:0 auto;height:70px;">'
    html += f"""
    <h1>Sing Yin Secondary School</h1>
    <h2>Study Prefect Duty Roster</h2>
    <p style="text-align:center; font-size:12px; color:#666;">報告生成日期: {today}</p>
    <h3>📅 本週值班表 (Weekly Duty Roster)</h3>
    {html_table}
    <h3>📊 累積工作負荷審計表 (Workload Audit Report)</h3>
    {report_table}
    </body></html>
    """
    return HTML(string=html).write_pdf()

# ==========================================
# 8. 側邊欄維護區
# ==========================================
with st.sidebar:
    st.header("🏫 Sing Yin Secondary School")
    uploaded_logo = st.file_uploader("上傳校徽 (PNG)", type=["png"])
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()

    st.write("---")
    st.header("🗄️ 數據行政導入")
    if st.button("💡 一鍵載入 Sing Yin 官方示範數據"):
        demo_data = [
            {"name": "陳卓軒", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 12, "history_weight": 12.0, "remarks": "隊長"},
            {"name": "李浩然", "form": "F.5", "class": "5B", "role": "Assistant Head Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 10, "history_weight": 10.0, "remarks": ""},
            {"name": "張凱傑", "form": "F.4", "class": "4A", "role": "Study Prefect", "available": "MONDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 9, "history_weight": 13.5, "remarks": ""},
            {"name": "黃子軒", "form": "F.4", "class": "4B", "role": "Study Prefect", "available": "TUESDAY,WEDNESDAY,FRIDAY", "history_duties": 8, "history_weight": 12.0, "remarks": ""},
            {"name": "林俊傑", "form": "F.3", "class": "3A", "role": "Study Prefect", "available": "MONDAY,TUESDAY,THURSDAY", "history_duties": 6, "history_weight": 9.0, "remarks": "需老帶新"},
            {"name": "王偉倫", "form": "F.5", "class": "5C", "role": "Study Prefect", "available": "MONDAY,WEDNESDAY,FRIDAY", "history_duties": 7, "history_weight": 10.5, "remarks": ""},
            {"name": "劉家豪", "form": "F.4", "class": "4C", "role": "Study Prefect", "available": "TUESDAY,THURSDAY", "history_duties": 5, "history_weight": 7.5, "remarks": ""},
        ]
        st.session_state.students_df = pd.DataFrame(demo_data)
        st.success("✅ 聖言中學示範數據已載入")
        st.rerun()

    st.write("---")
    st.header("👥 在線名冊即時維護")
    edited_df = st.data_editor(
        st.session_state.students_df,
        column_config={
            "name": st.column_config.TextColumn("姓名 *", required=True),
            "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5"]),
            "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"]),
            "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
            "history_duties": st.column_config.NumberColumn("歷史累計(次)", disabled=True),
            "history_weight": st.column_config.NumberColumn("歷史累計(點)", disabled=True),
        },
        num_rows="dynamic", use_container_width=True, hide_index=True, key="main_editor"
    )
    st.session_state.students_df = edited_df

    st.write("---")
    st.header("🛑 突發請假登記")
    valid_names_list = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    leave_students = st.multiselect("勾選今日請假同學", options=valid_names_list, default=[])

# ==========================================
# 9. 主畫面控制中心
# ==========================================
st.markdown('<p class="main-title">🦅 SING YIN STUDY PREFECT ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | v8.2 終極完全體</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1.5, 1.5])
with col1:
    if st.button("🚀 生成本週全新值班表", type="primary"):
        with st.spinner("智慧排班計算中..."):
            seed = random.randint(10000, 99999)
            st.session_state.roster_df = generate_roster(st.session_state.students_df, leave_students, seed)
            st.success(f"✅ 排班完成！公平驗證碼: {seed}")

with col2:
    if st.button("🗑️ 一鍵清空本週排班", type="secondary"):
        st.session_state.show_clear_confirm = True

if st.session_state.show_clear_confirm:
    st.warning("⚠️ 確定要清除全部排班？此操作無法復原！")
    c1, c2 = st.columns(2)
    if c1.button("確定清空", type="primary"):
        st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
        st.session_state.show_clear_confirm = False
        st.rerun()
    if c2.button("取消"):
        st.session_state.show_clear_confirm = False
        st.rerun()

# 執行全域即時統計分析
typo_detected, vacuum_detected, invalid_entries, vacuum_entries, master_report_df = \
    validate_and_compute(st.session_state.roster_df, st.session_state.students_df)

with col3:
    if PDF_AVAILABLE:
        logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.logo_data else None
        try:
            pdf_bytes = generate_pdf(st.session_state.roster_df, master_report_df, logo_b64)
            st.download_button("📄 匯出 PDF 列印公告版", pdf_bytes, f"SYSS_Roster_{datetime.date.today()}.pdf", "application/pdf")
        except Exception:
            st.button("📄 PDF 引擎載入中...", disabled=True)
    else:
        st.button("💡 請在伺服器補上 packages.txt 以啟用 PDF", disabled=True)

# ==========================================
# 10. 熔斷器警告與雙軌呈現
# ==========================================
if typo_detected:
    st.markdown('<div class="danger-alert"><b>⚠️ 偵測到手動微調輸入了無效姓名，系統已暫停統計：</b><br>' + '<br>'.join(invalid_entries) + '</div>', unsafe_allow_html=True)
elif vacuum_detected:
    st.markdown('<div class="warning-alert"><b>💡 提示：存在未配對的開門空缺（若手動填寫 X 代表不開放則忽略此訊息）：</b><br>' + '<br>'.join(vacuum_entries) + '</div>', unsafe_allow_html=True)

def apply_cell_style(val, role):
    val = str(val).strip()
    if val == "X": return "color: #EF4444; font-weight: bold; text-align: center;"
    if val == "": return "background-color: #F3F4F6;"
    base = "font-weight: bold; text-align: center;"
    if "Assist" in role: return base + " background-color: #FFF8E1; color: #B45309;"
    if "Room302" in role: return base + " background-color: #D1FAE5; color: #166534;"
    if "Room303" in role: return base + " background-color: #FEE2E2; color: #991B1B;"
    if "Room202" in role: return base + " background-color: #FEF3C7; color: #854D0E;"
    return base

tab_edit, tab_view = st.tabs(["✏️ 互動手動微調模式", "🎨 聖言色彩列印預覽"])
with tab_edit:
    updated_df = st.data_editor(st.session_state.roster_df, use_container_width=True, height=270, key="roster_editor")
    st.session_state.roster_df = updated_df
with tab_view:
    st.dataframe(st.session_state.roster_df.style.apply(lambda col: [apply_cell_style(v, st.session_state.roster_df.index[i]) for i, v in enumerate(col)], axis=0), use_container_width=True, height=270)

# ==========================================
# 11. 智慧替補推薦系統 UI
# ==========================================
st.write("---")
st.subheader("🔄 突發請假？智慧替補推薦系統")
c_sub1, c_sub2 = st.columns(2)
with c_sub1:
    chosen_day = st.selectbox("請假日期", DAYS)
with c_sub2:
    chosen_role = st.selectbox("請假崗位", ROWS_ROSTER)

current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
st.text_input("目前該時段原定人員", value=current_person if current_person not in ["", "X"] else "（此時段目前無人值班/不開放）", disabled=True)

if st.button("🔍 尋找最優替補人員", type="primary"):
    sub_df, msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
    if sub_df is not None:
        st.success("📋 推薦替補名單（已過濾同日值班、年級限制，並依累積總負荷點數由低到高排序）")
        st.dataframe(sub_df, use_container_width=True, hide_index=True)
    else:
        st.warning(msg)

# ==========================================
# 12. 工作量公平性監控圖表
# ==========================================
if not master_report_df.empty and not typo_detected:
    st.write("---")
    st.subheader("📊 全體工作量公平性監控 (含累積跨週點數)")
    fig = px.bar(
        master_report_df, 
        x='學生姓名 (Prefect Name)', 
        y='最終總計加權負荷 (點)', 
        text_auto='.1f', 
        color='最終總計加權負荷 (點)',
        color_continuous_scale='YlOrBr',
        labels={'最終總計加權負荷 (點)': '總負荷 (點)'}
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Sing Yin Secondary School Study Prefect Platform | v8.2 終極完全體優化穩定版")
