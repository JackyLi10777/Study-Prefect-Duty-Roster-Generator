import streamlit as str
import pandas as pd
import random
import plotly.express as px
from io import BytesIO

# ==========================================
# 1. 網頁初始設定（UI / UX 現代金色行動端優化風）
# ==========================================
st.set_page_config(
    page_title="Study Prefect Duty Roster Platform",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<style>
    .main > div { padding-top: 1.5rem !important; }
    .main-title { color: #D4AF37; font-size: 36px; font-weight: bold; letter-spacing: 2px; margin-bottom: 0px; }
    .main-subtitle { color: #6B7280; font-size: 15px; margin-top: 0px; margin-bottom: 15px; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { width: 100% !important; height: 3.2rem !important; font-size: 15px !important; font-weight: bold !important; border-radius: 10px !important; }
    .cloud-alert { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; color: #1E40AF; }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; color: #991B1B; }
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; color: #92400E; }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 定義學校行政常數
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
# 3. Session State 記憶體狀態機安全管理
# ==========================================
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=[
        "name", "form", "class", "role", "available", 
        "history_duties", "history_weight", "remarks"
    ])

def create_blank_roster():
    return pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = create_blank_roster()

if 'last_seed' not in st.session_state:
    st.session_state.last_seed = 42

if 'show_clear_confirm' not in st.session_state:
    st.session_state.show_clear_confirm = False

# ==========================================
# 4. 高效跨週負載平衡排班演算法
# ==========================================
def generate_roster(students_df, seed=42):
    if students_df.empty:
        st.error("⚠️ 錯誤：目前學生名冊為空，請先在左側邊欄新增或導入歷史累計檔案！")
        return create_blank_roster()

    random.seed(seed)
    new_roster = create_blank_roster()
    students = students_df.to_dict('records')
    
    current_week_weights = {str(s['name']).strip(): 0.0 for s in students if s.get('name') and str(s['name']).strip() != ""}
    base_historical_weights = {}
    student_form_map = {}
    student_avail_cache = {}
    
    for s in students:
        if not s.get('name') or str(s.get('name')).strip() == "": continue
        
        name_str = str(s['name']).strip()
        student_form_map[name_str] = str(s.get('form', '')).upper().strip()
        base_historical_weights[name_str] = float(s.get('history_weight', 0.0))
        
        raw_avail = str(s.get('available', '')).upper().split(',')
        student_avail_cache[name_str] = {d.strip() for d in raw_avail if d.strip()}

    last_duty_day = {name: -2 for name in current_week_weights}

    for d_idx, day in enumerate(DAYS):
        assigned_today = set()
        
        for role in ROWS_ROSTER:
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
                    if "3" in partner_form:
                        partner_is_junior = True

            for s in students:
                if not s.get('name') or str(s.get('name')).strip() == "": continue
                name = str(s['name']).strip()
                
                if day not in student_avail_cache.get(name, set()) or name in assigned_today:
                    continue

                is_ahp = (str(s.get('role', '')).strip() == "Assistant Head Study Prefect")
                if (role.startswith('Assist') and not is_ahp) or (not role.startswith('Assist') and is_ahp):
                    continue

                form_str = student_form_map.get(name, "")
                if partner_is_junior and "3" in form_str:
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

                total_current_score = base_historical_weights.get(name, 0.0) + current_week_weights.get(name, 0.0)
                score += total_current_score * 20
                
                candidates.append((score, name, w))

            if candidates:
                candidates.sort(key=lambda x: x)
                chosen = random.choice(candidates[:min(2, len(candidates))])
                chosen_name = chosen
                chosen_w = chosen
                
                new_roster.at[role, day] = chosen_name
                assigned_today.add(chosen_name)
                current_week_weights[chosen_name] += chosen_w
                last_duty_day[chosen_name] = d_idx
            else:
                if new_roster.at[role, day] != "X":
                    new_roster.at[role, day] = ""

    return new_roster

# ==========================================
# 5. 側邊欄：歷史檔案導入與在線名冊動態維護
# ==========================================
with st.sidebar:
    st.header("💾 雲端休眠防護與歷史庫")
    
    uploaded_history = st.file_uploader("📥 導入歷史累計資料庫 (CSV/Excel)", type=["csv", "xlsx"])
    if uploaded_history is not None:
        try:
            if uploaded_history.name.endswith('.csv'):
                import_df = pd.read_csv(uploaded_history)
            else:
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
            
            st.session_state.students_df = import_df[["name", "form", "class", "role", "available", 
                                                    "history_duties", "history_weight", "remarks"]]
            st.success("✅ 成功導入歷史資料庫！數據已跨週接軌。")
        except Exception as e:
            st.error(f"檔案解析格式有誤，請確認是否為系統導出的檔案: {e}")

    st.write("---")
    st.subheader("📝 在線 Prefect 名冊管理")
    edited_df = st.data_editor(
        st.session_state.students_df,
        column_config={
            "name": st.column_config.TextColumn("姓名 *", required=True),
            "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"], required=True),
            "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
            "history_duties": st.column_config.NumberColumn("歷史舊累計(次)", disabled=True, default=0),
            "history_weight": st.column_config.NumberColumn("歷史舊累計(點)", disabled=True, default=0.0)
        },
        num_rows="dynamic", use_container_width=True, hide_index=True, key="sidebar_editor"
    )
    st.session_state.students_df = edited_df

    if st.button("💡 載入標準測試數據名冊"):
        sample_data = [
            {"name": "謝竣儒", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", "history_duties": 10, "history_weight": 10.0, "remarks": ""},
            {"name": "羅梓滔", "form": "F.5", "class": "5B", "role": "Assistant Head Study Prefect", "available": "TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 8, "history_weight": 8.0, "remarks": ""},
            {"name": "孫卓豐", "form": "F.5", "class": "5C", "role": "Assistant Head Study Prefect", "available": "WEDNESDAY,FRIDAY", "history_duties": 7, "history_weight": 7.0, "remarks": ""},
            {"name": "賀俊彥", "form": "F.4", "class": "4A", "role": "Study Prefect", "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 12, "history_weight": 18.0, "remarks": ""},
            {"name": "何梓皓", "form": "F.3", "class": "3A", "role": "Study Prefect", "available": "TUESDAY,WEDNESDAY,FRIDAY", "history_duties": 9, "history_weight": 13.5, "remarks": ""},
            {"name": "梁家健", "form": "F.4", "class": "4B", "role": "Study Prefect", "available": "TUESDAY,WEDNESDAY,THURSDAY", "history_duties": 11, "history_weight": 16.5, "remarks": ""},
            {"name": "梁晉羲", "form": "F.4", "class": "4C", "role": "Study Prefect", "available": "TUESDAY,WEDNESDAY", "history_duties": 5, "history_weight": 7.5, "remarks": ""}
        ]
        st.session_state.students_df = pd.DataFrame(sample_data)
        st.rerun()

# ==========================================
# 6. 主畫面中央控制看板
# ==========================================
st.markdown('<p class="main-title">STUDY PREFECT DUTY ROSTER</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">📅 <b>自動化智能公平排班平台 (Week of 26–27 May)</b></p>', unsafe_allow_html=True)

st.markdown("""
<div class="cloud-alert">
    <b>🛡️ 高級數據持久化提示</b>：本排班表完全支援手動覆寫更換人選。
    一旦手動更改，下方的動態加權工作量報告與 Plotly 公平性監控圖表將會在毫秒級內即時自動重算！
</div>
""", unsafe_allow_html=True)

col_btn1, col_btn2 = st.columns()
with col_btn1:
    if st.button("🚀 生成本週全新值班表", type="primary"):
        current_seed = random.randint(1, 100000)
        st.session_state.last_seed = current_seed
        st.session_state.roster_df = generate_roster(st.session_state.students_df, current_seed)
        st.session_state.show_clear_confirm = False
        st.success(f"🎉 智能排班計算完成！（隨機種子: {current_seed}）")

with col_btn2:
    if st.button("🗑️ 一鍵清空本週排班", type="secondary"):
        st.session_state.show_clear_confirm = True

# 獨立狀態機安全二階確認區：完美防閃退機制
if st.session_state.show_clear_confirm:
    st.markdown('<div class="warning-alert"><b>⚠️ 確定要全部清空本週排班表嗎？</b>此動作將擦除所有手動修改內容。</div>', unsafe_allow_html=True)
    c_col1, c_col2, _ = st.columns()
    with c_col1:
        if st.button("🛑 確定抹除", type="primary", key="real_clear_btn"):
            st.session_state.roster_df = create_blank_roster()
            st.session_state.show_clear_confirm = False
            st.rerun()
    with c_col2:
        if st.button("❌ 取消返回", key="cancel_clear_btn"):
            st.session_state.show_clear_confirm = False
            st.rerun()

# ==========================================
# 7. 顯示與修改排班表
# ==========================================
def style_roster_dataframe(df: pd.DataFrame):
    style_df = pd.DataFrame("", index=df.index, columns=df.columns)
    for row in df.index:
        for col in df.columns:
            val = str(df.at[row, col]).strip()
            if val == "X":
                style_df.at[row, col] = "color: #EF4444; font-weight: bold; text-align: center;"
                continue
            if val == "":
                style_df.at[row, col] = "background-color: #F3F4F6; text-align: center;"
                continue
            
            base_style = "font-weight: bold; text-align: center;"
            if "Assist" in row: style_df.at[row, col] = base_style + "background-color: #FFF8E1; color: #B45309;"
            elif "Room302" in row: style_df.at[row, col] = base_style + "background-color: #D1FAE5; color: #166534;"
            elif "Room303" in row: style_df.at[row, col] = base_style + "background-color: #FEE2E2; color: #991B1B;"
            elif "Room202" in row: style_df.at[row, col] = base_style + "background-color: #FEF3C7; color: #854D0E;"
    return df.style.apply(lambda _: style_df, axis=None)

tab_edit, tab_view = st.tabs(["✏️ 手動微調/修改模式 (流暢無阻)", "🎨 視覺化彩色列印面 (唯讀預覽)"])

with tab_edit:
    updated_df = st.data_editor(
        st.session_state.roster_df, use_container_width=True, height=270, key="main_roster_pure_editor"
    )
    st.session_state.roster_df = updated_df

with tab_view:
    roster_styler = style_roster_dataframe(st.session_state.roster_df)
    st.dataframe(roster_styler, use_container_width=True, height=270)

# ==========================================
# 8. 全域零信任安全防禦網 (手動錯字、真空空值雙重熔斷)
# ==========================================
valid_names = set(str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip())

typo_detected = False
vacuum_detected = False
invalid_entries = []
vacuum_entries = []

# 將當前課表轉成原生高效率字典矩陣進行高速校驗
roster_dict = st.session_state.roster_df.to_dict(orient='index')

for d in DAYS:
    for r in ROWS_ROSTER:
        val = str(roster_dict.get(r, {}).get(d, "")).strip()
        
        if val and val not in ["X", ""] and val not in valid_names:
            typo_detected = True
            invalid_entries.append(f"【{d} - {r}】輸入了未登錄名字: \"{val}\"")
        
        is_closed = (('Room202' in r and d in ['MONDAY', 'TUESDAY', 'THURSDAY', 'FRIDAY']) or 
                     (('Room302' in r or 'Room303' in r) and d in ['MONDAY', 'THURSDAY', 'FRIDAY']))
        if val == "" and not is_closed:
            vacuum_detected = True
            vacuum_entries.append(f"【{d} - {r}】目前處於無人看管真空狀態")

if typo_detected:
    st.markdown('<div class="danger-alert"><b>⚠️ 偵測到無效姓名（防呆熔斷機制已啟動）：</b><br>' + '<br>'.join(invalid_entries) + '<br><i>請修正格子內的名字，確保與左側名冊完全相同。目前點數統計已暫停，且數據匯出功能已被強制鎖定。</i></div>', unsafe_allow_html=True)

if vacuum_detected and not typo_detected:
    st.markdown('<div class="warning-alert"><b>💡 溫馨提示：目前值班表存在無人值班的空白時段：</b><br>' + '<br>'.join(vacuum_entries) + '<br><i>這不會影響點數統計，但請確認學校現場是否需要手動安排人員填補。</i></div>', unsafe_allow_html=True)

# ==========================================
# 9. 即時動態累計工作量數據整合（⚡ 核心效能優化：拉平 O(1) 字典流統計）
# ==========================================
final_records = []

# 效能躍升點：將二維矩陣提前「拉平」為純 Python 列表，僅掃描排班表一次
allocated_list = []
if not typo_detected:
    for d in DAYS:
        for r in ROWS_ROSTER:
            v = str(roster_dict.get(r, {}).get(d, "")).strip()
            if v and v not in ["X", ""]:
                allocated_list.append((v, r))

for s in st.session_state.students_df.to_dict('records'):
    if not s.get('name') or str(s.get('name')).strip() == "": continue
    name = str(s['name']).strip()
    
    # 使用純 Python 的內建高效列表推導式與計數，免除千次 Pandas 開銷
    student_duties = [role for student_name, role in allocated_list if student_name == name]
    this_week_duties = len(student_duties)
    this_week_weight = sum(WEIGHTS.get(role, 1.0) for role in student_duties)
                
    history_d = int(s.get('history_duties', 0))
    history_w = float(s.get('history_weight', 0.0))
    
    final_records.append({
        "學生姓名 (Prefect Name)": name,
        "年級 (Form)": s.get('form', ''),
        "班別 (Class)": s.get('class', ''),
        "職級 (Role)": s.get('role', ''),
        "可用日子 (Available Days)": s.get('available', ''),
        "歷史舊常規值班累計 (次)": history_d,
        "歷史舊加權負荷累計 (點)": history_w,
        "當週新常規值班次數 (次)": this_week_duties,
        "當週新加權負荷點數 (點)": round(this_week_weight, 1),
        "最終總計值班次數 (次)": history_d + this_week_duties,
        "最終總計加權負荷 (點)": round(history_w + this_week_weight, 1),
        "備註 (Remarks)": s.get('remarks', '')
    })

master_report_df = pd.DataFrame(final_records)

# ==========================================
# 10. 智慧替補候選人建議系統
# ==========================================
st.write("---")
st.subheader("🔄 臨時請假？智慧替補候選人建議")

sub_col1, sub_col2 = st.columns(2)
with sub_col1:
    chosen_day = st.selectbox("請假日期 (星期)", DAYS)
with sub_col2:
    chosen_role = st.selectbox("請假職位/房間", ROWS_ROSTER)

current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
st.text_input("目前該時段被排定的人員", value=current_person if current_person not in ["", "X"] else "（當前為空白或非開放時段）", disabled=True)

if st.button("🔍 篩選並推薦最優替補名單"):
    if current_person in ["X", ""]:
        st.warning("該時段目前不需要安排替補（未開放或本就是空缺）。")
    elif typo_detected:
        st.error("請先修正值班表中的錯字，再使用替補系統。")
    else:
        assigned_today = set()
        for r in ROWS_ROSTER:
            p = str(st.session_state.roster_df.at[r, chosen_day]).strip()
            if p and p not in ["X", ""]:
                assigned_today.add(p)
        
        is_ahp_required = chosen_role.startswith('Assist')
        sub_candidates = []
        
        partner_is_junior = False
        if "- 1" in chosen_role or "- 2" in chosen_role:
            partner_role = chosen_role.replace("- 1", "- 2") if "- 1" in chosen_role else chosen_role.replace("- 2", "- 1")
            partner_name = str(st.session_state.roster_df.at[partner_role, chosen_day]).strip()
            if partner_name and partner_name not in ["X", ""]:
                for rec in master_report_df.to_dict('records'):
                    if rec["學生姓名 (Prefect Name)"] == partner_name and "3" in str(rec["年級 (Form)"]):
                        partner_is_junior = True
        
        for rec in master_report_df.to_dict('records'):
            name = rec["學生姓名 (Prefect Name)"]
            if name == current_person or name in assigned_today:
                continue
                
            raw_avail = str(rec["可用日子 (Available Days)"]).upper().split(',')
            avail_set = {d.strip() for d in raw_avail if d.strip()}
            if chosen_day not in avail_set:
                continue
                
            is_cand_ahp = rec["職級 (Role)"] == "Assistant Head Study Prefect"
            if (is_ahp_required and not is_cand_ahp) or (not is_ahp_required and is_cand_ahp):
                continue
                
            if partner_is_junior and "3" in str(rec["年級 (Form)"]):
                continue
                
            sub_candidates.append({
                "替補學生姓名": name,
                "年級": rec["年級 (Form)"],
                "班別": rec["班別 (Class)"],
                "當前累計總加權負荷 (點)": rec["最終總計加權負荷 (點)"]
            })
            
        if sub_candidates:
            sub_df = pd.DataFrame(sub_candidates).sort_values(by="當前累計總加權負荷 (點)")
            st.success(f"📋 依據『時間可用、職級相符、老帶新控場、歷史總工作量最輕』排名的最優替補：")
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
        else:
            st.error("❌ 遺憾！在名冊中找不到任何同時符合『當天有空、職級正確、且當天未被排班』的合法替補人員。")

# ==========================================
# 11. 備份資料庫導出區
# ==========================================
if not master_report_df.empty:
    st.write("---")
    st.subheader("💾 歷史累計資料庫中介導出（修眠救援備份）")
    
    if typo_detected:
        st.button("❌ 鎖定中：請先修正上方的無效姓名紅字警告，才能解鎖導出功能", disabled=True)
    else:
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            master_report_df.to_excel(writer, sheet_name="累計值班數據歷史庫", index=False, startrow=4)
            ws = writer.sheets["累計值班數據歷史庫"]
            ws["A1"] = "Study Prefect Duty Roster - 歷史累計工作負荷資料庫檔案"
            ws["A2"] = "【重要說明】此檔案專為解決 Streamlit Cloud 休眠重置問題設計。請妥善保存，於系統重啟時重新上傳即可還原並累計歷史工作量。"
            
        st.download_button(
            label="📥 點此導出本週累計歷史資料庫檔案 (Excel .xlsx)",
            data=output_excel.getvalue(),
            file_name="Study_Prefect_Cumulative_Database.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # ==========================================
    # 12. 歷史總負荷分布監控統計圖表
    # ==========================================
    st.write("---")
    st.subheader("📊 跨週歷史總計工作負荷（演算法依據此總負載自動進行公平化微調）")
    fig = px.bar(
        master_report_df,
        x='學生姓名 (Prefect Name)',
        y='最終總計加權負荷 (點)',
        color='最終總計加權負荷 (點)',
        text_auto='.1f',
        color_continuous_scale='gold',
        labels={'最終總計加權負荷 (點)': '歷年總累計負荷點數'}
    )
    fig.update_layout(
        height=340,
        margin=dict(l=20, r=20, t=10, b=10), 
        xaxis_title="Prefect 姓名", 
        coloraxis_showscale=False
    )
    st.plotly_chart(fig, use_container_width=True)
