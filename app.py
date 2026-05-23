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
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=["name", "form", "class", "role", "available", "remarks"])

def create_blank_roster():
    # 建立以 DAYS 為索引，職位為欄位的空白值班表
    df = pd.DataFrame(index=DAYS, columns=COLUMNS_ROSTER).fillna("")
    return df

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = create_blank_roster()

# ==========================================
# 4. 核心排班演算法
# ==========================================
def generate_roster(students_df):
    if students_df.empty:
        st.error("⚠️ 錯誤：目前學生名單為空，請先在左側邊欄新增或上傳名單！")
        return create_blank_roster()

    new_roster = create_blank_roster()
    students = students_df.to_dict('records')
    
    # 初始化每位學生的加權負荷與上一次當值日
    weekly_weights = {str(s['name']).strip(): 0.0 for s in students if pd.notna(s['name'])}
    last_duty_day = {str(s['name']).strip(): -2 for s in students if pd.notna(s['name'])}
    
    # 按天、按職位進行排班
    for d_idx, day in enumerate(DAYS):
        assigned_today = set()  # 確保一般 Study Prefect 一天最多只能安排 1 個職位
        
        for role in COLUMNS_ROSTER:
            # 依據需求規則：Room 202 僅週一、三、四開放（週二、五常規不開放 -> 保持留白）
            if 'Room 202' in role and day in ['Tue', 'Fri']:
                continue
                
            candidates = []
            for s in students:
                if pd.isna(s['name']) or str(s['name']).strip() == "":
                    continue
                name = str(s['name']).strip()
                
                # 穩健解析空閒日子 (將多種可能輸入統一切割為乾淨的 List)
                avail_val = s['available']
                if isinstance(avail_val, list):
                    avail = [str(d).strip() for d in avail_val]
                else:
                    avail = [d.strip() for d in str(avail_val).split(',') if d.strip()]

                # 1. 基本限制：必須在該學生 available 的日子 + 今天還沒排過
                if day not in avail or name in assigned_today:
                    continue
                
                # 2. 身份排他性限制
                is_ahp = (str(s['role']).strip() == "Assistant Head Study Prefect")
                if (role == 'Assist. in charge' and not is_ahp) or \
                   (role != 'Assist. in charge' and is_ahp):
                    continue

                # 3. 軟性分數計算 (分數越低越優先)
                score = 0
                w = WEIGHTS[role]

                # 限制：避免連續兩天值班
                if last_duty_day[name] == d_idx - 1:
                    score += 1000
                
                # 限制：每週加權上限最多 3 次 (3.0)
                if weekly_weights[name] + w > 3.0:
                    score += 800
                
                # 年級優先權
                form_str = str(s.get('form', '')).upper().strip()
                is_senior = any(x in form_str for x in ["4", "5", "6", "SENIOR"])
                
                if role == 'Room 302':
                    score += 30 if is_senior else -30
                elif 'Room 303' in role or 'Room 202' in role:
                    score += -30 if is_senior else 30

                # 公平分配
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
# 5. 智慧替補機制
# ==========================================
def get_optimized_substitutes(day, role, absentee, students_df, current_roster):
    if students_df.empty: 
        return pd.DataFrame()
        
    students = students_df.to_dict('records')
    assigned_today = {str(current_roster.at[day, r]).strip() for r in COLUMNS_ROSTER if str(current_roster.at[day, r]).strip() not in ["", "X"]}

    current_weights = {str(s['name']).strip(): 0.0 for s in students if pd.notna(s['name'])}
    for d in DAYS:
        for r in COLUMNS_ROSTER:
            p = str(current_roster.at[d, r]).strip()
            if p in current_weights:
                current_weights[p] += WEIGHTS[r]

    subs_pool = []
    for s in students:
        if pd.isna(s['name']): 
            continue
        name = str(s['name']).strip()
        if name == absentee:
            continue
            
        # 解析日子
        avail_val = s['available']
        if isinstance(avail_val, list):
            avail = [str(d).strip() for d in avail_val]
        else:
            avail = [d.strip() for d in str(avail_val).split(',') if d.strip()]
            
        if day not in avail or name in assigned_today:
            continue
        
        is_ahp = (str(s['role']).strip() == "Assistant Head Study Prefect")
        if (role == 'Assist. in charge' and not is_ahp) or \
           (role != 'Assist. in charge' and is_ahp):
            continue
            
        p_weight = current_weights.get(name, 0.0)
        if p_weight + WEIGHTS[role] > 3.0:
            continue
            
        subs_pool.append({
            "姓名": name,
            "年級": s['form'],
            "當週目前負載": p_weight,
            "備註": s['remarks']
        })
    
    if subs_pool:
        return pd.DataFrame(subs_pool).sort_values(by="當週目前負載").head(3)
    return pd.DataFrame()

# ==========================================
# 6. 側邊欄：學生名單管理（修正穩定版）
# ==========================================
with st.sidebar:
    st.header("👥 學生名單管理")
    
    st.download_button(
        label="📥 下載標準名單 CSV 範本",
        data=get_template_csv(),
        file_name="prefect_template.csv",
        mime="text/csv"
    )
    
    st.write("---")
    
    uploaded_file = st.file_uploader("📤 上傳學生名單 CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state.students_df = df
            st.success("名單導入成功！")
        except Exception as e:
            st.error(f"讀取錯誤，請確認欄位格式: {e}")
            
    st.write("---")
    st.subheader("📝 線上建立 / 編輯學生資料")
    st.caption("💡 提示：'可當值日子' 請用英文逗號隔開輸入，例如：`Mon,Wed,Fri`")
    
    # 修正點：將 available 改回 TextColumn，徹底解決 Streamlit 官方不支援多選 selectbox 的 bug
    sidebar_config = {
        "name": st.column_config.TextColumn("姓名 *", required=True),
        "form": st.column_config.TextColumn("年級"),
        "class": st.column_config.TextColumn("班級"),
        "role": st.column_config.SelectboxColumn(
            "職級", options=["Study Prefect", "Assistant Head Study Prefect"], default="Study Prefect", required=True
        ),
        "available": st.column_config.TextColumn("可當值日子 *", default="Mon,Tue,Wed,Thu,Fri", required=True),
        "remarks": st.column_config.TextColumn("備註")
    }
    
    edited_df = st.data_editor(
        st.session_state.students_df,
        column_config=sidebar_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_sidebar"
    )
    st.session_state.students_df = edited_df

    if st.button("💡 載入一鍵測試範例數據"):
        sample_data = [
            {"name": "Tom", "form": "F.5", "class": "5A", "role": "Assistant Head Study Prefect", "available": "Mon,Tue,Wed,Thu", "remarks": ""},
            {"name": "Jerry", "form": "F.5", "class": "5B", "role": "Assistant Head Study Prefect", "available": "Wed,Thu,Fri", "remarks": ""},
            {"name": "Alice", "form": "F.4", "class": "4A", "role": "Study Prefect", "available": "Mon,Tue,Wed,Thu,Fri", "remarks": "偏好 Room 303"},
            {"name": "Bob", "form": "F.4", "class": "4B", "role": "Study Prefect", "available": "Mon,Tue,Thu", "remarks": ""},
            {"name": "Chris", "form": "F.5", "class": "5A", "role": "Study Prefect", "available": "Tue,Wed,Fri", "remarks": ""},
            {"name": "David", "form": "F.3", "class": "3A", "role": "Study Prefect", "available": "Mon,Wed,Thu,Fri", "remarks": ""},
            {"name": "Emma", "form": "F.4", "class": "4C", "role": "Study Prefect", "available": "Mon,Tue,Wed,Fri", "remarks": ""},
            {"name": "Flora", "form": "F.5", "class": "5C", "role": "Study Prefect", "available": "Thu,Fri", "remarks": ""},
        ]
        st.session_state.students_df = pd.DataFrame(sample_data)
        st.rerun()

# ==========================================
# 7. 主畫面：生成與直接編輯值班表
# ==========================================
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("📅 Study Prefect Duty Roster")
    st.caption("點擊左側功能選單可以隨時管理名單")

with head_col2:
    if not st.session_state.students_df.empty:
        if st.button("🚀 生成本週值班表", type="primary", use_container_width=True):
            with st.spinner("正在為您公平排班中..."):
                st.session_state.roster_df = generate_roster(st.session_state.students_df)
                st.success("🎉 值班表已成功生成！")

if st.session_state.students_df.empty:
    st.info("👋 歡迎使用！請先在左側邊欄【建立學生名單】或點擊【載入一鍵測試範例數據】開始。")
else:
    if st.button("🔄 重新生成（重置全新排班方案）"):
        with st.spinner("正在重新計算..."):
            st.session_state.roster_df = generate_roster(st.session_state.students_df)
            st.success("🎉 已為您更換全新排班方案！")

    st.write("---")
    st.subheader("📋 本週值班表 (可直接雙擊修改)")
    st.caption("💡 提示：您可以直接點擊儲存格更換人名，或者手動改成 'X' 表示特殊不開放。")
    
    updated_roster = st.data_editor(
        st.session_state.roster_df,
        use_container_width=True,
        key="main_roster_editor"
    )
    st.session_state.roster_df = updated_roster

    # ==========================================
    # 8. 詳細統計表
    # ==========================================
    st.write("---")
    st.subheader("📊 本週值班次數與負荷平衡監控")
    
    stats = {str(name).strip(): {"值班次數": 0, "累積加權負荷": 0.0} for name in st.session_state.students_df["name"] if pd.notna(name)}
    
    for d in DAYS:
        for r in COLUMNS_ROSTER:
            p = str(st.session_state.roster_df.loc[d, r]).strip()
            if p in stats:
                stats[p]["值班次數"] += 1
                stats[p]["累積加權負荷"] += WEIGHTS[r]
                
    stats_df = pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': '學生姓名'})
    
    st.dataframe(
        stats_df,
        column_config={
            "累積加權負荷": st.column_config.ProgressColumn("當週工作量上限指標 (最高 3.0)", min_value=0, max_value=3, format="%.1f")
        },
        use_container_width=True,
        hide_index=True
    )

    # ==========================================
    # 9. 下載功能
    # ==========================================
    st.write("---")
    st.subheader("💾 匯出與下載值班表")
    
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    
    csv_data = st.session_state.roster_df.to_csv().encode('utf-8-sig')
    dl_col1.download_button("📥 下載 CSV 檔案", csv_data, "prefect_roster.csv", "text/csv", use_container_width=True)
    
    output_excel = BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        st.session_state.roster_df.to_excel(writer, sheet_name='值班表')
        stats_df.to_excel(writer, sheet_name='工作負荷統計', index=False)
    dl_col2.download_button("📥 下載 Excel 試算表", output_excel.getvalue(), "prefect_roster.xlsx", use_container_width=True)
    
    md_data = st.session_state.roster_df.to_markdown()
    dl_col3.download_button("📝 下載 Markdown 文字", md_data.encode('utf-8'), "prefect_roster.md", "text/plain", use_container_width=True)

    # ==========================================
    # 10. 替補機制 UI
    # ==========================================
    st.write("---")
    st.subheader("🔄 臨時請假？智慧替補候選人建議")
    
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        chosen_day = st.selectbox("請假日期 (星期)", DAYS)
    with sub_col2:
        chosen_role = st.selectbox("請假職位/房間", COLUMNS_ROSTER)
        
    current_person = str(st.session_state.roster_df.at[chosen_day, chosen_role]).strip()
    st.text_input("目前該時段被排定的人員", value=current_person if current_person not in ["", "X"] else "（當前為空白時段）", disabled=True)
    
    if st.button("🔍 篩選並推薦最優替補"):
        if current_person in ["", "X"]:
            st.warning("提示：該時段目前不需要尋找替補。")
        else:
            rec_df = get_optimized_substitutes(chosen_day, chosen_role, current_person, st.session_state.students_df, st.session_state.roster_df)
            if not rec_df.empty:
                st.success("💡 系統已為您尋找 2–3 名最適合的替補人選（已依工作負荷量由輕到重排序）：")
                st.table(rec_df)
            else:
                st.error("⚠️ 警告：目前系統找不到任何完全合規（即：今天有空、職級符合、且本週累積工作量不會超標）的替補人選！請進行人工協調。")