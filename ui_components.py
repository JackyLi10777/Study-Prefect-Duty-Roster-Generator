# ui_components.py
import streamlit as st
import pandas as pd
import datetime
import io
import random

from config import DAYS, ROWS_ROSTER, DAILY_VERSES, VERSION, APP_TITLE
from core import generate_roster
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
        
        # === 新增：校徽顯示開關 + GitHub 預設 ===
        show_logo = st.checkbox("🖼️ 顯示校徽（PDF與畫面）", value=True, key="show_logo_toggle")
        
        # 如果使用者想上傳自訂校徽，仍然保留原功能
        uploaded_logo = st.file_uploader("上傳自訂校徽 (PNG)（可選）", type=["png"], key="logo_uploader")
        if uploaded_logo:
            st.session_state.logo_data = uploaded_logo.getvalue()
            st.success("✅ 已使用自訂校徽")
        elif show_logo and "logo_data" not in st.session_state:
            # GitHub 預設校徽（放在 repo 根目錄的 logo.png）
            try:
                with open("logo.png", "rb") as f:
                    st.session_state.logo_data = f.read()
            except FileNotFoundError:
                st.info("💡 請將 logo.png 放到 GitHub 專案根目錄")

        # 其餘側邊欄內容（統計、名冊管理、AI、請假、備份）保持不變
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

        # ...（名冊管理、AI 解析、請假登記、備份系統的程式碼與上次相同，請保留原內容）

        st.write("---")
        st.subheader("💾 Cloud 備份系統")
        # （備份部分程式碼與上次相同）

        st.caption("Sing Yin Secondary School Study Prefect Platform | v1.3")
