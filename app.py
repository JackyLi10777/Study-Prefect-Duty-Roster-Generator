# app.py
import streamlit as st
import pandas as pd
import random
import plotly.express as px
import datetime
import io

# 匯入所有模組
from config import DAYS, ROWS_ROSTER, VERSION, APP_TITLE
from core import generate_roster, validate_and_compute, recommend_substitutes
from utils import generate_pdf, export_system_backup, import_system_backup
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

# ==========================================
# 主程式
# ==========================================
def main():
    # 1. 側邊欄（設定與管理）
    render_sidebar()

    # 2. 主畫面標題與每日金句
    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)
    show_daily_verse()

    # 3. 核心控制按鈕（生成排班表）
    selected_closures = render_control_buttons()

    # 4. 驗證與統計
    leave_students = st.session_state.leave_tracker_input
    audit_results = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
    master_report_df = audit_results["report_df"]

    # 5. 提示訊息
    if audit_results["typo"][0]:
        st.error("⚠️ 發現無效姓名，請檢查班表")
    if audit_results["duplicate"][0]:
        st.error("⚠️ 發現同一天重複排班")
    if audit_results["leave_conflict"][0]:
        st.warning("🛑 請假人員仍在班表中")

    # 6. 值班表顯示（雙 Tab）
    st.write("---")
    st.subheader("📅 本週值班表")
    tab_view, tab_edit = st.tabs(["📅 視覺公告版", "✏️ 手動編輯版"])

    def apply_cell_style(val, role, day):
        val = str(val).strip()
        if val == "X": return "color:#EF4444; font-weight:bold; background:#FEF2F2;"
        if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
            return "background:#E5E7EB; color:#9CA3AF; font-style:italic;"
        if val == "": return "background:#F9FAFB;"
        base = "font-weight:bold; text-align:center;"
        if "Assist" in role: return base + "background:#FFF8E1; color:#B45309;"
        if "Room302" in role: return base + "background:#D1FAE5; color:#166534;"
        if "Room303" in role: return base + "background:#FEE2E2; color:#991B1B;"
        if "Room202" in role: return base + "background:#DBEAFE; color:#1E40AF;"
        return base

    with tab_view:
        styled = st.session_state.roster_df.style.apply(
            lambda row: [apply_cell_style(val, row.name, col) for col, val in row.items()], axis=1
        )
        st.dataframe(styled, use_container_width=True, height=320)

    with tab_edit:
        st.session_state.roster_df = st.data_editor(
            st.session_state.roster_df,
            use_container_width=True,
            key="main_roster_editor"
        )

    # 7. 工作量圖表
    st.write("---")
    st.subheader("📊 全體累積工作負荷")
    if not master_report_df.empty:
        fig = px.bar(
            master_report_df,
            x='學生姓名 (Prefect Name)',
            y='最終總計加權負荷 (點)',
            text_auto='.1f',
            color_continuous_scale='gold'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 8. 智慧替補
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
            st.dataframe(sub_df, use_container_width=True)
        else:
            st.warning(msg)

    # 9. 導出區
    st.write("---")
    st.subheader("📤 導出")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📄 導出 PDF 公告版", use_container_width=True):
            pdf_bytes = generate_pdf(st.session_state.roster_df, master_report_df, st.session_state.logo_data)
            st.download_button("下載 PDF", pdf_bytes, "SYSS_Duty_Roster.pdf", "application/pdf", use_container_width=True)
    with c2:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.roster_df.to_excel(writer, sheet_name="值班表")
            master_report_df.to_excel(writer, sheet_name="統計", index=False)
        st.download_button("📊 導出 Excel", output.getvalue(), "SYSS_Roster.xlsx", use_container_width=True)
    with c3:
        backup_json = export_system_backup(master_report_df)
        st.download_button("💾 完整備份 JSON", backup_json, "backup.json", "application/json", use_container_width=True)

    st.caption(f"Sing Yin Study Prefect Platform | {VERSION}")

if __name__ == "__main__":
    main()
