import streamlit as st
import pandas as pd
import random
from io import BytesIO

# ==========================================
# 1. 網頁初始設定（行動端高度優化）
# ==========================================
st.set_page_config(
    page_title="Study Prefect Duty Roster Generator",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS 優化手機體驗：去除頂部空白、放大按鈕、確保表格在手機端不嚴重變形
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <link rel="manifest" href="data:application/manifest+json;base64,eyJuYW1lIjoiU3R1ZHkgUHJlZmVjdCIsInNob3J0X25hbWUiOiJQcmVmZWN0IiwiZGlzcGxheSI6InN0YW5kYWxvbmUiLCJzdWFydF91cmwiOiIuLyJ9">
    <style>
        .main > div { padding-top: 1rem !important; }
        .stButton > button {
            width: 100% !important;
            height: 3.4rem !important;
            font-size: 16px !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
        }
        [data-testid="stDataEditor"] { min-width: 320px !important; }
        footer {visibility: hidden;}
        h1, h2, h3 { color: #1E3A8A; }
    </style>
""", unsafe_allow_html=True)

# 定義常數（縱軸為天，橫軸為職位名額）
DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
COLUMNS_ROSTER = [
    'Assist. in charge',
    'Room 302',
    'Room 303 (Prefect 1)', 'Room 303 (Prefect 2)',
    'Room 202 (Prefect 1)', 'Room 202 (Prefect 2)'
]

# 負荷計分權重
WEIGHTS = {
    'Assist. in charge': 1.0,
    'Room 302': 1.5,
    'Room 303 (Prefect 1)': 1.0, 'Room 303 (Prefect 2)': 1.0,
    'Room 202 (Prefect 1)': 1.0, 'Room 202 (Prefect 2)': 1.0
}

# ==========================================
# 2. 建立下載範本功能（utf-8-sig 防止 Excel 亂碼）
# ==========================================
def get_template_csv():
    template_df = pd.DataFrame([
        {"name": "張大明", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "available": "Mon,Tue,Wed", "remarks": "偏好 Room 303"},
        {"name": "陳小華", "form": "F.4", "class": "4B", "role": "Study Prefect", "available": "Mon,Wed,Thu,Fri", "remarks": ""}
    ])
    return template_df.to_csv(index=False).encode('utf-8-sig')

# ==========================================
# 3. Session State 狀態管理
# ==========================================
# 依據需求：不提供任何預設名單，完全由使用者建立
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=["name", "form", "class", "role", "available", "remarks"])

def create_blank_roster():
    # 建立以 DAYS 為索引，職位為欄位的空白值班表
    df = pd.DataFrame(index=DAYS, columns=COLUMNS_ROSTER).fillna("")
    # 依據需求：Room 202 僅週一、三、四開放，週二、五常規不開放 -> 留空白
    # 這裡的空白在演算法中會被跳過，保持乾淨
    return df

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = create_blank_roster()

# ==========================================
# 4. 核心排班演算法（縱軸為天優化版）
# ==========================================
def generate_roster(students_df):
    if students_df.empty:
        st.error("⚠️ 錯誤：目前學生名單為空，請先在左側邊欄新增或上傳名單！")
        return create_blank_roster()

    # 每次點擊重新生成時，皆建立全新的表，徹底避免權重累加錯誤
    new_roster = create_blank_roster()
    students = students_df.to_dict('records')
    
    # 初始化每位學生的加權負荷與上一次當值日
    weekly_weights = {str(s['name']).strip(): 0.0 for s in students if pd.notna(s['name'])}
    last_duty_day = {str(s['name']).strip(): -2 for s in students if pd.notna(s['name'])}
    
    # 按天、按職位進行排班
    for d_idx, day in enumerate(DAYS):
        assigned_today = set()  # 確保一般 Study Prefect 一天最多只能安排 1 個職位
        
        for role in COLUMNS_ROSTER:
            # 依據需求規則：Room 202 僅週一、三、四開放（週二、五常規不開放 $\rightarrow$ 保持留白）
            if 'Room 202' in role and day in ['Tue', 'Fri']:
                continue
                
            candidates = []
            for s in students:
                if pd.isna(s['name']) or str(s['name']).strip() == "":
                    continue
                name = str(s['name']).strip()
                
                # 解析空閒日子 (支援多選 List 或 CSV 字串)
                avail_val = s['available']
                if isinstance(avail_val, list):
                    avail = [str(d).strip() for d in avail_val]
                else:
                    avail = [d.strip() for d in str(avail_val).split(',') if d.strip()]

                # 1. 基本限制：必須在該學生 available 的日子 + 今天還沒排過
                if day not in avail or name in assigned_today:
                    continue
                
                # 2. 身份排他性限制：Assistant Head 只能排 Assist. in charge，一般 Prefect 不能排該職位
                is_ahp = (str(s['role']).strip() == "Assistant Head Study Prefect")
                if (role == 'Assist. in charge' and not is_ahp) or \
                   (role != 'Assist. in charge' and is_ahp):
                    continue

                # 3. 軟性分數計算 (分數越低越優先)
                score = 0
                w = WEIGHTS[role]

                # 限制：避免連續兩天值班（至少間隔一天）
                if last_duty_day[name] == d_idx - 1:
                    score += 1000
                
                # 限制：每週加權上限最多 3 次 (3.0)
                if weekly_weights[name] + w > 3.0:
                    score += 800
                
                # 年級優先權：高年級優先排 Room 303/202，低年級優先排 Room 302
                form_str = str(s.get('form', '')).upper().strip()
                is_senior = any(x in form_str for x in ["4", "5", "6", "SENIOR"])
                
                if role == 'Room 302':
                    score += 30 if is_senior else -30
                elif 'Room 303' in role or 'Room 202' in role:
                    score += -30 if is_senior else 30

                # 公平分配：加計目前已累積的負荷權重
                score += weekly_weights[name] * 20

                candidates.append((score, name))

            # 智慧隨機池機制挑選
            if candidates:
                candidates.sort(key=lambda x: x[0])
                best_score = candidates[0][0]
                best_group = [c for c in candidates if c[0] <= best_score + 15]
                chosen_name = random.choice(best_group)[1]
                
                # 寫入值班表並更新後台狀態
                new_roster.at[day, role] = chosen_name
                assigned_today.add(chosen_name)
                weekly_weights[chosen_name] += w
                last_duty_day[chosen_name] = d_idx

    return new_roster

# ==========================================
# 5. 智慧替補機制（依現有負荷由低到高精準推薦）
# ==========================================
def get_optimized_substitutes(day, role, absentee, students_df, current_roster):
    if students_df.empty: 
        return pd.DataFrame()
        
    students = students_df.to_dict('records')
    # 收集請假當天「已經在當值」的人員名單，避免重複安排
    assigned_today = {str(current_roster.at[day, r]).strip() for r in COLUMNS_ROSTER if str(current_roster.at[day, r]).strip() not in ["", "X"]}

    # 計算當前畫面上所有人已分配的總重
    current_weights = {str(s['name']).strip(): 0.0 for s in students if pd.notna(s['name'])}
    for d in DAYS:
        for r in COLUMNS_ROSTER:
            p = str(current_