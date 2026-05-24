import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
import datetime
import io
import json

# ==========================================\n# 0. PDF 支援與環境強固檢查\n# ==========================================\ntry:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False

# ==========================================\n# 1. 網頁基礎設定與奢華聖言藍金視覺 UI 注入\n# ==========================================\nst.set_page_config(
    page_title="Sing Yin Study Prefect Duty Roster System",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入尊貴藍金 CSS 樣式表
st.markdown("""
<style>
    .main > div { padding-top: 1.5rem !important; }
    .main-title { color: #0C2340; font-size: 36px; font-weight: bold; letter-spacing: 2px; margin-bottom: 5px; }
    .main-subtitle { color: #D4AF37; font-size: 15px; font-weight: 600; margin-bottom: 25px; }
    .stDataFrame, [data-testid=\"stDataEditor\"] { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
    .stButton > button { height: 3.2rem; border-radius: 8px; font-weight: bold; transition: all 0.3s ease; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(212,175,55,0.3); }
    .report-card { background: #f8f9fa; border-left: 5px solid #0C2340; padding: 15px; border-radius: 4px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🦅 Sing Yin Secondary School</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">STUDY PREFECT DUTY ROSTER SYSTEM — 智慧決策與自動化排班系統</div>', unsafe_allow_html=True)

# ==========================================\n# 2. 常量定義與核心配置\n# ==========================================\nDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
COLUMNS_ROSTER = ["Assistant Head Study Prefect (AHP)", "Study Room 1 (SR1)", "Study Room 2 (SR2)", "Library (LIB)"]

# ==========================================\n# 3. 核心業務邏輯函數（封裝與優化）\n# ==========================================\ndef recommend_substitutes(roster_df, students_df, chosen_day, chosen_role):
    """
    智慧替補推薦核心函數：整合最新版安全篩選與舊版函數化結構
    """
    if roster_df is None or students_df is None:
        return None, "❌ 尚未生成或載入排班與學生數據。"
        
    try:
        current_person = str(roster_df.at[chosen_day, chosen_role]).strip()
    except Exception:
        return None, "❌ 找不到指定的日子或職位。"

    # 判定是否需要 AHP 職級
    is_ahp_req = (chosen_role == "Assistant Head Study Prefect (AHP)")
    
    # 找出當天已被排班的人員，避免重複排班
    assigned_today = [str(x).strip() for x in roster_df.loc[chosen_day].values if pd.notna(x)]
    
    subs = []
    for _, rec in students_df.iterrows():
        name = str(rec["學生姓名 (Prefect Name)"]).strip()
        
        # 排除本人及當天已有任務的人
        if name == current_person or name in assigned_today:
            continue
            
        # 檢查該日子是否在學生的可用日子中
        available_days_str = str(rec.get("可用日子 (Available Days)", "")).upper()
        if chosen_day.upper() not in available_days_str:
            continue
            
        # 職級過濾
        role_type = str(rec.get("職級 (Role)", "")).strip()
        if is_ahp_req and role_type != "Assistant Head Study Prefect":
            continue
        if not is_ahp_req and role_type == "Assistant Head Study Prefect":
            continue
            
        subs.append({
            "姓名": name,
            "年級": rec.get("年級 (Form)", "N/A"),
            "職級": role_type,
            "當前總計加權負荷 (點)": rec.get("最終總計加權負荷 (點)", 0.0)
        })
        
    if subs:
        sub_df = pd.DataFrame(subs).sort_values(by="當前總計加權負荷 (點)")
        return sub_df, None
    else:
        return None, "❌ 找不到符合當前特定條件（職級、可用日子、無重疊排班）的合格替補人員。"

def generate_pdf_bytes(roster_df, report_df):
    """
    動態生成優雅的 HTML 並轉換為 PDF (支援 WeasyPrint 熔斷降級)
    """
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; padding: 20px; }}
            h1 {{ color: #0C2340; text-align: center; border-bottom: 2px solid #D4AF37; padding-bottom: 10px; }}
            h2 {{ color: #0C2340; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #0C2340; color: white; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>Sing Yin Study Prefect Duty Report</h1>
        <p>Generated on: {datetime.date.today().strftime('%Y-%m-%d')}</p>
        
        <h2>1. Weekly Duty Roster</h2>
        {roster_df.to_html()}
        
        <h2>2. Workload Statistics Summary</h2>
        {report_df.to_html(index=False)}
    </body>
    </html>
    """
    if PDF_AVAILABLE:
        return HTML(string=html_content).write_pdf(), "pdf"
    else:
        return html_content.encode('utf-8'), "html"

# ==========================================\n# 4. 初始化 Session State (確保跨組件狀態穩定)\n# ==========================================\nif 'students_df' not in st.session_state:
    st.session_state.students_df = None
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = None
if 'report_df' not in st.session_state:
    st.session_state.report_df = None

# ==========================================\n# 5. 側邊欄：數據源配置與參數調整\n# ==========================================\nwith st.sidebar:
    st.markdown("### ⚙️ 系統核心配置")
    uploaded_file = st.file_uploader("上載 Prefects 原始資料名單 (Excel/CSV)", type=["xlsx", "csv"])
    
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

# ==========================================\n# 6. 主面板邏輯：數據處理與自動排班核心\n# ==========================================\nif uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)
            
        # 核心基礎數據清洗與結構檢查
        required_cols = ["學生姓名 (Prefect Name)", "職級 (Role)", "可用日子 (Available Days)", "年級 (Form)"]
        if not all(c in df_input.columns for c in required_cols):
            st.error(f"❌ 上載的檔案結構不正確，必須包含以下欄位：{required_cols}")
        else:
            # 初始化或重置計算欄位
            df_input["最終總計加權負荷 (點)"] = 0.0
            st.session_state.students_df = df_input
            st.success("🎉 學生名單原始數據成功載入並完成校驗！")
    except Exception as e:
        st.error(f"讀取檔案時發生錯誤: {e}")

if st.session_state.students_df is not None:
    st.write("### 📋 原始數據預覽 (Prefects 名單)")
    st.dataframe(st.session_state.students_df, use_container_width=True)
    
    # 觸發自動排班按鈕
    if st.button("🚀 開始執行智慧平衡排班演算法", type="primary"):
        with st.spinner("智慧優化引擎計算中，請稍候..."):
            # 建立空白排班表
            roster = pd.DataFrame(index=DAYS, columns=COLUMNS_ROSTER).fillna("")
            
            # 複製數據以便計算權重
            local_students = st.session_state.students_df.copy()
            local_students["最終總計加權負荷 (點)"] = 0.0
            
            # 排班策略：優先排 AHP 職位，再排其餘房間職位
            # 遍歷日子進行隨機動態最優分派
            melted_slots = []
            for d in DAYS:
                for c in COLUMNS_ROSTER:
                    # 排序確保先處理 AHP
                    priority = 0 if c == "Assistant Head Study Prefect (AHP)" else 1
                    melted_slots.append((priority, d, c))
            
            melted_slots.sort(key=lambda x: x)  # 先排 AHP
            
            # 執行分配
            success_generation = True
            for _, day, role in melted_slots:
                is_ahp = (role == "Assistant Head Study Prefect (AHP)")
                
                # 篩選當天可用且符合職級要求的候選人
                # 排除當天已被分配過任何職務的人
                assigned_today = [x for x in roster.loc[day].values if x != ""]
                
                cond_day = local_students["可用日子 (Available Days)"].str.upper().str.contains(day.upper(), na=False)
                if is_ahp:
                    cond_role = local_students["職級 (Role)"] == "Assistant Head Study Prefect"
                else:
                    cond_role = local_students["職級 (Role)"] != "Assistant Head Study Prefect"
                    
                candidates = local_students[cond_day & cond_role & (~local_students["學生姓名 (Prefect Name)"].isin(assigned_today))]
                
                if candidates.empty:
                    # 隨機安全熔斷機制
                    roster.at[day, role] = "❌ 無合適人員"
                    continue
                
                # 核心負載均衡平衡算法：選擇當前加權負荷「最少」的人
                min_load = candidates["最終總計加權負荷 (點)"].min()
                best_candidates = candidates[candidates["最終總計加權負荷 (點)"] == min_load]
                
                # 若有多人點數相同，隨機選擇以確保公平性
                chosen_one = random.choice(best_candidates["學生姓名 (Prefect Name)"].values)
                
                # 寫入排班表
                roster.at[day, role] = chosen_one
                
                # 更新該生累計工作負荷點數
                idx = local_students[local_students["學生姓名 (Prefect Name)"] == chosen_one].index
                local_students.loc[idx, "最終總計加權負荷 (點)"] += weight_map[role]
            
            # 將結果存入 session_state
            st.session_state.roster_df = roster
            st.session_state.students_df = local_students
            
            # 生成主統計報表 (Master Report)
            st.session_state.report_df = local_students[["學生姓名 (Prefect Name)", "年級 (Form)", "職級 (Role)", "最終總計加權負荷 (點)"]].copy()
            st.success("✨ 智慧輪班排班表生成完畢！已優化整體工作量均勻分配。")

# ==========================================\n# 7. 報表展示與視覺化圖表引擎\n# ==========================================\nif st.session_state.roster_df is not None:
    st.write("---")
    st.subheader("📅 本週 Study Prefect 輪值排班總表")
    st.dataframe(st.session_state.roster_df, use_container_width=True)
    
    st.write("---")
    st.subheader("📊 全體累積工作負荷監控與統計")
    
    col_graph, col_tbl = st.columns([6, 4])
    
    with col_tbl:
        st.write("📋 工作點數明細 (由高至低排定)")
        sorted_report = st.session_state.report_df.sort_values(by="最終總計加權負荷 (點)", ascending=False)
        st.dataframe(sorted_report, use_container_width=True, hide_index=True)
        
    with col_graph:
        fig = px.bar(
            st.session_state.report_df, 
            x='學生姓名 (Prefect Name)', 
            y='最終總計加權負荷 (點)',
            text_auto='.1f',
            title="領袖生負載分配公平性校驗圖",
            color='最終總計加權負荷 (點)',
            color_continuous_scale='Bluered'
        )
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================\n    # 8. 多格式數據匯出與高級下載面板 (完美融合版)\n    # ==========================================\n    st.write("---")
    st.subheader("📥 導出官方排班報告文件")
    
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    
    # Excel 導出
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
        st.session_state.roster_df.to_excel(writer, sheet_name='本週排班總表')
        st.session_state.report_df.to_excel(writer, sheet_name='工作負荷統計報告', index=False)
    dl_col1.download_button(
        label="🟢 下載 Excel 試算表 (.xlsx)",
        data=output_excel.getvalue(),
        file_name=f"SYSS_Prefect_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    # Markdown 導出
    md_data = "### Sing Yin Duty Roster\n\n" + st.session_state.roster_df.to_markdown()
    dl_col2.download_button(
        label="📝 下載 Markdown 文字檔 (.md)",
        data=md_data.encode('utf-8'),
        file_name=f"SYSS_Prefect_Roster_{datetime.date.today().strftime('%Y%m%d')}.md",
        mime="text/plain",
        use_container_width=True
    )
    
    # PDF / HTML 智慧降級導出
    report_bytes, file_type = generate_pdf_bytes(st.session_state.roster_df, st.session_state.report_df)
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

    # ==========================================\n    # 9. 智慧臨時替補機制 UI 區塊\n    # ==========================================\n    st.write("---")
    st.subheader("🩹 臨時請假緊急應變？智慧替補候選人建議")
    
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        chosen_day = st.selectbox("請假日期 (星期)", DAYS, key="sub_day_select")
    with sub_col2:
        chosen_role = st.selectbox("請假職位/房間區塊", COLUMNS_ROSTER, key="sub_role_select")
        
    current_person = str(st.session_state.roster_df.at[chosen_day, chosen_role]).strip()
    st.text_input(
        "當前被排定之人員", 
        value=current_person if current_person not in ["", "❌ 無合適人員"] else "（當前時段為空缺）", 
        disabled=True
    )
    
    if st.button("🔍 執行智慧篩選並推薦最優替補"):
        res_df, err = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
        if err:
            st.error(err)
        else:
            st.success(f"📋 依「總點數最少者優先」原則推薦之合格替補名單（已過濾當天已有職務者）：")
            st.dataframe(res_df, use_container_width=True, hide_index=True)
else:
    st.info("💡 提示：請先於左側邊欄上載 Prefects 原始資料名單以開啟自動排班功能。")
