import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
from io import BytesIO
import datetime

# PDF 支援
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False

# ==========================================
# 1. 網頁設定
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
    .stButton > button { height: 3.2rem; font-weight: bold; border-radius: 10px; }
    .alert { padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B; }
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; color: #92400E; }
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
WEIGHTS = {row: 1.0 if 'Room302' in row or 'Assist' in row else 1.5 for row in ROWS_ROSTER}

# ==========================================
# 3. Session State
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
# 4. 核心排班演算法
# ==========================================
def generate_roster(students_df: pd.DataFrame, leave_students: list, seed: int) -> pd.DataFrame:
    if students_df.empty or students_df['name'].str.strip().eq('').all():
        st.error("⚠️ 學生名冊為空，請先在側邊欄新增或導入資料！")
        return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

    rng = random.Random(seed)
    new_roster = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

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
        for role in ROWS_ROSTER:
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
# 5. 驗證與統計（快取）
# ==========================================
@st.cache_data(ttl=5)
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

    _, _, _, _, master_df = validate_and_compute(roster_df, students_df)
    student_lookup = {row["學生姓名 (Prefect Name)"]: row for _, row in master_df.iterrows()}

    assigned_today = {str(roster_df.at[r, chosen_day]).strip() 
                     for r in ROWS_ROSTER if str(roster_df.at[r, chosen_day]).strip() not in ["", "X"]}

    is_ahp_required = chosen_role.startswith('Assist')
    partner_is_junior = False

    if "- 2" in chosen_role or "- 1" in chosen_role:
        partner_role = chosen_role.replace("- 2", "- 1") if "- 2" in chosen_role else chosen_role.replace("- 1", "- 2")
        partner_name = str(roster_df.at[partner_role, chosen_day]).strip()
        if partner_name not in ["", "X"]:
            p_rec = student_lookup.get(partner_name)
            if p_rec and "3" in str(p_rec.get("年級 (Form)", "")):
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
# 7. 側邊欄
# ==========================================
with st.sidebar:
    st.header("🏫 Sing Yin Secondary School")
    uploaded_logo = st.file_uploader("上傳校徽 (PNG)", type=["png"])
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()

    st.write("---")
    st.header("🗄️ 數據導入")
    if st.button("💡 一鍵載入 Sing Yin 示範數據"):
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
        st.success("✅ Sing Yin 示範數據已載入")
        st.rerun()

    st.write("---")
    st.header("👥 在線名冊編輯")
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
        num_rows="dynamic", use_container_width=True, hide_index=True
    )
    st.session_state.students_df = edited_df

    st.write("---")
    st.header("🛑 突發請假名單")
    valid_names_list = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    leave_students = st.multiselect("全天請假同學", options=valid_names_list, default=[])

# ==========================================
# 主畫面
# ==========================================
st.markdown('<p class="main-title">🦅 SING YIN STUDY PREFECT ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1.5, 1.5])
with col1:
    if st.button("🚀 生成本週全新值班表", type="primary"):
        with st.spinner("智慧排班計算中..."):
            seed = random.randint(10000, 99999)
            st.session_state.roster_df = generate_roster(st.session_state.students_df, leave_students, seed)
            st.success(f"✅ 排班完成！種子碼: {seed}")

with col2:
    if st.button("🗑️ 一鍵清空本週排班", type="secondary"):
        st.session_state.show_clear_confirm = True

if st.session_state.show_clear_confirm:
    st.warning("⚠️ 確定要清除全部排班？此操作無法復原！")
    c1, c2 = st.columns(2)
    if c1.button("確定清空"):
        st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
        st.session_state.show_clear_confirm = False
        st.rerun()
    if c2.button("取消"):
        st.session_state.show_clear_confirm = False
        st.rerun()

with col3:
    if st.button("📄 匯出 PDF 列印版", type="primary"):
        typo, _, _, _, master_df = validate_and_compute(st.session_state.roster_df, st.session_state.students_df)
        if typo:
            st.error("請先修正姓名錯誤")
        elif PDF_AVAILABLE:
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.logo_data else None
            pdf_bytes = generate_pdf(st.session_state.roster_df, master_df, logo_b64)
            st.download_button("💾 下載 PDF", pdf_bytes, f"SingYin_Roster_{datetime.date.today()}.pdf", "application/pdf")
        else:
            st.info("PDF 功能需 weasyprint 支援")

# ==========================================
# Tabs + 驗證 + 完整替補系統
# ==========================================
typo_detected, vacuum_detected, invalid_entries, vacuum_entries, master_report_df = \
    validate_and_compute(st.session_state.roster_df, st.session_state.students_df)

if typo_detected:
    st.markdown(f'<div class="danger-alert"><b>⚠️ 偵測到無效姓名：</b><br>' + '<br>'.join(invalid_entries) + '</div>', unsafe_allow_html=True)
elif vacuum_detected:
    st.markdown(f'<div class="warning-alert"><b>💡 存在未排班的開放時段：</b><br>' + '<br>'.join(vacuum_entries) + '</div>', unsafe_allow_html=True)

tab_edit, tab_view = st.tabs(["✏️ 互動微調模式", "🎨 彩色列印預覽"])
with tab_edit:
    updated_df = st.data_editor(st.session_state.roster_df, use_container_width=True, height=320)
    st.session_state.roster_df = updated_df
with tab_view:
    st.dataframe(st.session_state.roster_df.style.apply(lambda col: ["color: #EF4444; font-weight: bold;" if v == "X" else "" for v in col], axis=0), use_container_width=True, height=320)

# 完整智慧替補系統
st.write("---")
st.subheader("🔄 突發請假？智慧替補推薦系統")
c_sub1, c_sub2 = st.columns(2)
with c_sub1:
    chosen_day = st.selectbox("請假日期", DAYS, key="sub_day")
with c_sub2:
    chosen_role = st.selectbox("請假崗位", ROWS_ROSTER, key="sub_role")

current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
st.text_input("目前該時段人員", value=current_person if current_person not in ["", "X"] else "（無人）", disabled=True)

if st.button("🔍 尋找最優替補", type="primary"):
    sub_df, msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
    if sub_df is not None:
        st.success("📋 推薦替補名單（按總負荷由低到高排序）")
        st.dataframe(sub_df, use_container_width=True, hide_index=True)
    else:
        st.warning(msg)

# 圖表與匯出
if not master_report_df.empty:
    st.write("---")
    st.subheader("📊 全體工作量公平性監控")
    fig = px.bar(master_report_df, x='學生姓名 (Prefect Name)', y='最終總計加權負荷 (點)', text_auto='.1f', color_continuous_scale='YlOrBr')
    st.plotly_chart(fig, use_container_width=True)

st.caption("Sing Yin Secondary School Study Prefect Platform | v8.1 最終完整版")
