# app.py
# ==========================================
# Sing Yin Secondary School Study Prefect Duty Roster Platform
# 最終完整穩定版 v2.4 - 簡約大氣沉穩風格
# ==========================================
import streamlit as st
import pandas as pd
import random
import plotly.express as px
from datetime import datetime

# 匯入所有模組
from config import DAYS, ROWS_ROSTER, VERSION, DAILY_VERSES, NASA_COLORS
from data import get_sample_excel_bytes
from ai_parser import smart_process_roster_import, ai_parse_remarks
from core import generate_roster, validate_and_compute, recommend_substitutes
from utils import (
    render_streamlit_visual_roster,
    generate_pdf,
    export_system_backup,
    import_system_backup,
    process_roster_import
)
from ui_components import render_sidebar, show_daily_verse, render_control_buttons

# ==========================================
# Session State 初始化
# ==========================================
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=["姓名", "年級", "班別", "職級", "固定總值班", "可用日子", "歷史累計(次)", "歷史動態(點)", "備註"])
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
if 'logo_data' not in st.session_state:
    st.session_state.logo_data = None
if 'leave_tracker_input' not in st.session_state:
    st.session_state.leave_tracker_input = []
if 'master_report_df' not in st.session_state:
    st.session_state.master_report_df = pd.DataFrame()
if 'show_clear_confirm' not in st.session_state:
    st.session_state.show_clear_confirm = False

# ==========================================
# 主程式
# ==========================================
st.set_page_config(
    page_title="Sing Yin Study Prefect Duty Roster",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 簡約沉穩 CSS
st.markdown("""
<style>
    .main { background-color: #F8F5F0; }
    .main-title { color: #0F1C2E; font-size: 38px; font-weight: 700; letter-spacing: 0.5px; }
    .main-subtitle { color: #5C5C5C; font-size: 17px; }
    .verse-card { 
        background: linear-gradient(180deg, #0F1C2E, #1A2A3F); 
        color: #E8D9B8; padding: 32px 28px; border-radius: 18px; 
        text-align: center; line-height: 1.85; font-size: 20px; 
        box-shadow: 0 10px 30px rgba(15,28,46,0.25); 
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">Sing Yin Study Prefect Duty Roster</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Smart Scheduling Platform</p>', unsafe_allow_html=True)

# 側邊欄
render_sidebar()

# 神聖每日金句
show_daily_verse()

# 控制按鈕
render_control_buttons()

# 驗證與警告
if not st.session_state.roster_df.empty:
    master_report, errors, warnings = validate_and_compute(
        st.session_state.roster_df, 
        st.session_state.students_df, 
        st.session_state.get("leave_tracker_input", [])
    )
    st.session_state.master_report_df = master_report

    if errors:
        st.error("⚠️ 發現問題：" + " | ".join(errors))
    if warnings:
        st.warning("💡 提醒：" + " | ".join(warnings))

# 雙軌呈現
tab_view, tab_edit = st.tabs(["📅 視覺公告版（沉穩專業）", "✏️ 手動修改版"])

with tab_view:
    if not st.session_state.roster_df.empty:
        styled = render_streamlit_visual_roster(st.session_state.roster_df)
        st.dataframe(styled, use_container_width=True, height=420)
    else:
        st.info("尚未生成排班表")

with tab_edit:
    if not st.session_state.roster_df.empty:
        edited = st.data_editor(
            st.session_state.roster_df,
            use_container_width=True,
            num_rows="fixed",
            key="roster_editor"
        )
        if not edited.equals(st.session_state.roster_df):
            st.session_state.roster_df = edited
            st.success("已更新排班表")
            st.rerun()
    else:
        st.info("尚未生成排班表")

# 智慧替補
st.write("---")
st.subheader("🔄 智慧替補推薦")
col_day, col_role = st.columns(2)
with col_day:
    chosen_day = st.selectbox("日期", DAYS, key="sub_day")
with col_role:
    chosen_role = st.selectbox("崗位", ROWS_ROSTER, key="sub_role")

if st.button("🔍 尋找最優替補", type="primary", use_container_width=True):
    sub_df, msg = recommend_substitutes(
        st.session_state.roster_df,
        st.session_state.students_df,
        chosen_day,
        chosen_role
    )
    if sub_df is not None:
        st.success("推薦替補（按總負荷由低到高）")
        st.dataframe(sub_df, use_container_width=True, hide_index=True)
    else:
        st.warning(msg)

# 累計統計圖表
if not st.session_state.master_report_df.empty:
    st.write("---")
    st.subheader("📊 全體累積工作負荷監控")
    fig = px.bar(
        st.session_state.master_report_df,
        x='姓名',
        y='最終總計加權負荷 (點)',
        color='最終總計加權負荷 (點)',
        color_continuous_scale='YlOrBr',
        text_auto='.1f'
    )
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)

# 快速匯出
st.write("---")
st.subheader("📤 快速匯出")
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("📄 匯出 PDF", use_container_width=True):
        pdf_bytes = generate_pdf(
            st.session_state.roster_df,
            st.session_state.master_report_df,
            base64.b64encode(st.session_state.logo_data).decode() if st.session_state.logo_data else None
        )
        st.download_button("下載 PDF", pdf_bytes, "SYSS_Duty_Roster.pdf", "application/pdf", use_container_width=True)
with c2:
    if st.button("📊 匯出 Excel", use_container_width=True):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.roster_df.to_excel(writer, sheet_name="排班表")
            st.session_state.master_report_df.to_excel(writer, sheet_name="累計負荷", index=False)
        st.download_button("下載 Excel", output.getvalue(), "SYSS_Roster.xlsx", use_container_width=True)
with c3:
    export_system_backup()
with c4:
    uploaded_backup = st.file_uploader("還原備份", type=["json"], key="backup_restore")
    if uploaded_backup:
        import_system_backup(uploaded_backup)

st.caption(f"Sing Yin Secondary School Study Prefect Platform | {VERSION}")