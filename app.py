# app.py
import streamlit as st
import pandas as pd
import random
import plotly.express as px
import base64
import datetime
import io
import json

# 匯入所有模組（包含全新 AI 解析模組）
from config import DAYS, ROWS_ROSTER, WEIGHTS, DAILY_VERSES, VERSION, APP_TITLE
from utils import generate_pdf, export_system_backup, import_system_backup, process_roster_import, get_daily_verse
from core import generate_roster, validate_and_compute, recommend_substitutes
from data import get_demo_dataframe, get_sample_format_dataframe
from ui_components import render_sidebar, render_main_header, render_control_buttons, show_daily_verse
from ai_parser import ai_parse_remarks

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
if 'show_help' not in st.session_state:
    st.session_state.show_help = False
if 'last_backup_time' not in st.session_state:
    st.session_state.last_backup_time = None
if 'leave_tracker_input' not in st.session_state:
    st.session_state.leave_tracker_input = []

# ==========================================
# 主程式入口
# ==========================================
def main():
    # 渲染側邊欄（已包含 AI 智能解析按鈕）
    render_sidebar()

    # 渲染主畫面標題與每日金句
    render_main_header()
    show_daily_verse()

    # 控制按鈕與特殊不開放設定
    selected_closures = render_control_buttons()

    # 驗證與統計
    leave_students = st.session_state.leave_tracker_input
    audit_results = validate_and_compute(st.session_state.roster_df, st.session_state.students_df, leave_students)
    typo_detected, invalid_entries = audit_results["typo"]
    vacuum_detected, vacuum_entries = audit_results["vacuum"]
    duplicate_detected, duplicate_entries = audit_results["duplicate"]
    leave_conflict_detected, leave_conflict_entries = audit_results["leave_conflict"]
    master_report_df = audit_results["report_df"]

    # 安全提示
    if typo_detected:
        st.markdown('<div class="danger-alert"><b>⚠️ 數據不符警告：</b>手動輸入了名冊之外的姓名。<br>' + '<br>'.join(invalid_entries) + '</div>', unsafe_allow_html=True)
    if duplicate_detected:
        st.markdown('<div class="danger-alert"><b>⚠️ 分身重複衝突警告：</b>同名隊員在同日被分配到多個崗位！<br>' + '<br>'.join(duplicate_entries) + '</div>', unsafe_allow_html=True)
    if leave_conflict_detected:
        st.markdown('<div class="danger-alert"><b>🛑 請假人員衝突警告：</b><br>' + '<br>'.join(leave_conflict_entries) + '</div>', unsafe_allow_html=True)
        if st.button("🩹 一鍵將請假同學從現有值班表中移出", type="primary"):
            for d in DAYS:
                for r in ROWS_ROSTER:
                    if str(st.session_state.roster_df.at[r, d]).strip() in leave_students:
                        st.session_state.roster_df.at[r, d] = ""
            st.success("✅ 已自動清除請假同學！")
            st.rerun()
    elif vacuum_detected:
        st.markdown('<div class="warning-alert"><b>💡 提示：存在未配對的開門空缺：</b><br>' + '<br>'.join(vacuum_entries) + '</div>', unsafe_allow_html=True)

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
            st.dataframe(styled_roster, use_container_width=True, height=260)
        except Exception:
            st.dataframe(st.session_state.roster_df, use_container_width=True, height=260)

    with tab_edit:
        st.markdown("<p style='font-size:13px; color:#666;'>💡 您可以直接在下方表格內手動修改或填入人名，輸入 <b>X</b> 代表鎖定該不開放時段：</p>", unsafe_allow_html=True)
        edited_roster_df = st.data_editor(
            st.session_state.roster_df,
            use_container_width=True,
            key="main_roster_editor_widget",
            on_change=lambda: setattr(st.session_state, 'roster_df', edited_roster_df) if 'edited_roster_df' in locals() else None
        )
        if 'edited_roster_df' in locals() and not edited_roster_df.equals(st.session_state.roster_df):
            st.session_state.roster_df = edited_roster_df
            st.rerun()

    # 多格式導出
    st.write("---")
    st.markdown("### 📊 行政名冊與排班數據多格式導出")
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        try:
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                st.session_state.roster_df.to_excel(writer, sheet_name='本週值班表')
                master_report_df.to_excel(writer, sheet_name='工作負荷統計', index=False)
            st.download_button(
                label="📊 下載 Excel 行政試算表 (.xlsx)",
                data=output_excel.getvalue(),
                file_name=f"SYSS_Prefect_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception:
            st.button("📊 Excel 編譯引擎加載中...", disabled=True, use_container_width=True)

    with dl_col2:
        try:
            md_data = "### 📅 本週值班表 (Weekly Duty Roster)\n\n" + st.session_state.roster_df.to_markdown() + "\n\n### 📊 累積動態工作負荷審計表\n\n" + master_report_df.to_markdown(index=False)
            st.download_button(
                label="📝 下載 Markdown 簡報純文字 (.md)",
                data=md_data.encode('utf-8'),
                file_name=f"SYSS_Prefect_Roster_{datetime.date.today().strftime('%Y%m%d')}.md",
                mime="text/plain",
                use_container_width=True
            )
        except Exception:
            st.button("📝 Markdown 轉換模組加載中...", disabled=True, use_container_width=True)

    # 工作量圖表
    st.write("---")
    st.subheader("📊 全體領袖生動態累計工作負荷審計大表")
    st.dataframe(master_report_df, use_container_width=True, hide_index=True)

    if not master_report_df.empty:
        st.write("---")
        st.subheader("🦅 全體累積工作點數公平性動態監控天平")
        fig = px.bar(
            master_report_df, 
            x='學生姓名 (Prefect Name)', 
            y='最終總計加權負荷 (點)', 
            text_auto='.1f', 
            title="全體領袖生加權工作量天平（點數低者將優先派班）", 
            color='最終總計加權負荷 (點)', 
            color_continuous_scale='gold'
        )
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # 智慧替補
    st.write("---")
    st.subheader("🔍 臨時請假？智慧替補候選人精準建議")
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        chosen_day = st.selectbox("請假或替換日期 (星期)", DAYS, index=0, key="sub_day_selector")
    with sub_col2:
        chosen_role = st.selectbox("請假或替換職位/房間", ROWS_ROSTER, index=0, key="sub_role_selector")

    current_person = str(st.session_state.roster_df.at[chosen_role, chosen_day]).strip()
    st.text_input("📍 目前該時段排定之人員", value=current_person if current_person not in ["", "X"] else "（當前為空白或特殊不開放時段）", disabled=True)

    if st.button("🔮 執行篩選並推薦最優替補人員", type="secondary", use_container_width=True):
        sub_df, error_msg = recommend_substitutes(st.session_state.roster_df, st.session_state.students_df, chosen_day, chosen_role)
        if sub_df is not None:
            st.success("📋 媒合成功！已依據「最終總計加權負荷」由低到高為您排序推薦合格替補人員：")
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
        else:
            st.warning(error_msg)

    st.caption(f"Sing Yin Secondary School Study Prefect Platform | {VERSION}")

if __name__ == "__main__":
    main()
