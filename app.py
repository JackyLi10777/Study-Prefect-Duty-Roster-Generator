# app.py
import streamlit as st
import pandas as pd
import random
import plotly.express as px
import datetime
import io

from config import DAYS, ROWS_ROSTER, VERSION, APP_TITLE
from core import generate_roster, validate_and_compute, recommend_substitutes
from utils import generate_pdf, export_system_backup, import_system_backup, process_roster_import
from ui_components import render_sidebar, show_daily_verse, render_control_buttons

# Session State
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"])
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
if 'logo_data' not in st.session_state:
    st.session_state.logo_data = None
if 'leave_tracker_input' not in st.session_state:
    st.session_state.leave_tracker_input = []

def main():
    render_sidebar()                     # 側邊欄（含備份導入）
    
    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)
    show_daily_verse()

    selected_closures = render_control_buttons()

    # 驗證
    audit = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, st.session_state.leave_tracker_input)
    master_report_df = audit["report_df"]

    # 提示
    if audit["typo"][0] or audit["duplicate"][0] or audit["leave_conflict"][0]:
        st.warning("⚠️ 請檢查上方提示")

    # 值班表
    st.write("---")
    st.subheader("📅 本週值班表")
    tab1, tab2 = st.tabs(["📅 視覺公告版", "✏️ 手動編輯版"])
    with tab1:
        st.dataframe(st.session_state.roster_df.style.apply(lambda row: [apply_cell_style(val, row.name, col) for col, val in row.items()], axis=1), use_container_width=True, height=320)
    with tab2:
        st.session_state.roster_df = st.data_editor(st.session_state.roster_df, use_container_width=True)

    # 圖表與替補、導出（略）... 為了簡潔，此處省略完整程式碼

    st.caption(f"Sing Yin Study Prefect Platform | {VERSION}")

def apply_cell_style(val, role, day):
    # （樣式函數，保持不變）
    val = str(val).strip()
    if val == "X": return "color:#EF4444; font-weight:bold; background:#FEF2F2;"
    if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']: return "background:#E5E7EB; color:#9CA3AF;"
    if val == "": return "background:#F9FAFB;"
    base = "font-weight:bold; text-align:center;"
    if "Assist" in role: return base + "background:#FFF8E1; color:#B45309;"
    if "Room302" in role: return base + "background:#D1FAE5; color:#166534;"
    if "Room303" in role: return base + "background:#FEE2E2; color:#991B1B;"
    if "Room202" in role: return base + "background:#DBEAFE; color:#1E40AF;"
    return base

if __name__ == "__main__":
    main()
