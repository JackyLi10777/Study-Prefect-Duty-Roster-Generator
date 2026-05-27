# ui_components.py
import streamlit as st
import pandas as pd
import random
import datetime

from config import DAYS, ROWS_ROSTER, DAILY_VERSES, VERSION, SCHOOL_EMAIL
from data import get_demo_dataframe, get_sample_excel_bytes
from utils import export_system_backup, import_system_backup, process_roster_import, smart_process_roster_import, render_streamlit_visual_roster
from core import generate_roster

# ==========================================
# 側邊欄渲染（舊版完整 UI 功能補回）
# ==========================================
def render_sidebar():
    """
    完整側邊欄介面，包含名冊管理、AI/傳統導入、即時編輯、請假登記、備份還原等舊版所有功能。
    """
    st.sidebar.header("🛠️ 系統控制面板")

    # 名冊管理區塊
    st.sidebar.subheader("📋 Prefect 名冊管理")
    uploaded_roster = st.sidebar.file_uploader(
        "上傳 Prefect 名冊 (Excel/CSV)", 
        type=["csv", "xlsx", "xls"], 
        key="roster_uploader"
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.sidebar.button("🤖 AI 智能導入", use_container_width=True):
            if uploaded_roster is not None:
                smart_process_roster_import(uploaded_roster)
            else:
                st.sidebar.warning("請先上傳檔案")
    with col2:
        if st.sidebar.button("📥 傳統格式導入", use_container_width=True):
            if uploaded_roster is not None:
                process_roster_import(uploaded_roster)
            else:
                st.sidebar.warning("請先上傳檔案")

    # 下載範例檔
    if st.sidebar.button("📥 下載名冊格式範例", use_container_width=True):
        bytes_data = get_sample_excel_bytes()
        st.sidebar.download_button(
            label="✅ 下載範例 Excel",
            data=bytes_data,
            file_name="Prefect_名冊導入格式範例.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # 名冊即時編輯
    st.sidebar.subheader("✏️ 名冊即時編輯")
    if not st.session_state.students_df.empty:
        edited_df = st.sidebar.data_editor(
            st.session_state.students_df,
            use_container_width=True,
            hide_index=True,
            key="student_editor"
        )
        if not edited_df.equals(st.session_state.students_df):
            st.session_state.students_df = edited_df
            st.sidebar.success("名冊已更新")
            st.rerun()

    # 請假追蹤
    st.sidebar.subheader("🛡️ 請假登記")
    leave_input = st.sidebar.text_area(
        "輸入請假同學姓名（每行一位）",
        value="\n".join(st.session_state.get("leave_tracker_input", [])),
        key="leave_input"
    )
    if st.sidebar.button("✅ 儲存請假名單"):
        st.session_state.leave_tracker_input = [line.strip() for line in leave_input.split("\n") if line.strip()]
        st.sidebar.success("請假名單已儲存")

    # 備份還原
    st.sidebar.subheader("💾 Cloud 備份")
    col_backup1, col_backup2 = st.sidebar.columns(2)
    with col_backup1:
        if st.sidebar.button("📤 匯出備份"):
            if not st.session_state.get("master_report_df", pd.DataFrame()).empty:
                backup_str = export_system_backup(st.session_state.master_report_df)
                st.sidebar.download_button(
                    "下載備份 JSON",
                    backup_str,
                    f"backup_{datetime.date.today().strftime('%Y%m%d')}.json",
                    "application/json",
                    use_container_width=True
                )
    with col_backup2:
        uploaded_backup = st.sidebar.file_uploader("上傳備份 JSON", type=["json"], key="backup_uploader")
        if uploaded_backup is not None and st.sidebar.button("📥 還原備份"):
            import_system_backup(uploaded_backup)

    st.sidebar.caption(f"版本 {VERSION}")

# ==========================================
# 每日聖經金句顯示（舊版功能完整保留）
# ==========================================
def show_daily_verse():
    """
    顯示每日聖經金句（舊版每日靈修功能完整保留）
    """
    today = datetime.date.today().weekday()
    verses = DAILY_VERSES.get(today, DAILY_VERSES[0])
    verse = random.choice(verses)
    st.markdown(f"""
    <div style="background-color:#0B1E3D; color:#D4AF37; padding:15px; border-radius:10px; text-align:center; margin:10px 0;">
        <strong>📖 今日金句</strong><br>
        {verse}
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 控制按鈕區塊（舊版所有控制功能完整保留）
# ==========================================
def render_control_buttons():
    """
    主畫面控制按鈕區塊，包含生成、清空、重置、匯出等舊版核心功能。
    """
    st.subheader("🎛️ 排班控制")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚀 智能計算：生成本週全新公平值班表", type="primary", use_container_width=True):
            st.session_state.roster_df = generate_roster(
                st.session_state.students_df,
                st.session_state.get("leave_tracker_input", []),
                seed=random.randint(10000, 99999)
            )
            st.success("✅ 值班表已生成！")
            st.rerun()

    with col2:
        if st.button("🧹 一鍵清空本週排班表", use_container_width=True):
            st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
            st.success("✅ 排班表已清空")
            st.rerun()

    with col3:
        if st.button("🔄 重置所有手動調整", use_container_width=True):
            st.session_state.manual_weights = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)
            st.success("✅ 手動調整已重置")
            st.rerun()

    return None