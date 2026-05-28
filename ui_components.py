# ui_components.py
import streamlit as st
import pandas as pd
import random
import base64
from io import BytesIO
from datetime import datetime
from config import DAYS, ROWS_ROSTER, VERSION, DAILY_VERSES
from data import get_sample_excel_bytes
from ai_parser import smart_process_roster_import, ai_parse_remarks
from utils import export_system_backup, import_system_backup

def render_sidebar():
    """側邊欄 - 簡約沉穩風格"""
    st.sidebar.title("⚙️ 控制面板")

    # 校徽上傳
    st.sidebar.subheader("🦅 校徽")
    logo_file = st.sidebar.file_uploader("上傳學校校徽 (PNG)", type=["png"], key="logo_uploader")
    if logo_file:
        st.session_state.logo_data = logo_file.getvalue()
        st.sidebar.image(logo_file, caption="已上傳校徽", use_column_width=True)
    elif st.session_state.get("logo_data"):
        st.sidebar.image(BytesIO(st.session_state.logo_data), caption="目前校徽", use_column_width=True)

    # 名冊管理
    st.sidebar.subheader("📋 名冊管理")
    uploaded = st.sidebar.file_uploader("上傳 Prefect 名冊", type=["xlsx", "csv"], key="roster_uploader")
    if uploaded:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🤖 AI 智能解析", use_container_width=True):
                st.session_state.students_df = smart_process_roster_import(uploaded)
                st.success("AI 解析完成")
        with col2:
            if st.button("📥 傳統解析", use_container_width=True):
                st.session_state.students_df = process_roster_import(uploaded)   # 請確保 app.py 中有此函數

    if st.sidebar.button("📥 下載名冊格式範例", use_container_width=True):
        st.sidebar.download_button(
            label="下載 Excel 範例",
            data=get_sample_excel_bytes(),
            file_name="Prefect_名冊格式範例.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # 請假登記（多選下拉 + 手動輸入）
    st.sidebar.subheader("🛑 請假登記")
    if "students_df" in st.session_state and not st.session_state.students_df.empty:
        all_names = sorted(st.session_state.students_df["姓名"].tolist())
        selected = st.sidebar.multiselect(
            "選擇請假同學",
            options=all_names,
            default=st.session_state.get("leave_tracker_input", []),
            key="leave_multiselect"
        )
    else:
        selected = []
    
    manual = st.sidebar.text_input("或手動輸入姓名（逗號分隔）", value="")
    if st.sidebar.button("✅ 確認請假名單", use_container_width=True):
        combined = list(dict.fromkeys(selected + [x.strip() for x in manual.split(",") if x.strip()]))
        st.session_state.leave_tracker_input = combined
        st.success(f"已登記 {len(combined)} 位請假同學")

    # AI 分析備註
    st.sidebar.subheader("🔍 AI 分析備註")
    if st.sidebar.button("🤖 AI 自動解析所有備註", use_container_width=True):
        if "students_df" in st.session_state and not st.session_state.students_df.empty:
            with st.spinner("AI 解析中..."):
                st.session_state.students_df = ai_parse_remarks(st.session_state.students_df)
            st.success("AI 已完成備註解析")
            st.rerun()

    # 即時累計指數（已還原）
    st.sidebar.write("---")
    st.sidebar.subheader("📊 即時累計指數")
    if "master_report_df" in st.session_state and not st.session_state.master_report_df.empty:
        total = st.session_state.master_report_df["最終總計加權負荷 (點)"].sum()
        st.sidebar.metric("全體總負荷點數", f"{total:.1f} 點")
        st.sidebar.dataframe(
            st.session_state.master_report_df[["學生姓名 (Prefect Name)", "最終總計加權負荷 (點)"]],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.sidebar.info("尚未生成排班表")

    # 備份還原
    st.sidebar.write("---")
    if st.sidebar.button("📤 匯出完整備份", use_container_width=True):
        export_system_backup()
    uploaded_backup = st.sidebar.file_uploader("📥 還原備份", type=["json"], key="backup_uploader")
    if uploaded_backup and st.sidebar.button("還原備份", use_container_width=True):
        import_system_backup(uploaded_backup)


def show_daily_verse():
    """每日聖經金句 - 神聖莊重版"""
    st.subheader("📖 每日聖經金句")
    
    if "current_verse_index" not in st.session_state:
        st.session_state.current_verse_index = random.randint(0, len(DAILY_VERSES[0]) - 1)
    
    today = datetime.today().weekday()
    verses = DAILY_VERSES.get(today, DAILY_VERSES[0])
    current = verses[st.session_state.current_verse_index]
    
    st.markdown(f"""
    <div class="verse-card">
        {current}
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 換一句金句", use_container_width=True, type="secondary"):
        st.session_state.current_verse_index = random.randint(0, len(verses) - 1)
        st.rerun()


def render_control_buttons():
    """控制按鈕區"""
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚀 智能計算本週排班", type="primary", use_container_width=True):
            st.session_state.roster_df = generate_roster(st.session_state.students_df, st.session_state.get("leave_tracker_input", []))
            st.success("排班表已生成")
            st.rerun()
    with col2:
        if st.button("🧹 一鍵清空本週排班", type="secondary", use_container_width=True):
            st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
            st.success("已清空本週排班表")
            st.rerun()
    with col3:
        if st.button("🔄 重置所有數據", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key != "logo_data":
                    del st.session_state[key]
            st.success("所有數據已重置")
            st.rerun()