# ui_components.py
import streamlit as st
import pandas as pd
import datetime
from config import DAYS, ROWS_ROSTER, DAILY_VERSES, VERSION, APP_TITLE
from utils import generate_pdf, export_system_backup, process_roster_import
from core import validate_and_compute, recommend_substitutes
from data import get_demo_dataframe, get_sample_format_dataframe

# ==========================================
# 每日金句顯示元件
# ==========================================
def show_daily_verse():
    """顯示今日聖經金句"""
    today = datetime.date.today().weekday()
    verse = DAILY_VERSES.get(today, DAILY_VERSES[0])
    st.markdown(f"""
    <div style="background: #F8F1E3; padding: 20px; border-radius: 12px; margin: 20px 0; text-align: center; border-left: 6px solid #D4AF37;">
        <h4 style="margin: 0 0 8px 0; color: #0C2340;">📖 今日聖經金句</h4>
        <p style="font-size: 16px; margin: 0; color: #333; line-height: 1.5;">{verse}</p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 側邊欄即時統計卡片
# ==========================================
def show_sidebar_stats(students_df):
    """側邊欄即時統計"""
    st.header("📊 即時統計")
    if not students_df.empty:
        total = len(students_df)
        total_points = students_df["history_weight"].sum()
        avg_points = round(total_points / total, 1) if total > 0 else 0
        st.metric("總領袖生人數", total)
        st.metric("歷史總累計點數", f"{total_points:.1f}")
        st.metric("平均每人負荷", f"{avg_points:.1f} 點")
    else:
        st.info("尚未載入名冊")

# ==========================================
# 側邊欄完整 UI 元件
# ==========================================
def render_sidebar():
    """完整側邊欄 UI"""
    st.header("🏫 Sing Yin Secondary School")
    
    # 校徽上傳
    uploaded_logo = st.file_uploader("上傳校徽 (PNG)", type=["png"])
    if uploaded_logo:
        st.session_state.logo_data = uploaded_logo.getvalue()

    st.write("---")
    
    # 即時統計
    show_sidebar_stats(st.session_state.students_df)

    st.write("---")
    st.header("🗄️ 數據導入")
    
    # 一鍵載入示範名冊
    if st.button("💡 一鍵載入 Sing Yin 官方示範名冊", use_container_width=True):
        st.session_state.students_df = get_demo_dataframe()
        st.success("✅ Sing Yin 示範名冊已載入")
        st.rerun()

    # 下載格式範例
    if st.button("📥 下載 Prefect 名冊導入格式範例 (Excel)", use_container_width=True):
        sample_df = get_sample_format_dataframe()
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sample_df.to_excel(writer, sheet_name="Prefect_名冊格式範例", index=False)
        st.download_button(
            label="✅ 點此下載範例檔",
            data=output.getvalue(),
            file_name="Prefect_名冊導入格式範例.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # 上傳名冊
    uploaded_roster = st.file_uploader("選取常規名冊檔案 (Excel/CSV)：", type=["csv", "xlsx", "xls"], key="roster_importer")
    if uploaded_roster is not None:
        if st.button("確認解析並覆蓋導入", type="primary", use_container_width=True):
            process_roster_import(uploaded_roster)

    st.write("---")
    st.header("👥 在線名冊即時維護")
    st.data_editor(
        st.session_state.students_df,
        column_config={
            "name": st.column_config.TextColumn("姓名 *", required=True),
            "form": st.column_config.SelectboxColumn("年級", options=["F.3", "F.4", "F.5"]),
            "role": st.column_config.SelectboxColumn("職級", options=["Study Prefect", "Assistant Head Study Prefect"]),
            "fixed_general_duty": st.column_config.SelectboxColumn("學年固定總值班", options=["NONE", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"], default="NONE"),
            "available": st.column_config.TextColumn("可用日子", default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"),
            "history_duties": st.column_config.NumberColumn("歷史累計(次)", min_value=0, step=1),
            "history_weight": st.column_config.NumberColumn("歷史動態(點)", min_value=0.0, step=0.5),
            "remarks": st.column_config.TextColumn("備註")
        },
        num_rows="dynamic", use_container_width=True, hide_index=True, 
        key="student_editor_widget", on_change=st.session_state.get("sync_students_data")
    )

    st.write("---")
    st.header("🛑 突發臨時請假登記")
    valid_names_list = [str(name).strip() for name in st.session_state.students_df["name"].dropna() if str(name).strip()]
    leave_students = st.multiselect(
        "選取今日請假人員：", 
        options=valid_names_list, 
        key="leave_tracker_input"
    )

    st.write("---")
    st.header("💾 Cloud 備份系統")
    # 備份按鈕已在主畫面處理，這裡保留提醒
    st.caption("💡 生成值班表後，系統會自動提醒備份")

# ==========================================
# 主畫面標題與金句
# ==========================================
def render_main_header():
    """主畫面標題與每日金句"""
    st.markdown(f'<p class="main-title">{APP_TITLE}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">F.3–F.5 Study Prefect Duty Platform | {VERSION}</p>', unsafe_allow_html=True)
    
    # 每日金句
    from utils import get_daily_verse
    daily_verse = get_daily_verse()
    st.markdown(f"""
    <div style="background: #F8F1E3; padding: 20px; border-radius: 12px; margin: 20px 0; text-align: center; border-left: 6px solid #D4AF37;">
        <h4 style="margin: 0 0 8px 0; color: #0C2340;">📖 今日聖經金句</h4>
        <p style="font-size: 16px; margin: 0; color: #333; line-height: 1.5;">{daily_verse}</p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 主畫面控制按鈕列
# ==========================================
def render_control_buttons():
    """生成、清空、PDF 等控制按鈕"""
    closure_options = [f"{d} - {room}" for d in DAYS for room in ["Room302", "Room303", "Room202"] if not (room == "Room202" and d in ["TUESDAY", "FRIDAY"])]
    selected_closures = st.multiselect("🛠️ 設定本週「特殊不開放」時段", options=closure_options, key="special_closures")

    btn_col1, btn_col2, btn_col3 = st.columns([2, 1.5, 1.5])

    with btn_col1:
        if st.button("🚀 智能計算：生成本週全新公平值班表", type="primary", use_container_width=True):
            with st.spinner("計算中..."):
                seed = random.randint(10000, 99999)
                st.session_state.roster_df = st.session_state.get("generate_roster_func")(st.session_state.students_df, st.session_state.leave_tracker_input, selected_closures, seed)
                st.success(f"🎉 排班計算成功！動態驗證碼: SY-{seed}")
                st.toast("✅ 值班表已生成！記得備份喔～", icon="📤")

    with btn_col2:
        if st.button("🗑️ 一鍵清空當前排班表", type="secondary", use_container_width=True):
            st.session_state.show_clear_confirm = True

    if st.session_state.get("show_clear_confirm", False):
        st.markdown('<div class="warning-alert"><b>⚠️ 確定要清除全部排班？此操作將會抹除目前畫面上所有的指派安排！</b></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("💥 確定清空", type="primary"):
            st.session_state.roster_df = pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna("")
            st.session_state.show_clear_confirm = False
            st.rerun()
        if c2.button("❌ 取消返回"):
            st.session_state.show_clear_confirm = False
            st.rerun()

    return selected_closures
