# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io
import json
import base64

from config import DAYS, ROWS_ROSTER, VERSION, APP_TITLE
from core import validate_and_compute, recommend_substitutes
from utils import generate_pdf, export_system_backup, import_system_backup, process_roster_import
from ui_components import render_sidebar, show_daily_verse, render_control_buttons

# ==========================================
# 使用說明書（完整版，已更新到 v2.0 最新功能）
# ==========================================
HELP_TEXT = """
### 📖 Sing Yin Study Prefect Duty Roster System 使用說明書（v2.0）

#### 1. 名冊導入（最重要）
- **推薦使用「🤖 AI 智能自動匹配」**：支援**任意格式**的 Excel / CSV，AI 會自動辨識姓名、年級、職級、可用日子等欄位。
- 傳統格式導入：需符合固定欄位名稱（姓名、年級、班別、職級、學年固定總值班、可用日子、歷史累計(次)、歷史動態(點)、備註）。
- 建議先點「📥 下載名冊格式範例」參考。

#### 2. 名冊即時修改
- 在側邊欄可以直接編輯所有領袖生資料，修改後會即時儲存。

#### 3. 生成值班表
- 在側邊欄設定「請假人員」與「本週特殊不開放時段」。
- 點擊主畫面大按鈕 **「🚀 智能計算：生成本週全新公平值班表」**。
- 系統會自動考慮：可用日子、固定值班、老帶新機制（F.3 優先配 F.4/F.5）、歷史負荷平衡、避免連續值班。

#### 4. 手動調整負荷指數（重要更新）
- 在「🔧 手動調整本次值班負荷指數」表格可以直接修改每個崗位本次值班的點數。
- **清空儲存格不會再出錯**（已修復）。
- 修改後系統會自動重新計算累計負荷與公平性圖表。

#### 5. 值班表操作
- **視覺公告版**：漂亮的彩色表格，適合直接截圖或列印。
- **手動修改版**：可以直接在表格上修改人名或打「X」鎖定。
- 建議先生成後，再用手動修改版微調。

#### 6. 智慧替補推薦
- 選擇日期與崗位後，點擊「🔍 尋找最優替補」，系統會依據目前總點數由低到高推薦合適人選。

#### 7. 匯出功能
- **📄 匯出 PDF**：公告用彩色班表（含校徽）。
- **📊 下載 Excel**：完整值班表 + 工作負荷統計表。
- **📝 下載 Markdown**：方便複製到其他文件。

#### 8. Cloud 備份（強烈建議）
- 每次生成新班表後，建議在側邊欄點擊「⬇️ 導出完整備份 (JSON)」下載備份。
- Streamlit Cloud 休眠後可以用「上傳備份 JSON 還原」快速恢復。

#### 9. 其他小功能
- 每日聖經金句可點擊「🔄 刷新金句」更換。
- 側邊欄有即時統計（總領袖生、累計點數、平均負荷）。
- AI 解析 Remarks：側邊欄可點「🚀 執行 AI 解析 Remarks」，自動更新固定值班與可用日子。

---

**有任何問題或建議，歡迎寄信到 s10777@syss.edu.hk**

祝使用順利！🙏
"""

def main():
    render_sidebar()

    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)
    
    show_daily_verse()

    # ==========================================
    # 使用說明書（已恢復）
    # ==========================================
    with st.expander("📖 點此展開完整使用說明書（v2.0 最新版）", expanded=False):
        st.markdown(HELP_TEXT)

    st.write("---")
    selected_closures = render_control_buttons()

    leave_students = st.session_state.leave_tracker_input
    audit_results = validate_and_compute(
        st.session_state.roster_df, 
        st.session_state.students_df, 
        leave_students, 
        st.session_state.manual_weights
    )
    st.session_state.master_report_df = audit_results["report_df"]

    if audit_results["typo"][0]:
        st.markdown('<div class="danger-alert"><b>⚠️ 數據不符警告：</b><br>' + '<br>'.join(audit_results["typo"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["duplicate"][0]:
        st.markdown('<div class="danger-alert"><b>⚠️ 重複排班警告：</b><br>' + '<br>'.join(audit_results["duplicate"][1]) + '</div>', unsafe_allow_html=True)
    if audit_results["leave_conflict"][0]:
        st.markdown('<div class="danger-alert"><b>🛑 請假衝突：</b><br>' + '<br>'.join(audit_results["leave_conflict"][1]) + '</div>', unsafe_allow_html=True)
        if st.button("🩹 一鍵清除請假同學", type="primary", use_container_width=True):
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
    tab_view, tab_edit = st.tabs(["📅 視覺公告版", "✏️ 手動修改版"])

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
        st.markdown("<p style='font-size:13px; color:#666;'>💡 直接修改人名或打 X 鎖定</p>", unsafe_allow_html=True)
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
    st.caption("針對每個崗位本次值班，手動修改累計負荷點數")

    manual_col = st.data_editor(
        st.session_state.manual_weights,
        use_container_width=True,
        key="manual_weight_editor"
    )

    if not manual_col.equals(st.session_state.manual_weights):
        st.session_state.manual_weights = (
            manual_col.astype(float)
                     .fillna(0.0)
        )
        st.rerun()

    # 累計審計表
    st.write("---")
    st.subheader("📊 累計動態工作負荷審計表")
    if not st.session_state.master_report_df.empty:
        st.dataframe(st.session_state.master_report_df, use_container_width=True, hide_index=True)
    else:
        st.info("請先生成排班表以顯示審計表")

    if not st.session_state.master_report_df.empty:
        st.write("---")
        st.subheader("🦅 全體累積工作點數公平性監控")
        fig = px.bar(
            st.session_state.master_report_df,
            x='學生姓名 (Prefect Name)',
            y='最終總計加權負荷 (點)',
            text_auto='.1f',
            color='最終總計加權負荷 (點)',
            color_continuous_scale='YlOrBr'
        )
        st.plotly_chart(fig, use_container_width=True)

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

    # 快速導出
    st.write("---")
    st.subheader("📤 快速導出")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 匯出 PDF", use_container_width=True):
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode() if st.session_state.get("logo_data") else None
            pdf_bytes = generate_pdf(st.session_state.roster_df, st.session_state.master_report_df, logo_b64)
            if pdf_bytes:
                st.download_button("💾 下載 PDF", pdf_bytes, f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)
    with col2:
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            st.session_state.roster_df.to_excel(writer, sheet_name='本週值班表')
            st.session_state.master_report_df.to_excel(writer, sheet_name='工作負荷統計', index=False)
        st.download_button("📊 下載 Excel", output_excel.getvalue(), f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    with col3:
        md_data = "### 本週值班表\n\n" + st.session_state.roster_df.to_markdown() + "\n\n### 工作負荷統計\n\n" + st.session_state.master_report_df.to_markdown(index=False)
        st.download_button("📝 下載 Markdown", md_data.encode('utf-8'), f"SYSS_Roster_{datetime.date.today().strftime('%Y%m%d')}.md", use_container_width=True)

    st.caption(f"Sing Yin Secondary School Study Prefect Platform | {VERSION}")

if __name__ == "__main__":
    main()