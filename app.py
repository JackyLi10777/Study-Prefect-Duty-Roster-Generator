import streamlit as st
import pandas as pd
import random
import plotly.express as px
from io import BytesIO

# ==========================================
# 1. 網頁初始設定（需為第一個執行的 Streamlit 指令）
# ==========================================
st.set_page_config(
    page_title="SYSS Study Prefect Duty Platform",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<style>
    .main > div { padding-top: 1.5rem !important; }
    .main-title { color: #0C2340; font-size: 34px; font-weight: bold; letter-spacing: 1px; margin-bottom: 0px; }
    .main-subtitle { color: #D4AF37; font-size: 15px; margin-top: 0px; margin-bottom: 15px; font-weight: 600; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { width: 100% !important; height: 3.2rem !important; font-size: 15px !important; font-weight: bold !important; border-radius: 10px !important; }
    .cloud-alert { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; color: #1E40AF; }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; color: #991B1B; }
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; color: #92400E; }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 定義學校行政常數與權重
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
# 3. Session State 安全管理與強固初始化
# ==========================================
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=[
        "name", "form", "class", "role", "available", 
        "history_duties", "history_weight", "remarks"
    ])

def create_blank_roster():
    return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("").astype(str)

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = create_blank_roster()

if 'show_clear_confirm' not in st.session_state:
    st.session_state.show_clear_confirm = False

# ==========================================
# 4. 高階排班演算法 (積分制 + 老帶新 + 全天請假排除)
# ==========================================
def generate_roster(students_df, leave_students, seed):
    if students_df.empty:
        st.error("⚠️ 錯誤：目前學生名冊為空，請先在左側邊欄新增或導入歷史檔案！")
        return create_blank_roster()

    random.seed(seed)
    new_roster = create_blank_roster()
    students = students_df.to_dict('records')
    
    current_week_weights = {str(s['name']).strip(): 0.0 for s in students if str(s.get('name')).strip()}
    base_historical_weights = {}
    student_form_map = {}
    student_avail_cache = {}
    
    for s in students:
        name_str = str(s.get('name', '')).strip()
        if not name_str: continue
        
        student_form_map[name_str] = str(s.get('form', '')).upper().strip()
        base_historical_weights[name_str] = float(s.get('history_weight', 0.0))
        raw_avail = str(s.get('available', '')).upper().split(',')
        student_avail_cache[name_str] = {d.strip() for d in raw_avail if d.strip()}

    last_duty_day = {name: -2 for name in current_week_weights}

    for d_idx, day in enumerate(DAYS):
        assigned_today = set()
        
        today_roles = list(ROWS_ROSTER)
        random.shuffle(today_roles)
        today_roles.sort(key=lambda x: 1 if "- 2" in x else 0)

        for role in today_roles:
            if 'Room202' in role and day in ['MONDAY', 'TUESDAY', 'THURSDAY', 'FRIDAY']:
                new_roster.at[role, day] = "X"
                continue
            if ('Room302' in role or 'Room303' in role) and day in ['MONDAY', 'THURSDAY', 'FRIDAY']:
                new_roster.at[role, day] = "X"
                continue

            candidates = []
            partner_is_junior = False
            
            if "- 2" in role:
                partner_role = role.replace("- 2", "- 1")
                partner_name = str(new_roster.at[partner_role, day]).strip()
                if partner_name and partner_name not in ["X", ""]:
                    partner_form = student_form_map.get(partner_name, "")
                    if "1" in partner_form or "2" in partner_form or "3" in partner_form:
                        partner_is_junior = True

            for s in students:
                name = str(s.get('name', '')).strip()
                if not name or name in leave_students: continue
                
                if day not in student_avail_cache.get(name, set()) or name in assigned_today:
                    continue

                is_ahp = (str(s.get('role', '')).strip() == "Assistant Head Study Prefect")
                if (role.startswith('Assist') and not is_ahp) or (not role.startswith('Assist') and is_ahp):
                    continue

                form_str = student_form_map.get(name, "")
                if partner_is_junior and any(x in form_str for x in ["1", "2", "3"]):
                    continue 

                score = 0
                w = WEIGHTS[role]

                if last_duty_day.get(name, -2) == d_idx - 1: score += 1000
                if current_week_weights.get(name, 0.0) + w > 3.0: score += 800

                is_senior = any(x in form_str for x in ["4", "5", "6", "SENIOR"])
                if 'Room302' in role:
                    score += 40 if is_senior else -40
                elif 'Room303' in role or 'Room202' in role:
                    score += -40 if is_senior else 40

                total_current_score = round(base_historical_weights.get(name, 0.0) + current_week_weights.get(name, 0.0), 2)
                score += total_current_score * 20
                
                candidates.append((score, name, w))

            if candidates:
                candidates.sort(key=lambda x: x[0])
                chosen = random.choice(candidates[:min(2, len(candidates))])
                chosen_name = chosen[1]
                chosen_w = chosen[2]
                
                new_roster.at[role, day] = chosen_name
                assigned_today.add(chosen_name)
                current_week_weights[chosen_name] += chosen_w
                last_duty_day[chosen_name] = d_idx
            else:
                if new_roster.at[role, day] != "X":
                    new_roster.at[role, day] = ""

    return new_roster

# ==========================================
# 5. 側邊欄：歷史檔案與名冊管理
# ==========================================
with st.sidebar:
    st.header("🗄️ 跨週數據備份區")
    
    # 【新增功能】一鍵載入高畫質行政示範數據
    if st.button("💡 一鍵載入行政示範數據", type="secondary"):
        demo_prefects = [
            {"name": "Alice Chan", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 5, "history_weight": 5.0, "remarks": "隊長/經驗豐富"},
            {"name": "Bob Wong", "form": "F.6", "class": "6B", "role": "Assistant Head Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 4, "history_weight": 4.5, "remarks": "副隊長"},
            {"name": "Charlie Li", "form": "F.4", "class": "4C", "role": "Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 3, "history_weight": 4.0, "remarks": ""},
            {"name": "David Cheung", "form": "F.3", "class": "3A", "role": "Study Prefect", "available": "MONDAY,WEDNESDAY,FRIDAY", "history_duties": 2, "history_weight": 3.0, "remarks": "初中/週二四補習"},
            {"name": "Eva Lau", "form": "F.1", "class": "1B", "role": "Study Prefect", "available": "TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 0, "history_weight": 0.0, "remarks": "新人/需老帶新"},
            {"name": "Frank Ho", "form": "F.2", "class": "2C", "role": "Study Prefect", "available": "MONDAY,TUESDAY,FRIDAY", "history_duties": 1, "history_weight": 1.5, "remarks": "初中"},
            {"name": "Grace Ng", "form": "F.5", "class": "5B", "role": "Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 2, "history_weight": 2.5, "remarks": ""},
            {"name": "Henry Mak", "form": "F.6", "class": "6A", "role": "Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 3, "history_weight": 3.5, "remarks": "即將畢業"},
            {"name": "Ivy Tsang", "form": "F.4", "class": "4A", "role": "Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 2, "history_weight": 2.5, "remarks": ""},
            {"name": "Jack Lam", "form": "F.2", "class": "2D", "role": "Study Prefect", "available": "TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 1, "history_weight": 1.5, "remarks": "初中"}
        ]
        st.session_state.students_df = pd.DataFrame(demo_prefects)
        st.success("🎉 示範名冊載入成功！請至右側點擊『啟動演算』觀看排班效果。")
        st.rerun()

    uploaded_history = st.file_uploader("📥 導入歷史累計資料庫 (Excel)", type=["xlsx"])
    if uploaded_history is not None:
        file_id = uploaded_history.name + str(uploaded_history.size)
        if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != file_id:
            try:
                import_df = pd.read_excel(uploaded_history, skiprows=4)
                if "學生姓名 (Prefect Name)" in import_df.columns:
                    import_df = import_df.rename(columns={
                        "學生姓名 (Prefect Name)": "name", "年級 (Form)": "form", "班別 (Class)": "class",
                        "職級 (Role)": "role", "可用日子 (Available Days)": "available",
                        "最終總計值班次數 (次)": "history_duties", "最終總計加權負荷 (點)": "history_weight"
                    })
                
                for col, default in [("history_duties", 0), ("history_weight", 0.0), ("remarks", "")]:
                    if col not in import_df.columns: import_df[col] = default
                
                import_df["history_duties"] = pd.to_numeric(import_df["history_duties"], errors='coerce').fillna(0).astype(int)
                import_df["history_weight"] = pd.to_numeric(import_df["history_weight"], errors='coerce').fillna(0.0).astype(float)
                
                st.session_state.students_df = import_df[["name", "form", "class", "role", "available", "history_duties", "history_weight", "remarks"]]
                st.session_state.last_uploaded_file = file_id
                st.success("✅ 成功導入歷史資料，數據已跨週接軌。")
            except Exception as e:
                st.error("❌ 檔案解析有誤。")

    st.write("---")
    st.header("👥 在線名冊與請假維護")
    edited_df = st.data_editor(
        st.session_state.students_df,
        column_config={
            "name": st.column_config.TextColumn("姓名 *", required=True),
            "form": st.column_config.SelectboxColumn("年級", options=["F.1", "F.2", "F.3", "F.4", "F.5", "F.6"]),
            "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"], required=True),
            "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
            "history_duties": st.column_config.NumberColumn("歷史累計(次)", disabled=True),
            "history_weight": st.column_config.NumberColumn("歷史累計(點)", disabled=True)
        },
        num_rows="dynamic", use_container_width=True, hide_index=True, key="sidebar_editor"
    )
    st.session_state.students_df = edited_df

    valid_names_list = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    
    st.write("---")
    st.header("🛑 突發請假名單")
    leave_students = st.multiselect("若排班前已知全天請假，請勾選：", options=valid_names_list, default=[])

# ==========================================
# 6. 主畫面：排班操作與防護網
# ==========================================
st.markdown('<p class="main-title">🦅 SYSS STUDY PREFECT ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">智慧公平排班平台 ｜ v5.4 智能示範版</p>', unsafe_allow_html=True)

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🚀 啟動演算：生成本週值班表", type="primary"):
        current_seed = random.randint(10000, 99999)
        st.session_state.roster_df = generate_roster(st.session_state.students_df, leave_students, current_seed)
        st.session_state.show_clear_confirm = False
        st.success(f"🎉 智能排班計算完成！(公平驗證種子碼: {current_seed})")
with col_btn2:
    if st.button("🗑️ 一鍵清空", type="secondary"):
        st.session_state.show_clear_confirm = True

if st.session_state.show_clear_confirm:
    st.markdown('<div class="warning-alert"><b>⚠️ 確定要抹除全部資料嗎？</b></div>', unsafe_allow_html=True)
    c1, c2, _ = st.columns(3)
    if c1.button("🛑 確定抹除", type="primary"):
        st.session_state.roster_df = create_blank_roster()
        st.session_state.show_clear_confirm = False
        st.rerun()
    if c2.button("❌ 取消返回"):
        st.session_state.show_clear_confirm = False
        st.rerun()

# ==========================================
# 7. UI 雙模式切換 (編輯 vs 列印彩繪)
# ==========================================
def style_roster(df):
    style_df = pd.DataFrame("", index=df.index, columns=df.columns)
    for r in df.index:
        for c in df.columns:
            v = str(df.at[r, c]).strip()
            if v == "X":
                style_df.at[r, c] = "color: #EF4444; font-weight: bold; text-align: center;"
            elif v == "":
                style_df.at[r, c] = "background-color: #F3F4F6; text-align: center;"
            else:
                base = "font-weight: bold; text-align: center;"
                if "Assist" in r: style_df.at[r, c] = base + "background-color: #FFF8E1; color: #B45309;"
                elif "Room302" in r: style_df.at[r, c] = base + "background-color: #D1FAE5; color: #166534;"
                elif "Room303" in r: style_df.at[r, c] = base + "background-color: #FEE2E2; color: #991B1B;"
                elif "Room202" in r: style_df.at[r, c] = base + "background-color: #FEF3C7; color: #854D0E;"
    return df.style.apply(lambda _: style_df, axis=None)

tab_edit, tab_view = st.tabs(["✏️ 互動微調模式", "🎨 彩色列印預覽"])

with tab_edit:
    updated_df = st.data_editor(st.session_state.roster_df, use_container_width=True, height=270)
    st.session_state.roster_df = updated_df
with tab_view:
    st.dataframe(style_roster(st.session_state.roster_df), use_container_width=True, height=270)

# ==========================================
# 8. 全域錯字與空值熔斷器
# ==========================================
valid_names = set(valid_names_list)
roster_dict = st.session_state.roster_df.to_dict(orient='index')

typo_detected, vacuum_detected = False, False
invalid_entries, vacuum_entries = [], []

for d in DAYS:
    for r in ROWS_ROSTER:
        val = str(roster_dict.get(r, {}).get(d, "")).strip()
        if val and val not in ["X", ""] and val not in valid_names:
            typo_detected = True
            invalid_entries.append(f"【{d} - {r}】: {val}")
        
        is_closed = (('Room202' in r and d in ['MONDAY', 'TUESDAY', 'THURSDAY', 'FRIDAY']) or 
                     (('Room302' in r or 'Room303' in r) and d in ['MONDAY', 'THURSDAY', 'FRIDAY']))
        if val == "" and not is_closed:
            vacuum_detected = True
            vacuum_entries.append(f"【{d} - {r}】")

if typo_detected:
    st.markdown('<div class="danger-alert"><b>⚠️ 偵測到無效姓名，請核對左側名冊：</b><br>' + '<br>'.join(invalid_entries) + '</div>', unsafe_allow_html=True)
elif vacuum_detected:
    st.markdown('<div class="warning-alert"><b>💡 提示：存在空白崗位：</b><br>' + '<br>'.join(vacuum_entries) + '</div>', unsafe_allow_html=True)

# ==========================================
# 9. 高效流線化統計計算
# ==========================================
final_records = []
allocated_list = [(str(roster_dict.get(r, {}).get(d, "")).strip(), r) for d in DAYS for r in ROWS_ROSTER if str(roster_dict.get(r, {}).get(d, "")).strip() not in ["", "X"]]

if not typo_detected:
    for s in st.session_state.students_df.to_dict('records'):
        name = str(s.get('name', '')).strip()
        if not name: continue
        
        student_duties = [role for n, role in allocated_list if n == name]
        this_w = sum(WEIGHTS.get(role, 1.0) for role in student_duties)
        
        hist_d = int(s.get('history_duties', 0))
        hist_w = float(s.get('history_weight', 0.0))
        
        final_records.append({
            "學生姓名 (Prefect Name)": name, "年級 (Form)": s.get('form', ''), "班別 (Class)": s.get('class', ''),
            "職級 (Role)": s.get('role', ''), "可用日子 (Available Days)": s.get('available', ''),
            "歷史累計 (次)": hist_d, "歷史累計 (點)": hist_w,
            "當週新增 (次)": len(student_duties), "當週新增 (點)": round(this_w, 2),
            "最終總計值班次數 (次)": hist_d + len(student_duties), "最終總計加權負荷 (點)": round(hist_w + this_w, 2)
        })

master_report_df = pd.DataFrame(final_records)

# ==========================================
# 10. 智慧替補系統 (救火隊長功能)
# ==========================================
st.write("---")
st.subheader("🔄 突發請假？智慧替補推薦系統")
c_sub1, c_sub2 = st.columns(2)
with c_sub1: chosen_day = st.selectbox("請假星期", DAYS)
with c_sub2: chosen_role = st.selectbox("請假崗位", ROWS_ROSTER)

current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
st.text_input("該崗位原定人員", value=current_person if current_person not in ["", "X"] else "（無人）", disabled=True)

if st.button("🔍 尋找最優替補"):
    if typo_detected: st.error("請先修正表格紅字。")
    elif current_person in ["", "X"]: st.warning("該時段無需替補。")
    else:
        assigned_today = {str(st.session_state.roster_df.at[r, chosen_day]).strip() for r in ROWS_ROSTER if str(st.session_state.roster_df.at[r, chosen_day]).strip() not in ["", "X"]}
        is_ahp_req = chosen_role.startswith('Assist')
        
        subs = []
        for rec in master_report_df.to_dict('records'):
            name = rec["學生姓名 (Prefect Name)"]
            if name == current_person or name in assigned_today or chosen_day not in str(rec["可用日子 (Available Days)"]).upper(): continue
            if (is_ahp_req and rec["職級 (Role)"] != "Assistant Head Study Prefect") or (not is_ahp_req and rec["職級 (Role)"] == "Assistant Head Study Prefect"): continue
            
            subs.append({"姓名": name, "年級": rec["年級 (Form)"], "當前總點數": rec["最終總計加權負荷 (點)"]})
            
        if subs:
            sub_df = pd.DataFrame(subs).sort_values(by="當前總點數")
            st.success("📋 依總點數 (最少優先) 推薦之合格替補：")
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
        else: st.error("❌ 找不到合適的替補人員。")

# ==========================================
# 11. 數據匯出與圖表
# ==========================================
if not master_report_df.empty:
    st.write("---")
    c_out1, c_out2 = st.columns([7, 3])
    with c_out1:
        st.plotly_chart(px.bar(master_report_df, x='學生姓名 (Prefect Name)', y='最終總計加權負荷 (點)', text_auto='.2f', title="全體累積工作點數監控", color='最終總計加權負荷 (點)', color_continuous_scale='gold'), use_container_width=True)
    with c_out2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if not typo_detected:
            out_xl = BytesIO()
            with pd.ExcelWriter(out_xl, engine='openpyxl') as writer:
                master_report_df.to_excel(writer, sheet_name="累計數據", index=False, startrow=4)
            st.download_button("📥 導出跨週存檔 Excel", data=out_xl.getvalue(), file_name="SYSS_Roster_Backup.xlsx", use_container_width=True)
