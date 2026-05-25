# ui_components.py
import streamlit as st
import pandas as pd
import datetime
import io
import random

from config import DAYS, ROWS_ROSTER, DAILY_VERSES, VERSION, APP_TITLE

# 如果 config.py 中沒有 ALL_VERSES，則在這裡建立（防止 ImportError）
if "ALL_VERSES" not in globals():
    ALL_VERSES = []
    for day_list in DAILY_VERSES.values():
        ALL_VERSES.extend(day_list)

from core import generate_roster
from utils import process_roster_import, export_system_backup, import_system_backup
from data import get_demo_dataframe, get_sample_format_dataframe
from ai_parser import ai_parse_remarks

def show_daily_verse():
    if "current_verse" not in st.session_state or st.session_state.current_verse is None:
        st.session_state.current_verse = random.choice(ALL_VERSES)

    st.markdown(f"""
    <div style="background:#F8F1E3;padding:20px;border-radius:12px;margin:20px 0;text-align:center;border-left:6px solid #D4AF37;">
        <h4 style="margin:0 0 8px 0;color:#0C2340;">📖 今日聖經金句</h4>
        <p style="font-size:16px;margin:0;color:#333;line-height:1.5;">{st.session_state.current_verse}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 刷新金句", use_container_width=True):
        st.session_state.current_verse = random.choice(ALL_VERSES)
        st.rerun()

def render_sidebar():
    with st.sidebar:
        st.header("🏫 Sing Yin Secondary School")
        
        show_logo = st.checkbox("🖼️ 顯示校徽（畫面與 PDF）", value=True, key="show_logo_toggle")
        
        uploaded_logo = st.file_uploader("上傳自訂校徽 (PNG)（可選）", type=["png"], key="logo_uploader")
        if uploaded_logo:
            st.session_state.logo_data = uploaded_logo.getvalue()
            st.success("✅ 已使用自訂校徽")
        elif show_logo and "logo_data" not in st.session_state:
            try:
                with open("logo.png", "rb") as f:
                    st.session_state.logo_data = f.read()
            except FileNotFoundError:
                st.info("💡 請將 logo.png 放到 GitHub 專案根目錄")

        st.write("---")
        st.subheader("📊 即時統計")
        if not st.session_state.students_df.empty:
            total = len(st.session_state.students_df)
            total_points = st.session_state.students_df["history_weight"].sum()
            avg = round(total_points / total, 1) if total > 0 else 0
            st.metric("總領袖生", total)
            st.metric("累計點數", f"{total_points:.1f}")
            st.metric("平均負荷", f"{avg:.1f} 點")
        else:
            st.info("尚未載入名冊")

        st.write("---")
        st.subheader("🗄️ 名冊管理")
        if st.button("💡 一鍵載入官方示範名冊", use_container_width=True):
            st.session_state.students_df = get_demo_dataframe()
            st.success("✅ 示範名冊已載入")
            st.rerun()

        if st.button("📥 下載名冊格式範例", use_container_width=True):
            sample_df = get_sample_format_dataframe()
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                sample_df.to_excel(writer, index=False)
            st.download_button("✅ 下載範例檔", output.getvalue(), "Prefect_名冊格式範例.xlsx", use_container_width=True)

        uploaded_roster = st.file_uploader("上傳名冊 (Excel/CSV)", type=["csv", "xlsx", "xls"], key="roster_importer")
        if uploaded_roster and st.button("確認導入", use_container_width=True):
            process_roster_import(uploaded_roster)

        st.write("---")
        st.subheader("👥 名冊即時修改")
        st.caption("直接在此編輯所有資料")
        st.session_state.students_df = st.data_editor(
            st.session_state.students_df,
            column_config={
                "name": st.column_config.TextColumn("姓名 *", required=True),
                "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5"]),
                "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"]),
                "fixed_general_duty": st.column_config.SelectboxColumn("學年固定總值班", options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]),
                "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
                "history_duties": st.column_config.NumberColumn("歷史累計(次)", min_value=0, step=1),
                "history_weight": st.column_config.NumberColumn("歷史動態(點)", min_value=0.0, step=0.5),
                "remarks": st.column_config.TextColumn("備註")
            },
            num_rows="dynamic", use_container_width=True, hide_index=True, key="student_editor_widget"
        )

        st.write("---")
        st.subheader("🤖 AI 智能解析")
        if st.button("🚀 執行 AI 解析 Remarks", use_container_width=True):
            with st.spinner("AI 解析中..."):
                updated_df = ai_parse_remarks(st.session_state.students_df)
                st.session_state.students_df = updated_df
                st.success("✅ AI 已自動更新固定值班、可用日子、職級等欄位")
                st.rerun()

        st.write("---")
        st.subheader("🛑 請假登記")
        valid_names = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
        st.session_state.leave_tracker_input = st.multiselect("選取今日請假人員", options=valid_names)

        st.write("---")
        st.subheader("💾 Cloud 備份系統")
        st.caption("解決 Streamlit Cloud 休眠重置問題")
        if st.button("⬇️ 導出完整備份 (JSON)", use_container_width=True):
            backup_json = export_system_backup(st.session_state.get("master_report_df", pd.DataFrame()))
            st.download_button("✅ 下載備份檔", backup_json, f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d')}.json", "application/json", use_container_width=True)

        uploaded_backup = st.file_uploader("上傳備份 JSON 還原", type=["json"], key="backup_importer")
        if uploaded_backup and st.button("🔄 還原備份", use_container_width=True):
            import_system_backup(uploaded_backup)

        st.caption("💡 每次生成班表後建議立即備份")

def render_control_buttons():
    closure_options = [f"{d} - {room}" for d in DAYS for room in ["Room302", "Room303", "Room202"] if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"])]
    selected_closures = st.multiselect("🛠️ 本週特殊不開放時段", options=closure_options, key="special_closures")

    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    with col1:
        if st.button("🚀 智能計算：生成本週全新公平值班表", type="primary", use_container_width=True):
            with st.spinner("計算中..."):
                seed = random.randint(10000, 99999)
                st.session_state.roster_df = generate_roster(
                    st.session_state.students_df, 
                    st.session_state.leave_tracker_input, 
                    selected_closures, 
                    seed
                )
                st.success(f"✅ 排班完成！驗證碼: SY-{seed}")

    with col2:
        if st.button("🗑️ 一鍵清空本週排班", type="secondary", use_container_width=True):
            st.session_state.show_clear_confirm = True

    if st.session_state.get("show_clear_confirm", False):
        st.markdown('<div class="warning-alert"><b>⚠️ 確定要清除全部排班？此操作無法復原！</b></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("💥 確定清空", type="primary"):
            st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
            st.session_state.show_clear_confirm = False
            st.rerun()
        if c2.button("❌ 取消"):
            st.session_state.show_clear_confirm = False
            st.rerun()

    return selected_closures
