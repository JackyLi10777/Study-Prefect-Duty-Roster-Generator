# app.py
# ==========================================
# Sing Yin Secondary School Study Prefect Duty Roster Platform
# 最終完整穩定版 v2.4 - 簡約大氣沉穩風格
# ==========================================
import streamlit as st
import pandas as pd
import base64
from datetime import datetime

# ==================== 匯入所有模組 ====================
from config import APP_TITLE, VERSION, DAYS, ROWS_ROSTER, NASA_COLORS, SCHOOL_EMAIL
from data import get_demo_dataframe_cached, get_sample_excel_bytes
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
if "students_df" not in st.session_state:
    st.session_state.students_df = pd.DataFrame()
if "roster_df" not in st.session_state:
    st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
if "logo_data" not in st.session_state:
    st.session_state.logo_data = None
if "leave_tracker_input" not in st.session_state:
    st.session_state.leave_tracker_input = []
if "master_report_df" not in st.session_state:
    st.session_state.master_report_df = pd.DataFrame()
if "manual_weights" not in st.session_state:
    st.session_state.manual_weights = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna(1.0)

# ==========================================
# 頁面設定
# ==========================================
st.set_page_config(page_title=APP_TITLE, page_icon="🦅", layout="wide")
st.markdown(f"""
<style>
    .main-title {{ color: #0F1C2E; font-size: 38px; font-weight: 700; }}
    .main-subtitle {{ color: #5C5C5C; font-size: 17px; }}
    .verse-card {{ background: linear-gradient(180deg, #0F1C2E, #1A2A3F); color: #E8D9B8; padding: 32px 28px; border-radius: 18px; text-align: center; line-height: 1.85; font-size: 20px; }}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">Sing Yin Study Prefect Duty Roster</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">F.3–F.5 Study Prefect Smart Scheduling Platform</p>', unsafe_allow_html=True)

# ==========================================
# 側邊欄（包含即時統計、AI導入、說明書入口）
# ==========================================
render_sidebar()

# ==========================================
# 每日聖經金句（神聖莊重）
# ==========================================
show_daily_verse()

# ==========================================
# 控制按鈕
# ==========================================
render_control_buttons()

# ==========================================
# 手動調整負荷面板（新功能）
# ==========================================
st.write("---")
st.subheader("⚖️ 手動調整本次值班負荷")
if not st.session_state.roster_df.empty:
    manual_edited = st.data_editor(
        st.session_state.manual_weights,
        use_container_width=True,
        num_rows="fixed",
        key="manual_weight_editor"
    )
    if not manual_edited.equals(st.session_state.manual_weights):
        st.session_state.manual_weights = manual_edited
        st.success("負荷已更新")
        st.rerun()

# ==========================================
# 排班表顯示
# ==========================================
if not st.session_state.roster_df.empty:
    tab_view, tab_edit = st.tabs(["📅 視覺公告版（沉穩專業）", "✏️ 手動修改版"])
    with tab_view:
        styled = render_streamlit_visual_roster(st.session_state.roster_df)
        st.dataframe(styled, use_container_width=True, height=420)
    with tab_edit:
        edited = st.data_editor(st.session_state.roster_df, use_container_width=True, key="roster_editor")
        if not edited.equals(st.session_state.roster_df):
            st.session_state.roster_df = edited
            st.rerun()

# ==========================================
# 智慧替補 + 即時統計
# ==========================================
st.write("---")
st.subheader("🔄 智慧替補推薦")
col1, col2 = st.columns(2)
with col1:
    chosen_day = st.selectbox("日期", DAYS, key="sub_day")
with col2:
    chosen_role = st.selectbox("崗位", ROWS_ROSTER, key="sub_role")
if st.button("🔍 尋找最優替補", type="primary", use_container_width=True):
    sub_df, msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
    if sub_df is not None:
        st.dataframe(sub_df, use_container_width=True, hide_index=True)
    else:
        st.warning(msg)

# 即時統計
if not st.session_state.master_report_df.empty:
    st.write("---")
    st.subheader("📊 即時累計統計")
    st.dataframe(st.session_state.master_report_df[["姓名", "最終總計加權負荷 (點)"]], use_container_width=True)

# ==========================================
# 使用說明書（內嵌）
# ==========================================
with st.expander("📖 使用說明書（v2.4）"):
    st.markdown(f"""
    **歡迎使用 Sing Yin Study Prefect Duty Roster Platform**

    1. 側邊欄 → 上傳名冊（支援 AI 智能解析）
    2. 設定請假名單
    3. 點擊「智能計算本週排班」
    4. 可在「手動修改版」直接編輯
    5. 可手動調整每次值班的負荷權重
    6. 匯出 PDF / Excel / 完整備份

    **有問題請 email**： {SCHOOL_EMAIL}

    版本：{VERSION}
    """)

# ==========================================
# 頁尾
# ==========================================
st.caption(f"{APP_TITLE} | {VERSION} | Sing Yin Secondary School")