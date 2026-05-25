# ui_components.py
import streamlit as st
import pandas as pd
import datetime
import io
import random

from config import DAYS, ROWS_ROSTER, DAILY_VERSES, VERSION, APP_TITLE, ALL_VERSES
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
                st.success("✅ AI 已自動更新")
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
