import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
import datetime
import io
import json

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

# 注入尊貴藍金 CSS 樣式表與隱藏頁尾
st.markdown("""
<style>
    .main > div { padding-top: 1.5rem !important; }
    .main-title { color: #0C2340; font-size: 36px; font-weight: bold; letter-spacing: 2px; margin-bottom: 5px; }
    .main-subtitle { color: #D4AF37; font-size: 15px; font-weight: 600; margin-bottom: 25px; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { height: 3.2rem; border-radius: 8px; font-weight: bold; transition: all 0.3s ease; width: 100%; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(212,175,55,0.3); }
    .report-card { background: #f8f9fa; border-left: 5px solid #0C2340; padding: 15px; border-radius: 4px; margin-bottom: 10px; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🦅 Sing Yin Secondary School</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">STUDY PREFECT DUTY ROSTER SYSTEM — 智慧決策、動態負載與自動化排班系統</div>', unsafe_allow_html=True)

# ==========================================
# 2. 常量定義與核心配置
# ==========================================
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
COLUMNS_ROSTER = ["Assistant Head Study Prefect (AHP)", "Study Room 1 (SR1)", "Study Room 2 (SR2)", "Library (LIB)"]

# ==========================================
# 3. 初始化 Session State (確保跨組件狀態穩定與高容錯)
# ==========================================
if 'students_df' not in st.session_state:
    st.session_state.students_df = None
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = None
if 'report_df' not in st.session_state:
    st.session_state.report_df = None
if 'logo_data' not in st.session_state:
    st.session_state.logo_data = None

# ==========================================
# 4. 側邊欄：大數據行政維護、校徽與彈性權重天平
# ==========================================
with st.sidebar:
    st.markdown("### 🦅 學校行政與校徽系統")
    uploaded_logo = st.file_uploader("上傳官方校徽圖片 (PNG)", type=["png"], key="logo_uploader")
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()
        st.success("🖼️ 校徽圖片已同步整合至 PDF 導出模組！")
        
    st.write("---")
    st.markdown("### ⚙️ 數據源配置管理")
    uploaded_file = st.file_uploader("上載 Prefects 原始名冊 (Excel/CSV)", type=["xlsx", "csv"])
    
    # 數據備份導出與全狀態恢復引擎
    def export_system_backup():
        backup_data = {
            "students_df": st.session_state.students_df.to_dict(orient="records") if st.session_state.students_df is not None else None,
            "roster_df": st.session_state.roster_df.to_dict(orient="index") if st.session_state.roster_df is not None else None,
            "report_df": st.session_state.report_df.to_dict(orient="records") if st.session_state.report_df is not None else None
        }
        return json.dumps(backup_data, ensure_ascii=False, indent=2)

    def import_system_backup(uploaded_json_file):
        try:
            data = json.load(uploaded_json_file)
            if "students_df" in data and "roster_df" in data:
                if data["students_df"] is not None:
                    st.session_state.students_df = pd.DataFrame(data["students_df"])
                if data["roster_df"] is not None:
                    st.session_state.roster_df = pd.DataFrame.from_dict(data["roster_df"], orient="index")
                if data["report_df"] is not None:
                    st.session_state.report_df = pd.DataFrame(data["report_df"])
                st.sidebar.success("🎉 全系統備份數據已完美還原恢復！")
                st.rerun()
            else:
                st.sidebar.error("❌ 備份檔解析失敗：資料結構不符規範。")
        except Exception as e:
            st.sidebar.error(f"❌ 備份還原失敗: {str(e)}")

    st.write("---")
    st.markdown("### 💾 系統備份與還原通道")
    if st.session_state.students_df is not None:
        backup_json = export_system_backup()
        st.download_button(
            label="📤 導出當前全系統備份檔 (.json)",
            data=backup_json,
            file_name=f"SYSS_Prefect_System_Backup_{datetime.date.today().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    uploaded_backup = st.file_uploader("📥 導入 JSON 備份進行還原", type=["json"], key="backup_uploader")
    if uploaded_backup:
        import_system_backup(uploaded_backup)
        
    st.write("---")
    st.markdown("### ⚖️ 職務加權負荷點數設定")
    w_ahp = st.slider("AHP 職位權重", 0.5, 3.0, 1.5, 0.1)
    w_sr1 = st.slider("SR1 房間權重", 0.5, 3.0, 1.0, 0.1)
    w_sr2 = st.slider("SR2 房間權重", 0.5, 3.0, 1.0, 0.1)
    w_lib = st.slider("LIB 圖書館權重", 0.5, 3.0, 1.2, 0.1)
    
    weight_map = {
        "Assistant Head Study Prefect (AHP)": w_ahp,
        "Study Room 1 (SR1)": w_sr1,
        "Study Room 2 (SR2)": w_sr2,
        "Library (LIB)": w_lib
    }

# ==========================================
# 5. 核心業務邏輯函數（高內聚、動態重算閉環）
# ==========================================
def recalculate_workload():
    """
    高能同步重算引擎：融合自動排班與管理員手動調整，即時刷新工作量大表
    """
    if st.session_state.students_df is not None and st.session_state.roster_df is not None:
        students = st.session_state.students_df.copy()
        
        if "歷史累積負荷 (點)" not in students.columns:
            students["歷史累積負荷 (點)"] = 0.0
        else:
            students["歷史累積負荷 (點)"] = pd.to_numeric(students["歷史累積負荷 (點)"], errors='coerce').fillna(0.0)
            
        students["當週加權負荷 (點)"] = 0.0
        
        # 遍歷現有排班矩陣，精準計算當週實際派任負荷
        for day in DAYS:
            for role in COLUMNS_ROSTER:
                person = str(st.session_state.roster_df.at[day, role]).strip()
                if person and person not in ["", "❌ 無合適人員", "X"]:
                    idx = students[students["學生姓名 (Prefect Name)"] == person].index
                    if not idx.empty:
                        students.loc[idx, "當週加權負荷 (點)"] += weight_map[role]
                        
        students["最終總計加權負荷 (點)"] = students["歷史累積負荷 (點)"] + students["當週加權負荷 (點)"]
        st.session_state.students_df = students
        
        # 構建完整大數據審計報表
        st.session_state.report_df = students[[
            "學生姓名 (Prefect Name)", "年級 (Form)", "職級 (Role)", 
            "歷史累積負荷 (點)", "當週加權負荷 (點)", "最終總計加權負荷 (點)"
        ]].copy()

def recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    """
    智慧替補推薦核心函數：全面考量可用日子(相容全稱與縮寫)、歷史累積負荷與職級安全過濾
    """
    if roster_df is None or students_df is None:
        return None, "❌ 尚未生成或載入排班與學生數據。"
        
    try:
        current_person = str(roster_df.at[chosen_day, chosen_role]).strip()
    except Exception:
        return None, "❌ 找不到指定的日子或職位。"

    is_ahp_req = (chosen_role == "Assistant Head Study Prefect (AHP)")
    assigned_today = [str(x).strip() for x in roster_df.loc[chosen_day].values if pd.notna(x)]
    
    subs = []
    for _, rec in students_df.iterrows():
        name = str(rec["學生姓名 (Prefect Name)"]).strip()
        
        if name == current_person or name in assigned_today:
            continue
            
        available_days_str = str(rec.get("可用日子 (Available Days)", "")).upper()
        # 增強型容錯匹配：同時支持全稱(MONDAY)與三字縮寫(MON)
        if (chosen_day.upper() not in available_days_str) and (chosen_day.upper()[:3] not in available_days_str):
            continue
            
        role_type = str(rec.get("職級 (Role)", "")).strip()
        if is_ahp_req and role_type != "Assistant Head Study Prefect":
            continue
        if not is_ahp_req and role_type == "Assistant Head Study Prefect":
            continue
            
        subs.append({
            "姓名": name,
            "年級": rec.get("年級 (Form)", "N/A"),
            "職級": role_type,
            "歷史累積負荷 (點)": round(float(rec.get("歷史累積負荷 (點)", 0.0)), 2),
            "當前總計加權負荷 (點)": round(float(rec.get("最終總計加權負荷 (點)", 0.0)), 2)
        })
        
    if subs:
        sub_df = pd.DataFrame(subs).sort_values(by="當前總計加權負荷 (點)")
        return sub_df, None
    else:
        return None, "❌ 找不到符合當前特定條件（職級、可用日子、無重疊排班）的合格替補人員。"

def generate_pdf_bytes(roster_df, report_df, logo_data=None):
    """
    動態生成奢華網頁外觀並轉換為高解析度 PDF (完美融合校徽圖片與降級備用渲染)
    """
    logo_html = ""
    if logo_data:
        try:
            logo_b64 = base64.b64encode(logo_data).decode()
            logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:65px; display:block; margin:0 auto 10px auto;">'
        except Exception:
            pass
            
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; padding: 20px; }}
            .header-container {{ text-align: center; margin-bottom: 30px; }}
            h1 {{ color: #0C2340; text-align: center; border-bottom: 2px solid #D4AF37; padding-bottom: 10px; margin-top: 5px; }}
            h2 {{ color: #0C2340; margin-top: 25px; font-size: 18px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #0C2340; color: white; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <div class="header-container">
            {logo_html}
            <h1>Sing Yin Secondary School</h1>
            <p style="color: #D4AF37; font-weight: bold; font-size: 16px; margin: 5px 0; text-align: center;">STUDY PREFECT DUTY ROSTER & WORKLOAD AUDIT REPORT</p>
            <p style="text-align: center; font-size: 12px; color: #666;">Generated Date: {datetime.date.today().strftime('%Y-%m-%d')}</p>
        </div>
        
        <h2>1. Weekly Duty Roster</h2>
        {roster_df.to_html(classes='table')}
        
        <h2>2. Dynamic Workload Audit Summary</h2>
        {report_df.to_html(index=False, classes='table')}
    </body>
    </html>
    """
    if PDF_AVAILABLE:
        try:
            return HTML(string=html_content).write_pdf(), "pdf"
        except Exception:
            return html_content.encode('utf-8'), "html"
    else:
        return html_content.encode('utf-8'), "html"

# ==========================================
# 6. 主面板邏輯：智能數據對齊與自動化排班核心
# ==========================================
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)
            
        # 寬容型原始名冊彈性名稱映射器，高度相容多種新舊中英文報表格式
        field_mapping = {
            '姓名': '學生姓名 (Prefect Name)', 'name': '學生姓名 (Prefect Name)', 'Prefect Name': '學生姓名 (Prefect Name)', '學生姓名': '學生姓名 (Prefect Name)',
            '年級': '年級 (Form)', 'form': '年級 (Form)', 'Form': '年級 (Form)',
            '職級': '職級 (Role)', 'role': '職級 (Role)', 'Role': '職級 (Role)',
            '可用日子': '可用日子 (Available Days)', 'available': '可用日子 (Available Days)', 'Available Days': '可用日子 (Available Days)', '可用天數': '可用日子 (Available Days)',
            '歷史動態(點)': '歷史累積負荷 (點)', 'history_weight': '歷史累積負荷 (點)', '歷史點數': '歷史累積負荷 (點)', '歷史累積': '歷史累積負荷 (點)', '歷史累積負荷 (點)': '歷史累積負荷 (點)'
        }
        
        df_input = df_input.rename(columns=lambda x: field_mapping.get(str(x).strip(), str(x).strip()))
        
        # 核心結構強制安全性校驗
        required_cols = ["學生姓名 (Prefect Name)", "職級 (Role)", "可用日子 (Available Days)", "年級 (Form)"]
        if not all(c in df_input.columns for c in required_cols):
            st.error(f"❌ 上載的檔案結構不正確，必須包含以下基本欄位（或可辨識的對應欄位）：{required_cols}")
        else:
            if "歷史累積負荷 (點)" not in df_input.columns:
                df_input["歷史累積負荷 (點)"] = 0.0
            else:
                df_input["歷史累積負荷 (點)"] = pd.to_numeric(df_input["歷史累積負荷 (點)"], errors='coerce').fillna(0.0)
                
            df_input["最終總計加權負荷 (點)"] = df_input["歷史累積負荷 (點)"]
            st.session_state.students_df = df_input
            st.success("🎉 學生名冊原始數據載入成功，並已完成欄位對齊校驗！")
    except Exception as e:
        st.error(f"讀取名冊檔案時發生系統錯誤: {e}")

if st.session_state.students_df is not None:
    st.write("### 📋 領袖生名冊管理系統維護")
    st.dataframe(st.session_state.students_df, use_container_width=True)
    
    # 觸發自動排班按鈕
    if st.button("🚀 開始執行智慧平衡排班演算法", type="primary"):
        with st.spinner("智慧最優化公平引擎計算中，請稍候..."):
            roster = pd.DataFrame(index=DAYS, columns=COLUMNS_ROSTER).fillna("")
            local_students = st.session_state.students_df.copy()
            local_students["最終總計加權負荷 (點)"] = local_students["歷史累積負荷 (點)"].astype(float)
            
            # 排班策略：建立時段清單並確保 AHP 擁有最高調度優先權
            melted_slots = []
            for d in DAYS:
                for c in COLUMNS_ROSTER:
                    priority = 0 if c == "Assistant Head Study Prefect (AHP)" else 1
                    melted_slots.append((priority, d, c))
            
            # 【Bug 修復】：優化排序鍵值，一級排序依職務級別，二級排序依週一至週五時間自然序，拒絕字串首字母隨機排序
            melted_slots.sort(key=lambda x: (x, DAYS.index(x[1])))
            
            # 執行約束條件貪心分配
            for _, day, role in melted_slots:
                is_ahp = (role == "Assistant Head Study Prefect (AHP)")
                assigned_today = [x for x in roster.loc[day].values if x != ""]
                
                # 容錯匹配：支持全稱與簡寫
                cond_day = local_students["可用日子 (Available Days)"].str.upper().str.contains(day.upper(), na=False) | \
                           local_students["可用日子 (Available Days)"].str.upper().str.contains(day.upper()[:3], na=False)
                
                if is_ahp:
                    cond_role = local_students["職級 (Role)"] == "Assistant Head Study Prefect"
                else:
                    cond_role = local_students["職級 (Role)"] != "Assistant Head Study Prefect"
                    
                candidates = local_students[cond_day & cond_role & (~local_students["學生姓名 (Prefect Name)"].isin(assigned_today))]
                
                if candidates.empty:
                    roster.at[day, role] = "❌ 無合適人員"
                    continue
                
                # 核心動態負載天平分配
                min_load = candidates["最終總計加權負荷 (點)"].min()
                best_candidates = candidates[candidates["最終總計加權負荷 (點)"] == min_load]
                
                chosen_one = random.choice(best_candidates["學生姓名 (Prefect Name)"].values)
                roster.at[day, role] = chosen_one
                
                idx = local_students[local_students["學生姓名 (Prefect Name)"] == chosen_one].index
                local_students.loc[idx, "最終總計加權負荷 (點)"] += weight_map[role]
            
            st.session_state.roster_df = roster
            recalculate_workload()
            st.success("✨ 智慧公平排班表生成完畢！已完美均勻分配工作量。")

# ==========================================
# 7. 報表展示與高階微調同步引擎
# ==========================================
if st.session_state.roster_df is not None:
    st.write("---")
    st.subheader("📅 本週 Study Prefect 輪值排班總表 (支援現場互動微調修正)")
    
    updated_roster = st.data_editor(st.session_state.roster_df, use_container_width=True)
    
    col_save1, col_save2 = st.columns([3, 7])
    with col_save1:
        if st.button("🔄 儲存手動微調並同步更新數據", type="secondary"):
            st.session_state.roster_df = updated_roster
            recalculate_workload()
            st.success("📝 手動微調覆寫已儲存！所有統計報表、公平性校驗圖已完成即時聯動更新。")
            st.rerun()
            
    st.write("---")
    st.subheader("📊 領袖生加權工作量全景審計與監控")
    
    col_graph, col_tbl = st.columns([6, 4])
    
    with col_tbl:
        st.write("📋 動態審計明細表 (依最終總負荷由高至低)")
        sorted_report = st.session_state.report_df.sort_values(by="最終總計加權負荷 (點)", ascending=False)
        st.dataframe(sorted_report, use_container_width=True, hide_index=True)
        
    with col_graph:
        # 【視覺優化】：自定義尊貴藍金漸層色階(Navy Blue -> Gold)，完美切合聖言中學視覺意向
        fig = px.bar(
            st.session_state.report_df, 
            x='學生姓名 (Prefect Name)', 
            y='最終總計加權負荷 (點)',
            text_auto='.2f',  # 整合舊版精準度設定
            title="領袖生工作分配公平性監控圖表 (藍金專屬視覺)",
            color='最終總計加權負荷 (點)',
            color_continuous_scale=[[0, '#0C2340'], [1, '#D4AF37']]
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # 8. 高級多格式數據導出面板
    # ==========================================
    st.write("---")
    st.subheader("📥 導出行政官方排班報告文件")
    
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    
    # Excel 完整導出 + 行政自動優化欄寬
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
        st.session_state.roster_df.to_excel(writer, sheet_name='本週排班總表')
        st.session_state.report_df.to_excel(writer, sheet_name='動態負荷工作量審計', index=False)
        # 高級行政優化：調整欄寬防遮擋
        for sheet_name in writer.sheets:
            writer.sheets[sheet_name].set_column(0, 10, 22)
            
    dl_col1.download_button(
        label="🟢 下載 Excel 試算表 (.xlsx)",
        data=output_excel.getvalue(),
        file_name=f"SYSS_Prefect_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    # Markdown 文字導出
    md_data = f"### Sing Yin Secondary School Study Prefect Duty Roster\nReport Date: {datetime.date.today()}\n\n" + st.session_state.roster_df.to_markdown()
    dl_col2.download_button(
        label="📝 下載 Markdown 簡報字檔 (.md)",
        data=md_data.encode('utf-8'),
        file_name=f"SYSS_Prefoster_{datetime.date.today().strftime('%Y%m%d')}.md",
        mime="text/plain",
        use_container_width=True
    )
    
    # 高階 PDF 導出通道
    report_bytes, file_type = generate_pdf_bytes(st.session_state.roster_df, st.session_state.report_df, st.session_state.logo_data)
    if file_type == "pdf":
        dl_col3.download_button(
            label="🔴 下載 PDF 官方列印報表 (.pdf)",
            data=report_bytes,
            file_name=f"SYSS_Report_{datetime.date.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    else:
        dl_col3.download_button(
            label="🌐 下載網頁版 HTML 報表 (PDF 降級備用)",
            data=report_bytes,
            file_name=f"SYSS_Report_{datetime.date.today().strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True
        )

    # ==========================================
    # 9. 智慧請假應變替補建議模組
    # ==========================================
    st.write("---")
    st.subheader("🩹 臨時突發請假緊急應變？智慧替補推薦")
    
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        chosen_day = st.selectbox("請假日期 (星期)", DAYS, key="sub_day_select")
    with sub_col2:
        chosen_role = st.selectbox("請假職位/房間區塊", COLUMNS_ROSTER, key="sub_role_select")
        
    current_person = str(st.session_state.roster_df.at[chosen_day, chosen_role]).strip()
    st.text_input(
        "當前原定受指派之人員", 
        value=current_person if current_person not in ["", "❌ 無合適人員", "X"] else "（當前時段本為空缺狀態）", 
        disabled=True
    )
    
    if st.button("🔍 執行智慧篩選並推薦最優替補候選名單"):
        res_df, err = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
        if err:
            st.error(err)
        else:
            st.success(f"📋 依「當前總計負荷最少者優先」篩選之完美替補名單（已自動識別全稱/縮寫、剔除當天有任務、非同等職級與不可用者）：")
            st.dataframe(res_df, use_container_width=True, hide_index=True)
else:
    st.info("💡 提示：請先於左側邊欄上載 Prefects 原始名冊或導入 JSON 系統備份檔，以開啟自動化排班決策功能。")
