# app.py
import streamlit as st
import pandas as pd
import random
import plotly.express as px
import datetime
import io
import json

# 匯入所有模組
from config import DAYS, ROWS_ROSTER, WEIGHTS, VERSION, APP_TITLE
from core import generate_roster, validate_and_compute, recommend_substitutes
from utils import generate_pdf, export_system_backup, import_system_backup, process_roster_import
from ui_components import render_sidebar, show_daily_verse, render_control_buttons

# ==========================================
# Session State 初始化
# ==========================================
if 'students_df' not in st.session_state:
    st.session_state.students_df = pd.DataFrame(columns=["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"])
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
if 'logo_data' not in st.session_state:
    st.session_state.logo_data = None
if 'show_clear_confirm' not in st.session_state:
    st.session_state.show_clear_confirm = False
if 'leave_tracker_input' not in st.session_state:
    st.session_state.leave_tracker_input = []
if 'master_report_df' not in st.session_state:
    st.session_state.master_report_df = pd.DataFrame()

# ==========================================
# 主程式
# ==========================================
def main():
    # 側邊欄（包含所有管理功能）
    render_sidebar()

    # 主畫面標題與每日金句
    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)
    show_daily_verse()

    # 生成排班按鈕與特殊不開放設定
    selected_closures = render_control_buttons()

    # 驗證與統計
    leave_students = st.session_state.leave_tracker_input
    audit_results = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
    st.session_state.master_report_df = audit_results["report_df"]

    # 安全提示
    if audit_results["typo"][0]:
        st.markdown('<div class="danger-alert"><b>⚠️ 數據不符警告：</b>手動輸入了名冊之外的姓名。<br>' + '<br>'.join(audit_results["typo"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["duplicate"][0]:
        st.markdown('<div class="danger-alert"><b>⚠️ 分身重複衝突警告：</b><br>' + '<br>'.join(audit_results["duplicate"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["leave_conflict"][0]:
        st.markdown('<div class="danger-alert"><b>🛑 請假人員衝突警告：</b><br>' + '<br>'.join(audit_results["leave_conflict"][1]) + '</div>', unsafe_allow_html=True)
        if st.button("🩹 一鍵將請假同學從現有值班表中移出", type="primary"):
            for d in DAYS:
                for r in ROWS_ROSTER:
                    if str(st.session_state.roster_df.at[r, d]).strip() in leave_students:
                        st.session_state.roster_df.at[r, d] = ""
            st.success("✅ 已自動清除請假同學！")
            st.rerun()
    elif audit_results["vacuum"][0]:
        st.markdown('<div class="warning-alert"><b>💡 提示：存在未配對的開門空缺：</b><br>' + '<br>'.join(audit_results["vacuum"][1]) + '</div>', unsafe_allow_html=True)

    # 雙軌呈現
    st.write("---")
    st.subheader("📅 本週班表狀態與動態調整通道")
    tab_view, tab_edit = st.tabs(["📅 奢華藍金值班表 (視覺公告版)", "✏️ 互動式手動修改 (動態校準版)"])

    def apply_cell_style(val, role, day):
        val = str(val).strip()
        if val == "X": return "color: #EF4444; font-weight: bold; text-align: center; background-color: #FEF2F2;"
        if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
            return "background-color: #E5E7EB; color: #9CA3AF; text-align: center; font-style: italic;"
        if val == "": return "background-color: #F9FAFB;"
        base = "font-weight: bold; text-align: center;"
        if "Assist" in role: return base + " background-color: #FFF8E1; color: #B45309; border: 1px solid #D4AF37;"
        if "Room302" in role: return base + " background-color: #D1FAE5; color: #166534; border: 1px solid #10B981;"
        if "Room303" in role: return base + " background-color: #FEE2E2; color: #991B1B; border: 1px solid #EF4444;"
        if "Room202" in role: return base + " background-color: #DBEAFE; color: #1E40AF; border: 1px solid #3B82F6;"
        return base

    with tab_view:
        try:
            styled_roster = st.session_state.roster_df.style.apply(
                lambda row: [apply_cell_style(val, row.name, col) for col, val in row.items()], axis=1
            )
            st.dataframe(styled_roster, use_container_width=True, height=320)
        except Exception:
            st.dataframe(st.session_state.roster_df, use_container_width=True, height=320)

    with tab_edit:
        st.markdown("<p style='font-size:13px; color:#666;'>💡 您可以直接在下方表格內手動修改或填入人名，輸入 <b>X</b> 代表鎖定該不開放時段：</p>", unsafe_allow_html=True)
        edited_roster_df = st.data_editor(
            st.session_state.roster_df,
            use_container_width=True,
            key="main_roster_editor_widget"
        )
        if not edited_roster_df.equals(st.session_state.roster_df):
            st.session_state.roster_df = edited_roster_df
            st.rerun()

    # 工作量圖表
    st.write("---")
    st.subheader("📊 全體累積工作點數公平性動態監控天平")
    if not st.session_state.master_report_df.empty:
        fig = px.bar(
            st.session_state.master_report_df,
            x='學生姓名 (Prefect Name)',
            y='最終總計加權負荷 (點)',
            text_auto='.1f',
            color='最終總計加權負荷 (點)',
            color_continuous_scale='gold'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 智慧替補
    st.write("---")
    st.subheader("🔍 臨時請假？智慧替補候選人精準建議")
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        chosen_day = st.selectbox("請假或替換日期", DAYS, key="sub_day_selector")
    with sub_col2:
        chosen_role = st.selectbox("請假或替換職位/房間", ROWS_ROSTER, key="sub_role_selector")

    current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
    st.text_input("目前該時段人員", value=current_person if current_person not in ["", "X"] else "（無人）", disabled=True)

    if st.button("🔍 尋找最優替補", type="primary", use_container_width=True):
        sub_df, msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
        if sub_df is not None:
            st.success("📋 推薦替補名單")
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
        else:
            st.warning(msg)

    st.caption(f"Sing Yin Secondary School Study Prefect Platform | {VERSION}")

if __name__ == "__main__":
    main()
