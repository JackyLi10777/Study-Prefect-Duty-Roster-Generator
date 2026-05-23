import streamlit as st
import pandas as pd
import random
import plotly.express as px
from io import BytesIO

# ==========================================
# 1. 網頁初始設定（聖言藍金行動端優化風）
# ==========================================
st.set_page_config(
    page_title="SYSS Study Prefect Duty Roster Platform",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<style>
    .main > div { padding-top: 1.5rem !important; }
    .main-title { color: #0C2340; font-size: 34px; font-weight: bold; letter-spacing: 1px; margin-bottom: 0px; }
    .main-subtitle { color: #D4AF37; font-size: 15px; margin-top: 0px; margin-bottom: 15px; font-weight: 500; }
    .stDataFrame, [data-testid=\"stDataEditor\"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { width: 100% !important; height: 3.2rem !important; font-size: 15px !important; font-weight: bold !important; border-radius: 12px !important; transition: all 0.3s ease; background-color: #0C2340 !important; color: white !important; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(12,35,64,0.4); background-color: #D4AF37 !important; color: #0C2340 !important; }
    .danger-alert { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 8px; color: #991B1B; margin-bottom: 15px; }
    .warning-alert { background-color: #FFFBEB; border-left: 5px solid #F59E0B; padding: 15px; border-radius: 8px; color: #92400E; margin-bottom: 15px; }
    .success-alert { background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 15px; border-radius: 8px; color: #166534; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🦅 SING YIN SECONDARY SCHOOL</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">Study Prefect Team 智慧排崗管理系統 ｜ 終極穩定版 (v3.0)</p>', unsafe_allow_html=True)

# ==========================================
# 2. 定義基礎靜態規則
# ==========================================
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
ROOMS = [
    "Room202 (1st Prefect)", "Room202 (2nd Prefect)",
    "Room302 (1st Prefect)", "Room302 (2nd Prefect)",
    "Room303 (1st Prefect)", "Room303 (2nd Prefect)"
]

def get_weight(day, room):
    if day == "WEDNESDAY":
        return 1.5
    if "Room202" in room:
        return 1.0
    return 0.5

DEFAULT_STUDENTS = [f"SYSS Prefect {str(i).zfill(2)}" for i in range(1, 15)]

# ==========================================
# 3. 側邊欄：歷史資料庫、名冊與請假管理
# ==========================================
with st.sidebar:
    st.header("🗄️ 1. 跨週歷史數據備份區")
    uploaded_file = st.file_uploader(
        "若為第二週以上啟用，請上傳上週導出的 Excel 檔案以延續累計點數。全新第一週啟用請直接留空。",
        type=["xlsx"]
    )
    
    st.write("---")
    st.header("👥 2. 本學期 Prefect 兄弟名冊")
    students_text = st.text_area(
        "成員名單設定（每行一個名字）：", 
        value="\n".join(DEFAULT_STUDENTS), 
        height=200
    )
    current_students = [name.strip() for name in students_text.split("\n") if name.strip()]

    st.write("---")
    st.header("🛑 3. 本週請假/免役名單")
    st.caption("被勾選的兄弟將不會被系統安排本週崗位")
    leave_students = st.multiselect(
        "選擇請假兄弟：",
        options=current_students,
        default=[]
    )

# ==========================================
# 4. 解析或自動初始化歷史點數數據庫
# ==========================================
history_db = {}
if uploaded_file is not None:
    try:
        parsed_df = pd.read_excel(uploaded_file, sheet_name="累計值崗數據歷史庫", skiprows=4)
        if "Prefect 姓名" in parsed_df.columns:
            for _, row in parsed_df.iterrows():
                name = str(row["Prefect 姓名"]).strip()
                if name in current_students:
                    history_db[name] = {
                        "times": int(row.get("歷史累計值崗次數", 0)),
                        "points": float(row.get("歷史累計加權負荷點數", 0.0))
                    }
            st.sidebar.success("✅ 成功讀取歷史累積點數檔案！")
    except Exception as e:
        st.sidebar.error(f"❌ 歷史檔案解析失敗，請確認格式。錯誤訊息: {e}")

for student in current_students:
    if student not in history_db:
        history_db[student] = {"times": 0, "points": 0.0}

# ==========================================
# 5. 初始化當週崗位表 Session State
# ==========================================
if 'duty_matrix' not in st.session_state:
    st.session_state.duty_matrix = pd.DataFrame("", index=ROOMS, columns=DAYS)

# ==========================================
# 6. 核心排崗按鈕：請假支援與防連續疲勞演算法
# ==========================================
st.subheader("🛠️ 當週排崗動態控制台")

if st.button("🚀 啟動聖言演算法：自動隨機公平排崗", type="primary"):
    simulated_history = {s: history_db[s]["points"] for s in current_students}
    new_matrix = pd.DataFrame("", index=ROOMS, columns=DAYS)
    
    all_slots = []
    for d in DAYS:
        for r in ROOMS:
            if d == "WEDNESDAY":
                continue
            if 'Room202' in r and d in ['MONDAY', 'TUESDAY', 'THURSDAY', 'FRIDAY']:
                continue
            if ('Room302' in r or 'Room303' in r) and d in ['MONDAY', 'THURSDAY', 'FRIDAY']:
                continue
            all_slots.append((d, r))
            
    random.shuffle(all_slots)
    
    for d, r in all_slots:
        # 排除已排班、請假名單
        already_assigned_today = [new_matrix.loc[room_idx, d] for room_idx in ROOMS if new_matrix.loc[room_idx, d] != ""]
        available_candidates = [s for s in current_students if s not in already_assigned_today and s not in leave_students]
        
        # 極端狀況：如果大家都排滿了或請假，強制開放未請假全員
        if not available_candidates:
            available_candidates = [s for s in current_students if s not in leave_students]
        
        # 若連未請假名單都空了（不可能發生，防呆用），開放全員
        if not available_candidates:
            available_candidates = current_students
            
        # 找出最低點數的候選人
        min_point = round(min([simulated_history[cand] for cand in available_candidates]), 2)
        best_candidates = [cand for cand in available_candidates if round(simulated_history[cand], 2) == min_point]
        
        chosen_prefect = random.choice(best_candidates)
        
        new_matrix.loc[r, d] = chosen_prefect
        simulated_history[chosen_prefect] += get_weight(d, r)
        
    st.session_state.duty_matrix = new_matrix
    st.rerun()

# ==========================================
# 7. 主要互動式崗位表編輯器
# ==========================================
st.markdown("### 📅 本週 Prefect 值崗排崗表 (可直接點擊格子手動修改)")
st.caption("💡 提示：Wednesday 全天不開崗。Room202 僅週三開崗。Room302/303 僅週一、四、五開崗。其餘崗位系統已自動鎖定。")

edited_matrix = st.data_editor(
    st.session_state.duty_matrix,
    use_container_width=True,
    height=260,
    key="editor_matrix"
)
st.session_state.duty_matrix = edited_matrix

# ==========================================
# 8. 即時防呆熔斷與提示機制
# ==========================================
typo_detected = False
invalid_entries = []
vacuum_detected = False
vacuum_entries = []

for d in DAYS:
    for r in ROOMS:
        val = str(edited_matrix.loc[r, d]).strip()
        if val != "" and val not in current_students:
            typo_detected = True
            invalid_entries.append(f"• 【{d} - {r}】輸入了無效姓名：\"{val}\"")
        
        is_closed = (('Room202' in r and d in ['MONDAY', 'TUESDAY', 'THURSDAY', 'FRIDAY']) or 
                     (('Room302' in r or 'Room303' in r) and d in ['MONDAY', 'THURSDAY', 'FRIDAY']) or
                     (d == "WEDNESDAY"))
        if val == "" and not is_closed:
            vacuum_detected = True
            vacuum_entries.append(f"• 【{d} - {r}】目前處於無人值崗的空白狀態")

if typo_detected:
    st.markdown('<div class="danger-alert"><b>⚠️ 偵測到未登記的姓名（防呆機制已啟動）：</b><br>' + '<br>'.join(invalid_entries) + '<br><i>請修正格子內的名字，確保與左側名冊完全相同（注意大小寫）。目前點數統計已暫停，匯出功能已鎖定。</i></div>', unsafe_allow_html=True)

if vacuum_detected and not typo_detected:
    st.markdown('<div class="warning-alert"><b>💡 溫馨提示：目前崗位表存在尚未安排人員的空白崗位：</b><br>' + '<br>'.join(vacuum_entries) + '<br><i>這不影響系統運行，但請確認是否需要手動指派兄弟補齊人力。</i></div>', unsafe_allow_html=True)

# ==========================================
# 9. 動態數據整合與計算
# ==========================================
final_records = []
for s in current_students:
    hist_times = history_db[s]["times"]
    hist_points = history_db[s]["points"]
    
    current_times = 0
    current_points = 0.0
    
    if not typo_detected:
        for d in DAYS:
            for r in ROOMS:
                if str(edited_matrix.loc[r, d]).strip() == s:
                    current_times += 1
                    current_points += get_weight(d, r)
                    
    final_times = hist_times + current_times
    final_points = round(hist_points + current_points, 2)
    
    final_records.append({
        "Prefect 姓名": s,
        "當週新增值崗次數": current_times,
        "當週新增加權點數": current_points,
        "歷史累計值崗次數": final_times,
        "歷史累計加權負荷點數": final_points
    })

master_report_df = pd.DataFrame(final_records)

# ==========================================
# 10. 後台數據看板與 Excel 導出下載區
# ==========================================
st.write("---")
st.subheader("📈 本週數據核算與跨週歷史資料庫備份導出")

if typo_detected:
    st.warning("⚠️ 請先修正崗位表中拼錯的名字，系統方可進行總點數核算與數據導出。")
else:
    col1, col2 = st.columns()
    
    with col1:
        st.dataframe(master_report_df, use_container_width=True, hide_index=True)
        
    with col2:
        st.markdown("""
        <div style="background-color: #FAFAFA; padding: 15px; border-radius: 12px; border: 1px solid #E5E7EB;">
            <h4 style="margin-top:0; color:#0C2340;">💾 SYSS 數據跨週保存</h4>
            <p style="font-size: 13px; color:#4B5563; line-height: 1.6;">
                請排崗負責人於每週確認崗位表後，點擊下方按鈕導出 Excel。
                <br><b>下週排崗前，把該檔案丟回左側上傳區，就能讓兄弟們的點數完美跨週累計，確保點數絕對平均！</b>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            master_report_df.to_excel(writer, sheet_name="累計值崗數據歷史庫", index=False, startrow=4)
            ws = writer.sheets["累計值崗數據歷史庫"]
            ws["A1"] = "Sing Yin Secondary School - Study Prefect Duty Database"
            ws["A2"] = "【聖言 Study Prefect 團隊專用】此檔案用於儲存跨週歷史點數。下週排崗時請將此檔上傳至系統，確保點數絕對平均。"
            
        st.download_button(
            label="📥 導出最新累計歷史資料庫檔案 (Excel)",
            data=output_excel.getvalue(),
            file_name="SYSS_Study_Prefect_Database.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# ==========================================
# 11. 歷史總負荷分布監控統計圖表 (Plotly)
# ==========================================
if not typo_detected:
    st.write("---")
    st.subheader("📊 兄弟們的歷史總工作負荷分佈（演算法會自動拉平差距）")
    
    fig = px.bar(
        master_report_df,
        x='Prefect 姓名',
        y='歷史累計加權負荷點數',
        text='歷史累計加權負荷點數',
        title="全體 Study Prefect 歷史累積點數（越平整代表全隊負擔越平均）",
        color='歷史累計加權負荷點數',
        color_continuous_scale=[[0, '#0C2340'], [1, '#D4AF37']]
    )
    fig.update_traces(texttemplate='%{text:.1f}點', textposition='outside', marker_line_color='rgb(8,48,107)', marker_line_width=1.5, opacity=0.85)
    fig.update_layout(
        xaxis_title="Prefect 兄弟姓名",
        yaxis_title="總累積加權點數 (Points)",
        font=dict(family="Microsoft JhengHei, sans-serif", size=13),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20),
        height=450
    )
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(229, 231, 235, 0.6)')
    st.plotly_chart(fig, use_container_width=True)
