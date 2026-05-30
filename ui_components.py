# ui_components.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
UI 元件模組 - 側邊欄、神聖每日聖經金句、控制按鈕

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（神聖金句深色漸層 + 金色文字 + 全局負荷滑桿相容 + 多槽位支援 + 完整側邊欄功能）
"""

import streamlit as st
import pandas as pd
import datetime
import io
import random

# ====================== 模組導入 ======================
from config import (
    DAYS, ROWS_ROSTER, DAILY_VERSES, VERSION, PROJECT_FULL_NAME,
    NASA_COLORS, get_role_style
)
from core import generate_roster
from utils import (
    process_roster_import, smart_process_roster_import,
    export_system_backup, import_system_backup
)
from data import get_demo_dataframe, get_sample_format_dataframe
from ai_parser import ai_parse_remarks

# ====================== 合併所有金句供隨機刷新使用 ======================
ALL_VERSES = []
for day_list in DAILY_VERSES.values():
    ALL_VERSES.extend(day_list)


def show_daily_verse():
    """顯示每日聖經金句 + 隨機刷新按鈕（神聖莊重風格）"""
    if "current_verse" not in st.session_state or st.session_state.current_verse is None:
        st.session_state.current_verse = random.choice(ALL_VERSES)

    # 神聖莊重區塊：深色漸層背景、金色文字、較大間距
    st.markdown(f"""
    <div style="background: linear-gradient(180deg, #1A1A2E 0%, #0B1E3D 100%); 
                padding: 28px 24px; 
                border-radius: 16px; 
                margin: 20px 0 30px 0; 
                text-align: center; 
                border: 1px solid #D4AF37; 
                box-shadow: 0 8px 32px rgba(212, 175, 55, 0.15);">
        <h3 style="margin: 0 0 12px 0; color: #D4AF37; font-size: 22px; letter-spacing: 1px;">
            📖 今日聖經金句
        </h3>
        <p style="font-size: 17px; margin: 0; color: #F5E8C7; line-height: 1.65; font-weight: 500;">
            {st.session_state.current_verse}
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_refresh, col_spacer = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 刷新金句", use_container_width=True, type="secondary"):
            st.session_state.current_verse = random.choice(ALL_VERSES)
            st.rerun()


def render_sidebar():
    """側邊欄完整功能（包含即時統計、名冊管理、AI解析、請假、備份）"""
    with st.sidebar:
        st.header("🏫 Sing Yin Secondary School")

        # ==================== 校徽 ====================
        show_logo = st.checkbox("🖼️ 顯示校徽（畫面與 PDF）", value=True, key="show_logo_toggle")

        uploaded_logo = st.file_uploader("上傳自訂校徽 (PNG)", type=["png"], key="logo_uploader")
        if uploaded_logo:
            st.session_state.logo_data = uploaded_logo.getvalue()
            st.success("✅ 已使用自訂校徽")
        elif show_logo and "logo_data" not in st.session_state:
            try:
                with open("logo.png", "rb") as f:
                    st.session_state.logo_data = f.read()
            except FileNotFoundError:
                st.info("💡 請將 logo.png 放到專案根目錄（可選）")

        st.write("---")

        # ==================== 即時統計 ====================
        st.subheader("📊 即時累計統計")
        if not st.session_state.students_df.empty:
            total = len(st.session_state.students_df)
            total_points = st.session_state.students_df["history_weight"].sum()
            avg = round(total_points / total, 1) if total > 0 else 0.0
            st.metric("總領袖生人數", total)
            st.metric("累計總點數", f"{total_points:.1f}")
            st.metric("平均負荷", f"{avg:.1f} 點")
        else:
            st.info("📌 尚未載入名冊")

        st.write("---")

        # ==================== 名冊管理 ====================
        st.subheader("🗄️ 名冊管理")

        if st.button("💡 一鍵載入官方示範名冊", use_container_width=True):
            st.session_state.students_df = get_demo_dataframe()
            st.success("✅ 官方示範名冊已載入")
            st.rerun()

        if st.button("📥 下載名冊格式範例", use_container_width=True):
            sample_df = get_sample_format_dataframe()
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                sample_df.to_excel(writer, index=False)
            st.download_button(
                "✅ 下載範例檔",
                output.getvalue(),
                "Prefect_名冊格式範例.xlsx",
                use_container_width=True
            )

        uploaded_roster = st.file_uploader(
            "上傳名冊 (Excel/CSV)", 
            type=["csv", "xlsx", "xls"], 
            key="roster_importer"
        )

        col_trad, col_ai = st.columns(2)
        with col_trad:
            if uploaded_roster and st.button("📋 傳統格式導入", use_container_width=True):
                process_roster_import(uploaded_roster)
        with col_ai:
            if uploaded_roster and st.button("🤖 AI 智能自動匹配", type="primary", use_container_width=True):
                smart_process_roster_import(uploaded_roster)

        st.caption("💡 AI 智能導入：支援任意欄位名稱與順序")

        st.write("---")

        # ==================== 名冊即時修改 ====================
        st.subheader("👥 名冊即時修改")
        st.caption("直接編輯後即時儲存")
        st.session_state.students_df = st.data_editor(
            st.session_state.students_df,
            column_config={
                "name": st.column_config.TextColumn("姓名 *", required=True),
                "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5", "F.6"]),
                "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"]),
                "fixed_general_duty": st.column_config.SelectboxColumn(
                    "學年固定總值班", 
                    options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
                ),
                "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
                "history_duties": st.column_config.NumberColumn("歷史累計(次)", min_value=0, step=1),
                "history_weight": st.column_config.NumberColumn("歷史動態(點)", min_value=0.0, step=0.5),
                "remarks": st.column_config.TextColumn("備註")
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="student_editor_widget"
        )

        st.write("---")

        # ==================== AI 智能解析 ====================
        st.subheader("🤖 AI 智能解析")
        if st.button("🚀 執行 AI 解析 Remarks", use_container_width=True):
            with st.spinner("AI 解析中..."):
                updated_df = ai_parse_remarks(st.session_state.students_df)
                st.session_state.students_df = updated_df
                st.success("✅ AI 已自動更新固定值班、可值班日與職級")
                st.rerun()

        st.write("---")

        # ==================== 請假登記 ====================
        st.subheader("🛑 請假登記")
        valid_names = [
            str(name).strip() 
            for name in st.session_state.students_df["name"].dropna() 
            if str(name).strip()
        ]
        st.session_state.leave_tracker_input = st.multiselect(
            "選取今日請假人員（可多選）", 
            options=valid_names,
            default=st.session_state.get("leave_tracker_input", [])
        )

        st.write("---")

        # ==================== Cloud 備份 ====================
        st.subheader("💾 Cloud 備份系統")
        st.caption("解決 Streamlit Cloud 休眠後資料遺失問題")

        if st.button("⬇️ 導出完整備份 (JSON)", use_container_width=True):
            backup_json = export_system_backup(st.session_state.get("master_report_df", pd.DataFrame()))
            st.download_button(
                "✅ 下載備份檔",
                backup_json,
                f"SYSS_Backup_{datetime.date.today().strftime('%Y%m%d')}.json",
                "application/json",
                use_container_width=True
            )

        uploaded_backup = st.file_uploader("上傳備份 JSON 還原", type=["json"], key="backup_importer")
        if uploaded_backup and st.button("🔄 還原備份", use_container_width=True):
            import_system_backup(uploaded_backup)

        st.caption("💡 每次生成班表後建議立即備份")


def render_control_buttons():
    """主畫面控制按鈕（生成排班、一鍵清空）"""
    closure_options = [
        f"{d} - {room}" 
        for d in DAYS 
        for room in ["Room302", "Room303", "Room202"]
        if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"])
    ]
    selected_closures = st.multiselect(
        "🛠️ 本週特殊不開放時段", 
        options=closure_options, 
        key="special_closures"
    )

    col1, col2, col3 = st.columns([2, 1.5, 1.5])

    with col1:
        if st.button("🚀 智能計算：生成本週全新公平值班表", type="primary", use_container_width=True):
            with st.spinner("正在進行公平排班計算..."):
                seed = random.randint(10000, 99999)
                # 使用全局負荷滑桿的值
                global_multiplier = st.session_state.get("global_load_multiplier", 1.0)
                st.session_state.roster_df = generate_roster(
                    st.session_state.students_df,
                    st.session_state.leave_tracker_input,
                    selected_closures,
                    seed,
                    global_load_multiplier=global_multiplier
                )
                st.success(f"✅ 排班完成！驗證碼: SY-{seed}（全局負荷倍率：{global_multiplier:.1f}）")

    with col2:
        if st.button("🗑️ 一鍵清空本週排班", type="secondary", use_container_width=True):
            st.session_state.show_clear_confirm = True

    if st.session_state.get("show_clear_confirm", False):
        st.markdown(
            '<div class="warning-alert"><b>⚠️ 確定要清除全部排班？此操作無法復原！</b></div>', 
            unsafe_allow_html=True
        )
        c1, c2 = st.columns(2)
        if c1.button("💥 確定清空", type="primary"):
            st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
            st.session_state.show_clear_confirm = False
            st.rerun()
        if c2.button("❌ 取消"):
            st.session_state.show_clear_confirm = False
            st.rerun()

    return selected_closures


print("✅ ui_components.py 已載入完成 - 側邊欄、神聖金句區塊、控制按鈕模組就緒")