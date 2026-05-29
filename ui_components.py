# ui_components.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
UI 元件模組 - 彩色排班表、學生管理、智慧替補、快捷下載

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（完全符合根本編程誡命：美觀、專業、即時互動）
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional
import datetime

from config import (
    DAYS, ROWS_ROSTER, VERSION, PROJECT_FULL_NAME, APP_TITLE,
    get_role_style, NASA_COLORS, DAILY_VERSES
)
from utils import (
    generate_pdf, export_to_excel, export_to_markdown,
    export_system_backup, import_system_backup
)
from core import recommend_substitutes


# ====================== 彩色排班表顯示 ======================
def display_colored_roster(roster_df: pd.DataFrame):
    """美觀彩色排班表（支援多槽位 + ⬜ + ❌）"""
    if roster_df.empty:
        st.warning("尚未生成排班表")
        return

    st.markdown("### 📋 **值班公告版**")
    st.caption(f"更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | v{VERSION}")

    # 使用 st.dataframe + 自訂 CSS 實現角色顏色
    styled_df = roster_df.copy()

    # 建立 HTML 版本（Streamlit 支援）
    html = styled_df.to_html(escape=False, index=True)

    # 注入顏色樣式
    html = html.replace('<table', '''
    <style>
        .roster-table td { text-align: center; font-weight: bold; padding: 10px !important; }
        .assist { background-color: #F5E8C7 !important; color: #8B5A2B; }
        .room302 { background-color: #E6F4EA !important; color: #137333; }
        .room303 { background-color: #FFF3E0 !important; color: #E67E22; }
        .room202 { background-color: #FCE8E6 !important; color: #C5221F; }
        .closed { background-color: #F1F1F1 !important; color: #777; font-size: 18px; }
        th { background-color: #0B1E3D !important; color: white !important; }
    </style>
    <table class="roster-table"''')

    # 替換格位顏色
    for row in ROWS_ROSTER:
        base_role = row.split(" - ")[0].strip()
        style_class = ""
        if "Assist" in base_role:
            style_class = "assist"
        elif "302" in base_role:
            style_class = "room302"
        elif "303" in base_role:
            style_class = "room303"
        elif "202" in base_role:
            style_class = "room202"

        if style_class:
            html = html.replace(f"<td>{row}</td>", f'<td class="{style_class}">{row}</td>')

    st.markdown(html, unsafe_allow_html=True)


# ====================== 學生管理面板 ======================
def student_management_panel(students_df: pd.DataFrame) -> pd.DataFrame:
    """學生名冊管理（新增、編輯、刪除、手動調整負荷）"""
    st.markdown("### 👥 **學生名冊管理**")

    col1, col2 = st.columns([3, 1])
    with col1:
        edited_df = st.data_editor(
            students_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "name": st.column_config.TextColumn("姓名", required=True),
                "form": st.column_config.SelectboxColumn("年級", options=["F.1", "F.2", "F.3"]),
                "role": st.column_config.SelectboxColumn("職位", options=["Study Prefect", "Assistant Head Study Prefect", "Head Study Prefect"]),
                "history_weight": st.column_config.NumberColumn("歷史累計權重", format="%.2f", min_value=0.0),
            },
            hide_index=False,
        )

    with col2:
        st.markdown("**快速操作**")
        if st.button("➕ 新增學生", use_container_width=True):
            new_row = pd.DataFrame([{"name": "新學生", "form": "F.2", "role": "Study Prefect", "history_weight": 0.0}])
            edited_df = pd.concat([edited_df, new_row], ignore_index=True)

        if st.button("🗑️ 刪除選取", use_container_width=True):
            st.warning("請在左側表格勾選後再按此按鈕")

        if st.button("🔄 重置為示範資料", use_container_width=True, type="secondary"):
            from data import get_demo_dataframe
            edited_df = get_demo_dataframe()
            st.success("已重置為示範名冊")

    return edited_df


# ====================== 全局負荷滑桿 + 即時預覽 ======================
def global_multiplier_slider() -> float:
    """全局負荷倍率滑桿（即時影響排班公平性）"""
    st.markdown("### ⚖️ **全局負荷倍率調整**")
    multiplier = st.slider(
        "調整整體工作負荷（影響權重計算）",
        min_value=0.5,
        max_value=2.5,
        value=1.0,
        step=0.1,
        format="%.1f×",
        help="1.0 = 正常，>1.0 增加負荷，<1.0 減輕負荷"
    )

    if multiplier != 1.0:
        st.info(f"目前已啟用 **{multiplier}×** 負荷調整模式", icon="📈")

    return multiplier


# ====================== 智慧替補推薦面板 ======================
def substitute_recommendation_panel(roster_df: pd.DataFrame, students_df: pd.DataFrame):
    """智慧替補推薦（點擊即可替換）"""
    st.markdown("### 🔄 **智慧替補推薦**")

    if roster_df.empty:
        st.info("請先生成排班表")
        return

    col1, col2 = st.columns(2)
    with col1:
        target_day = st.selectbox("請假日期", DAYS, index=0)
    with col2:
        target_role_options = [r for r in ROWS_ROSTER if roster_df.at[r, target_day] not in ["⬜", "❌", ""]]
        target_role = st.selectbox("請假崗位", target_role_options)

    leave_name = roster_df.at[target_role, target_day]

    if not leave_name or leave_name in ["⬜", "❌"]:
        st.warning("該格位無人值班")
        return

    st.write(f"**{leave_name}** 於 **{target_day}** 請假 → **{target_role}**")

    recommendations = recommend_substitutes(roster_df, students_df, target_day, target_role, leave_name)

    if recommendations:
        st.markdown("**推薦替補（依總負荷由低到高排序）**")
        for rec in recommendations:
            col_a, col_b, col_c = st.columns([3, 1, 1])
            with col_a:
                st.write(f"**{rec['name']}**（{rec['form']}）")
            with col_b:
                st.metric("目前總累計", f"{rec['current_total']}")
            with col_c:
                if st.button("✅ 替補", key=f"sub_{rec['name']}"):
                    # 執行替補
                    roster_df.at[target_role, target_day] = rec["name"]
                    st.success(f"已將 {leave_name} 替換為 {rec['name']}")
                    st.rerun()
    else:
        st.warning("目前無合適替補人選")


# ====================== 下載區塊 ======================
def download_section(roster_df: pd.DataFrame, report_df: pd.DataFrame, global_multiplier: float):
    """一鍵下載所有格式"""
    st.markdown("### 📤 **一鍵下載**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pdf_bytes = generate_pdf(roster_df, pd.DataFrame(), report_df, global_multiplier)
        st.download_button(
            label="📄 下載 PDF 公告版",
            data=pdf_bytes,
            file_name=f"值班表_{datetime.date.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with col2:
        excel_bytes = export_to_excel(roster_df, report_df)
        st.download_button(
            label="📊 下載 Excel",
            data=excel_bytes,
            file_name=f"值班表_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col3:
        md_text = export_to_markdown(roster_df, report_df)
        st.download_button(
            label="📝 下載 Markdown",
            data=md_text,
            file_name=f"值班表_{datetime.date.today().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    with col4:
        backup_data = export_system_backup()
        st.download_button(
            label="💾 完整系統備份",
            data=json.dumps(backup_data, ensure_ascii=False, indent=2),
            file_name=f"系統備份_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )


print("✅ ui_components.py 已載入完成 - 所有 Streamlit UI 元件就緒")
