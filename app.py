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
    # 強制轉換為字串型別，避免後續寫入引發 Pandas FutureWarning
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
        
        # 決定當天崗位順序，打亂增加隨機性，但確保 -1 在 -2 前面以利判斷
        today_roles = list(ROWS_ROSTER)
        random.shuffle(today_roles)
        today_roles.sort(key=lambda x: 1 if "- 2" in x else 0)

        for role in today_roles:
            # 關閉特定時段
            if 'Room202' in role and day in ['MONDAY', 'TUESDAY', 'THURSDAY', 'FRIDAY']:
                new_roster.at[role, day] = "X"
                continue
            if ('Room302' in role or 'Room303' in role) and day in ['MONDAY', 'THURSDAY', 'FRIDAY']:
                new_roster.at[role, day] = "X"
                continue

            candidates = []
            partner_is_junior = False
            
            # 老帶新檢查：如果我是位子2，去查位子1是不是初中生
            if "- 2" in role:
                partner_role = role.replace("- 2", "- 1")
                partner_name = str(new_roster.at[partner_role, day]).strip()
                if partner_name and partner_name not in ["X", ""]:
                    partner_form = student_form_map.get(partner_name, "")
                    if "1" in partner_form or "2" in partner_form or "3" in partner_form:
                        partner_is_junior = True

            for s in students:
                name = str(s.get('name', '')).strip()
                # 核心業務邏輯：過濾掉空名字與「全天請假名單」中的學生
                if not name or name in leave_students: continue
                
                if day not in student_avail_cache.get(name, set()) or name in assigned_today:
                    continue

                is_ahp = (str(s.get('role', '')).strip() == "Assistant Head Study Prefect")
                if (role.startswith('Assist') and not is_ahp) or (not role.startswith('Assist') and is_ahp):
                    continue

                form_str = student_form_map.get(name, "")
                # 老帶新防護網觸發
                if partner_is_junior and any(x in form_str for x in ["1", "2", "3"]):
                    continue 

                # 積分計算系統 (分數越低越優先排班)
                score = 0
                w = WEIGHTS[role]

                # 連續疲勞懲罰與本週負荷懲罰
                if last_duty_day.get(name, -2) == d_idx - 1: score += 1000
                if current_week_weights.get(name, 0.0) + w > 3.0: score += 800

                # 任務適配性 (高年級優先去管教低年級，低年級去自修室)
                is_senior = any(x in form_str for x in ["4", "5", "6", "SENIOR"])
                if 'Room302' in role:
                    score += 40 if is_senior else -40
                elif 'Room303' in role or 'Room202' in role:
                    score += -40 if is_senior else 40

                # 歷史累積點數權重化 (核心公平機制)
                total_current_score = round(base_historical_weights.get(name, 0.0) + current_week_weights.get(name, 0.0), 2)
                score += total_current_score * 20
                
                candidates.append((score, name, w))

            if candidates:
                candidates.sort(key=lambda x: x[0])
                # 從最低分的前兩名隨機挑一個
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
# 5. 側邊欄：歷史檔案與名冊管理 (含快取鎖定防呆)
# ==========================================
with st.sidebar:
    st.header("🗄️ 跨週數據備份區")
    
    uploaded_history = st.file_uploader("📥 導入歷史累計資料庫 (Excel)", type=["xlsx"])
    # 快取鎖定機制：防止 Streamlit rerun 時不斷覆蓋手動編輯的數據
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
            "history_weight": st.column_config.NumberColumn("歷史累計
