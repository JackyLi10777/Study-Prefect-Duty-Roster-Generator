# app.py
"""
聖言中學導學風紀當值排班平台
Sing Yin Secondary School Study Prefect Duty Roster Platform
最終主程式（v2.3 Final）

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
"""

import streamlit as st
import pandas as pd
import json
import datetime
from typing import Optional

# ====================== 導入所有模組 ======================
from config import (
    APP_TITLE, PROJECT_FULL_NAME, VERSION, DAYS, ROWS_ROSTER,
    DAILY_VERSES, NASA_COLORS, get_role_style
)
from data import get_demo_dataframe, initialize_session_state
from ai_parser import ai_parse_remarks, get_column_mapping_from_ai
from core import generate_roster, validate_and_compute, recommend_substitutes
from utils import (
    generate_pdf, export_to_excel, export_to_markdown,
    export_system_backup, import_system_backup, process_roster_import
)
from ui_components import (
    display_colored_roster,
    student_management_panel,
    global_multiplier_slider,
    substitute_recommendation_panel,
    download_section
)

# ====================== 頁面設定 ======================
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== 初始化 Session State ======================
initialize_session_state()

# ====================== 側邊欄 ======================
with st.sidebar:
    st.title("🛡️ 導學風紀")
    st.caption(f"**{PROJECT_FULL_NAME}**  v{VERSION}")

    # 每日金句
    today = datetime.date.today().weekday() % 5
    verse_list = DAILY_VERSES.get(today, ["「你要專心仰賴耶和華...」——箴言 3:5"])
    verse = verse_list[0] if isinstance(verse_list, list) else str(verse_list)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1C2526, #2C3E50); 
                color:#F4D03F; padding:15px; border-radius:12px; text-align:center;">
        <strong>今日金句</strong><br>
        {verse}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    menu = st.radio(
        "功能選單",
        [
            "🏠 儀表板",
            "👥 學生名冊",
            "📅 排班生成",
            "🤖 AI 匯入",
            "🔄 智慧替補",
            "📤 下載中心",
            "💾 系統備份"
        ],
        label_visibility="collapsed"
    )

    st.divider()
    st.caption("由 Head Study Prefect 26-27 LI Chuangjie Jacky 製作")

# ====================== 主頁面 ======================
st.title(f"🛡️ {APP_TITLE}")
st.markdown("### 聖言中學導學風紀當值排班平台")

if menu == "🏠 儀表板":
    st.success(f"✅ 系統運作正常 | 目前共有 {len(st.session_state.students_df)} 位風紀")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("總學生數", len(st.session_state.students_df))
    with col2:
        st.metric("目前全局倍率", f"{st.session_state.get('global_load_multiplier', 1.0)}×")
    with col3:
        if "roster_df" in st.session_state and not st.session_state.roster_df.empty:
            st.metric("已生成排班", "✅ 完整")
        else:
            st.metric("已生成排班", "❌ 尚未")

    if "roster_df" in st.session_state and not st.session_state.roster_df.empty:
        st.subheader("最新排班表預覽")
        display_colored_roster(st.session_state.roster_df)

elif menu == "👥 學生名冊":
    st.session_state.students_df = student_management_panel(st.session_state.students_df)

elif menu == "📅 排班生成":
    st.subheader("🎯 手動生成排班")
    
    # 正確處理全局負荷滑桿（已修正 widget 衝突）
    multiplier = global_multiplier_slider()
    
    if "global_load_multiplier" not in st.session_state or st.session_state.global_load_multiplier != multiplier:
        st.session_state.global_load_multiplier = multiplier

    if st.button("🚀 立即生成最新排班表", type="primary", use_container_width=True):
        with st.spinner("正在使用公平演算法生成排班..."):
            roster = generate_roster(st.session_state.students_df, multiplier)
            audit = validate_and_compute(roster, st.session_state.students_df)
            st.session_state.roster_df = roster
            st.session_state.audit_report = audit["report_df"]
        st.success("✅ 排班表生成完成！")
        st.rerun()

    if "roster_df" in st.session_state and not st.session_state.roster_df.empty:
        display_colored_roster(st.session_state.roster_df)

elif menu == "🤖 AI 匯入":
    st.subheader("🤖 AI 輔助匯入")
    uploaded_file = st.file_uploader("上傳 Excel / CSV / JSON 備份", 
                                   type=["xlsx", "xls", "csv", "json"])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.json'):
            backup = json.loads(uploaded_file.getvalue().decode())
            if import_system_backup(backup):
                st.success("✅ 完整系統備份還原成功！")
                st.rerun()
        else:
            df = process_roster_import(uploaded_file)
            if df is not None:
                st.session_state.students_df = df
                st.success("✅ 已成功匯入學生資料")

elif menu == "🔄 智慧替補":
    if "roster_df" in st.session_state and not st.session_state.roster_df.empty:
        substitute_recommendation_panel(st.session_state.roster_df, st.session_state.students_df)
    else:
        st.info("請先在「排班生成」頁面產生排班表")

elif menu == "📤 下載中心":
    if "roster_df" in st.session_state and not st.session_state.roster_df.empty:
        report = st.session_state.get("audit_report", pd.DataFrame())
        download_section(st.session_state.roster_df, report, st.session_state.get("global_load_multiplier", 1.0))
    else:
        st.warning("尚未生成排班表，無法下載")

elif menu == "💾 系統備份":
    st.subheader("💾 完整系統備份 / 還原")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 匯出目前完整備份", use_container_width=True):
            backup = export_system_backup()
            st.download_button(
                label="下載 JSON 備份",
                data=json.dumps(backup, ensure_ascii=False, indent=2),
                file_name=f"SYSS_備份_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_backup = st.file_uploader("📥 上傳備份檔案還原", type=["json"])
        if uploaded_backup:
            backup_data = json.loads(uploaded_backup.getvalue().decode())
            if import_system_backup(backup_data):
                st.success("✅ 系統已成功還原！")
                st.rerun()

st.caption(f"© 2026 聖言中學導學風紀 | v{VERSION} | 由 Jacky Li 開發")