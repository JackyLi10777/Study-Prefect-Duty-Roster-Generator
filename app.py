# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io
import json
import base64

from config import DAYS, ROWS_ROSTER, VERSION, APP_TITLE, DAILY_VERSES
from core import validate_and_compute, recommend_substitutes
from utils import generate_pdf, export_system_backup, import_system_backup, process_roster_import
from ui_components import render_sidebar, show_daily_verse, render_control_buttons

# ==========================================
# Session State 初始化（完整防護）
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
# 使用說明書（完整版）
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
- 彩色 PDF 公告班表（含校徽）
- 智慧替補推薦系統
- Cloud 完整備份 / 還原（解決休眠問題）
- 名冊即時編輯
- 累計動態工作負荷審計表
- 多格式導出（PDF、Excel、Markdown）

### 操作流程
1. 側邊欄 → 導入或編輯名冊
2. 側邊欄 → 使用 AI 解析 Remarks（強烈推薦）
3. 主畫面 → 點擊「🚀 智能計算：生成本週全新公平值班表」
4. 檢查所有提示並修正
5. 使用下方 Tabs 預覽 / 手動修改
6. 導出 PDF / Excel / Markdown / 備份

**如有問題請聯絡開發者**
"""

def main():
    # 側邊欄（完整呼叫）
    render_sidebar()

    # 主畫面標題
    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)
    show_daily_verse()

    # 使用說明書
    with st.expander("📖 查看完整使用說明書"):
        st.markdown(HELP_TEXT)

    # 控制按鈕（含一鍵清空）
    selected_closures = render_control_buttons()

    # 驗證與統計
    leave_students = st.session_state.leave_tracker_input
    audit_results = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
    st.session_state.master_report_df = audit_results["report_df"]

    # 安全提示（完整）
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

    # ==================== 排班表預覽 + 手動修改 ====================
    st.write("---")
    st.subheader("📅 本週值班表")
    tab_view, tab_edit = st.tabs(["📅 視覺公告版（彩色）", "✏️ 手動修改版"])

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
        st.markdown("<p style='font-size:13px; color:#666;'>💡 直接在下方表格修改人名或打 X 鎖定</p>", unsafe_allow_html=True)
        edited_roster = st.data_editor(
            st.session_state.roster_df,
            use_container_width=True,
            key="main_roster_editor_widget"
        )
        if not edited_roster.equals(st.session_state.roster_df):
            st.session_state.roster_df = edited_roster
            st.rerun()

    # ==================== 累計動態工作負荷審計表 ====================
    st.write("---")
    st.subheader("📊 累計動態工作負荷審計表")
    if not st.session_state.master_report_df.empty:
        st.dataframe(st.session_state.master_report_df, use_container_width=True, hide_index=True)
    else:
        st.info("請先生成排班表以顯示審計表")

    # ==================== 工作量圖表 ====================
    if not st.session_state.master_report_df.empty:
        st.write("---")
        st.subheader("🦅 全體累積工作點數公平性動態監控")
        fig = px.bar(
            st.session_state.master_report_df,
            x='學生姓名 (Prefect Name)',
            y='最終總計加權負荷 (點)',
            text_auto='.1f',
            color='最終總計加權負荷 (點)',
            color_continuous_scale='YlOrBr'
        )
        st.plotly_chart(fig, use_container_width=True)

    # ==================== PDF + 多格式導出 ====================
    st.write("---")
    st.subheader("📤 導出功能")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 匯出 A4 橫式公告 PDF", use_container_width=True):
            logo_b64 = None
            if st.session_state.get("show_logo_toggle", True) and st.session_state.get("logo_data"):
                logo_b64 = base64.b64encode(st.session_state.logo_data).decode()
            pdf_bytes = generate_pdf(st.session_state.roster_df, st.session_state.master_report_df, logo_b64)
            if pdf_bytes:
                st.download_button("💾 下載 PDF", pdf_bytes, f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)

    with col2:
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            st.session_state.roster_df.to_excel(writer, sheet_name='本週值班表')
            st.session_state.master_report_df.to_excel(writer, sheet_name='工作負荷統計', index=False)
        st.download_button("📊 下載 Excel (.xlsx)", output_excel.getvalue(), f"SYSS_Prefect_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx", use_container_width=True)

    with col3:
        md_data = "### 本週值班表\n\n" + st.session_state.roster_df.to_markdown() + "\n\n### 工作負荷統計\n\n" + st.session_state.master_report_df.to_markdown(index=False)
        st.download_button("📝 下載 Markdown (.md)", md_data.encode('utf-8'), f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.md", use_container_width=True)

    # ==================== 智慧替補 ====================
    st.write("---")
    st.subheader("🔍 智慧替補推薦")
    c1, c2 = st.columns(2)
    with c1:
        chosen_day = st.selectbox("日期", DAYS, key="sub_day")
    with c2:
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
