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
if 'manual_weights' not in st.session_state:
    st.session_state.manual_weights = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)

# ==========================================
# 使用說明書（完整版 + 直接反饋）
# ==========================================
HELP_TEXT = """
# 📖 Sing Yin Secondary School Study Prefect Duty Roster 使用說明書  
**版本**：v1.4 手動調整負荷 + DeepSeek V4 版  
**更新日期**：2026 年 5 月 25 日  

**適用對象**：Study Prefect Team Advisor、Head Study Prefect、Assistant Head Study Prefect

### 主要功能
- 智能公平排班（自動讀取年級判斷老帶新）
- DeepSeek V4 AI 智能解析 Remarks
- 手動調整每次值班負荷指數
- 彩色 PDF 公告班表 + Excel + Markdown 導出
- Cloud 完整備份 / 還原
- 每日聖經金句 + 校徽顯示開關

### 操作流程
1. 側邊欄載入名冊 → AI 解析 Remarks
2. 主畫面設定不開放時段 → 生成排班
3. 使用「🔧 手動調整負荷」微調
4. 導出 PDF / Excel / 備份

---

### 📧 直接反饋給開發者
遇到問題或有建議，請直接點擊下方按鈕寄信：

[📧 點此直接寄信給開發者](mailto:s10777@syss.edu.hk?subject=Study Prefect Duty Roster 反饋)

---

如有任何問題，歡迎隨時聯絡我！
"""

def main():
    render_sidebar()

    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)
    show_daily_verse()

    with st.expander("📖 查看完整使用說明書（含直接反饋）", expanded=False):
        st.markdown(HELP_TEXT)

    selected_closures = render_control_buttons()

    leave_students = st.session_state.leave_tracker_input
    audit_results = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students, st.session_state.manual_weights)
    st.session_state.master_report_df = audit_results["report_df"]

    # 安全提示
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
            st.success("✅ 已清除")
            st.rerun()
    elif audit_results["vacuum"][0]:
        st.markdown('<div class="warning-alert"><b>💡 空缺提示：</b><br>' + '<br>'.join(audit_results["vacuum"][1]) + '</div>', unsafe_allow_html=True)

    # 值班表
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

    # 手動調整負荷
    st.write("---")
    st.subheader("🔧 手動調整本次值班負荷指數")
    st.caption("針對每個崗位本次值班，手動修改累計負荷點數（調整後會即時更新最終總計）")
    manual_col = st.data_editor(
        st.session_state.manual_weights,
        use_container_width=True,
        key="manual_weight_editor"
    )
    if not manual_col.equals(st.session_state.manual_weights):
        st.session_state.manual_weights = manual_col
        st.rerun()

    # 累計審計表
    st.write("---")
    st.subheader("📊 累計動態工作負荷審計表（已包含手動調整）")
    if not st.session_state.master_report_df.empty:
        st.dataframe(st.session_state.master_report_df, use_container_width=True, hide_index=True)
    else:
        st.info("請先生成排班表以顯示審計表")

    # 工作量圖表
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

    # 導出功能
    st.write("---")
    st.subheader("📤 導出功能")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 匯出 A4 橫式公告 PDF", use_container_width=True):
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
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

    # 智慧替補
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
