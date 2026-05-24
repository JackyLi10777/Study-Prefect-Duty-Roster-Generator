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
# 使用說明書（已完整恢復）
# ==========================================
HELP_TEXT = """
# 📖 Sing Yin Study Prefect Duty Roster 使用說明書  
**版本**：v1.3 模組化最終版  
**更新日期**：2026 年 5 月 25 日  

**適用對象**：Study Prefect Team Advisor、Head Study Prefect、Assistant Head Study Prefect

### 主要功能
- 智能公平排班（考慮歷史負荷、可用日子、老帶新、固定總值班）
- AI 智能解析 Remarks（自動更新固定值班、可用日子、職級）
- 每日聖經金句
- 彩色 PDF 公告班表
- 智慧替補推薦
- Cloud 完整備份 / 還原（解決休眠問題）
- 名冊即時編輯

### 操作流程
1. 側邊欄 → 上傳或載入名冊
2. 側邊欄 → 使用 AI 解析 Remarks（推薦）
3. 主畫面 → 點擊「🚀 智能計算：生成本週全新公平值班表」
4. 檢查提示 → 修正錯誤
5. 導出 PDF / Excel / 備份

**如有問題請聯絡開發者**
"""

# ==========================================
# 主程式
# ==========================================
def main():
    render_sidebar()                     # 側邊欄（已包含備份、AI、名冊編輯）

    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)
    show_daily_verse()

    # 使用說明書（可展開）
    with st.expander("📖 查看完整使用說明書"):
        st.markdown(HELP_TEXT)

    selected_closures = render_control_buttons()

    # 驗證
    leave_students = st.session_state.leave_tracker_input
    audit_results = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
    st.session_state.master_report_df = audit_results["report_df"]

    # 提示
    if audit_results["typo"][0]:
        st.markdown('<div class="danger-alert"><b>⚠️ 數據不符警告：</b><br>' + '<br>'.join(audit_results["typo"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["duplicate"][0]:
        st.markdown('<div class="danger-alert"><b>⚠️ 重複排班警告：</b><br>' + '<br>'.join(audit_results["duplicate"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["leave_conflict"][0]:
        st.markdown('<div class="danger-alert"><b>🛑 請假衝突：</b><br>' + '<br>'.join(audit_results["leave_conflict"][1]) + '</div>', unsafe_allow_html=True)
        if st.button("🩹 一鍵清除請假同學", type="primary"):
            for d in DAYS:
                for r in ROWS_ROSTER:
                    if str(st.session_state.roster_df.at[r, d]).strip() in leave_students:
                        st.session_state.roster_df.at[r, d] = ""
            st.success("✅ 已清除請假同學")
            st.rerun()
    elif audit_results["vacuum"][0]:
        st.markdown('<div class="warning-alert"><b>💡 空缺提示：</b><br>' + '<br>'.join(audit_results["vacuum"][1]) + '</div>', unsafe_allow_html=True)

    # 值班表
    st.write("---")
    st.subheader("📅 本週值班表")
    tab_view, tab_edit = st.tabs(["📅 視覺公告版", "✏️ 手動編輯版"])

    def apply_cell_style(val, role, day):
        val = str(val).strip()
        if val == "X": return "color:#EF4444;font-weight:bold;background:#FEF2F2;"
        if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
            return "background:#E5E7EB;color:#9CA3AF;font-style:italic;"
        if val == "": return "background:#F9FAFB;"
        base = "font-weight:bold;text-align:center;"
        if "Assist" in role: return base + "background:#FFF8E1;color:#B45309;"
        if "Room302" in role: return base + "background:#D1FAE5;color:#166534;"
        if "Room303" in role: return base + "background:#FEE2E2;color:#991B1B;"
        if "Room202" in role: return base + "background:#DBEAFE;color:#1E40AF;"
        return base

    with tab_view:
        styled = st.session_state.roster_df.style.apply(
            lambda row: [apply_cell_style(val, row.name, col) for col, val in row.items()], axis=1
        )
        st.dataframe(styled, use_container_width=True, height=320)

    with tab_edit:
        st.session_state.roster_df = st.data_editor(st.session_state.roster_df, use_container_width=True)

    # 圖表（已修正色階 + 空值檢查）
    st.write("---")
    st.subheader("📊 全體累積工作點數公平性動態監控天平")
    if not st.session_state.master_report_df.empty:
        fig = px.bar(
            st.session_state.master_report_df,
            x='學生姓名 (Prefect Name)',
            y='最終總計加權負荷 (點)',
            text_auto='.1f',
            color='最終總計加權負荷 (點)',
            color_continuous_scale='YlOrBr'   # 已修正為有效色階
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("請先生成值班表以顯示工作量圖表")

    # 智慧替補
    st.write("---")
    st.subheader("🔍 智慧替補推薦")
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

    st.caption(f"Sing Yin Secondary School Study Prefect Platform | {VERSION}")

if __name__ == "__main__":
    main()
