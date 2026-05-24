# ui_components.py
import streamlit as st
import pandas as pd
import datetime
import io
import random
from config import DAYS, ROWS_ROSTER, VERSION, APP_TITLE
from core import generate_roster          # ← 修正 NameError
from utils import process_roster_import, export_system_backup, import_system_backup
from data import get_demo_dataframe, get_sample_format_dataframe
from ai_parser import ai_parse_remarks

def show_daily_verse():
    today = datetime.date.today().weekday()
    verse = DAILY_VERSES.get(today, DAILY_VERSES[0])
    st.markdown(f"""
    <div style="background:#F8F1E3;padding:20px;border-radius:12px;margin:20px 0;text-align:center;border-left:6px solid #D4AF37;">
        <h4 style="margin:0 0 8px 0;color:#0C2340;">📖 今日聖經金句</h4>
        <p style="font-size:16px;margin:0;color:#333;line-height:1.5;">{verse}</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.header("🏫 Sing Yin Secondary School")
        uploaded_logo = st.file_uploader("上傳校徽 (PNG)", type=["png"])
        if uploaded_logo:
            st.session_state.logo_data = uploaded_logo.getvalue()

        # ...（即時統計、名冊管理、AI 解析、請假登記、備份系統保持不變）
        # （完整內容與您上次已更新的版本相同）

        st.write("---")
        st.subheader("👥 名冊即時修改")
        st.session_state.students_df = st.data_editor(
            st.session_state.students_df,
            column_config={...},   # 與上次相同
            num_rows="dynamic", use_container_width=True, hide_index=True, key="student_editor_widget"
        )

        # 備份系統（已確認存在）
        st.write("---")
        st.subheader("💾 Cloud 備份系統")
        if st.button("⬇️ 導出完整備份 (JSON)", use_container_width=True):
            backup_json = export_system_backup(st.session_state.get("master_report_df", pd.DataFrame()))
            st.download_button("✅ 下載備份檔", backup_json, f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d')}.json", "application/json", use_container_width=True)

        uploaded_backup = st.file_uploader("上傳備份 JSON 還原", type=["json"], key="backup_importer")
        if uploaded_backup and st.button("🔄 還原備份", use_container_width=True):
            import_system_backup(uploaded_backup)

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
