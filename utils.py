# utils.py
import streamlit as st
import pandas as pd
import io
import json
import datetime
import base64
import google.generativeai as genai

from config import DAYS, ROWS_ROSTER, NASA_COLORS, get_role_style, GEMINI_MODEL

# ==========================================
# PDF 支援強固檢查
# ==========================================
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False
    st.warning("⚠️ WeasyPrint 未就緒（PDF 功能暫時無法使用）。請確認 GitHub 已加入 packages.txt 並重新部署。")

# ==========================================
# Gemini 配置
# ==========================================
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(GEMINI_MODEL)
else:
    model = None

# ==========================================
# PDF 專用顏色樣式函數（完整版 - 與 config.py 完全配合）
# ==========================================
def get_cell_style(val, role, day):
    val = str(val).strip()

    if val == "X":
        return f"color:{NASA_COLORS['x_text']}; font-weight:bold; background-color:{NASA_COLORS['x_bg']}; text-align:center; border:2px solid {NASA_COLORS['x_border']};"

    if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
        return f"background-color:{NASA_COLORS['closed_bg']}; color:#546E7A; font-style:italic; text-align:center; border:1px solid #90A4AE;"

    if val == "":
        return f"background-color:{NASA_COLORS['empty_bg']}; text-align:center;"

    # 核心：呼叫 config.py 的 get_role_style，確保所有房間都有正確顏色
    style = get_role_style(role, day)

    return (
        f"font-weight:bold; text-align:center; padding:9px 7px; "
        f"background-color:{style['bg']}; "
        f"color:{style['text']}; "
        f"border:{style['border']};"
    )

# ==========================================
# 名冊導入引擎（傳統格式）
# ==========================================
def process_roster_import(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        mapping = {
            '姓名': 'name', 'name': 'name', 'Prefect Name': 'name', '學生姓名': 'name',
            '年級': 'form', 'form': 'form', 'Form': 'form',
            '班別': 'class', 'class': 'class', 'Class': 'class',
            '職級': 'role', 'role': 'role', 'Role': 'role',
            '學年固定總值班': 'fixed_general_duty', 'fixed_general_duty': 'fixed_general_duty',
            '可用日子': 'available', 'available': 'available',
            '歷史累計(次)': 'history_duties', 'history_duties': 'history_duties',
            '歷史動態(點)': 'history_weight', 'history_weight': 'history_weight',
            '備註': 'remarks', 'remarks': 'remarks'
        }

        df = df.rename(columns=lambda x: mapping.get(str(x).strip(), str(x).strip()))

        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required_cols:
            if col not in df.columns:
                if col == "fixed_general_duty": df[col] = "NONE"
                elif col == "available": df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                elif col == "history_duties": df[col] = 0
                elif col == "history_weight": df[col] = 0.0
                else: df[col] = ""

        df = df[required_cols]
        df["name"] = df["name"].astype(str).str.strip()
        df = df[(df["name"] != "") & (df["name"] != "nan")]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors='coerce').fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors='coerce').fillna(0.0)

        st.session_state.students_df = df
        st.sidebar.success(f"🎉 成功導入 {len(df)} 位領袖生名冊！")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 導入失敗: {str(e)}")

# ==========================================
# AI 智能名冊導入（任意格式）
# ==========================================
def smart_process_roster_import(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty or len(df.columns) < 2:
            st.error("❌ 檔案為空或格式不正確")
            return

        from ai_parser import get_column_mapping_from_ai
        mapping = get_column_mapping_from_ai(df)

        rename_dict = {v: k for k, v in mapping.items() if v in df.columns}
        df = df.rename(columns=rename_dict)

        required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
        for col in required_cols:
            if col not in df.columns:
                if col == "fixed_general_duty": df[col] = "NONE"
                elif col == "available": df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                elif col == "history_duties": df[col] = 0
                elif col == "history_weight": df[col] = 0.0
                else: df[col] = ""

        df["name"] = df["name"].astype(str).str.strip()
        df = df[df["name"].notna() & (df["name"] != "")]
        df["history_duties"] = pd.to_numeric(df["history_duties"], errors="coerce").fillna(0).astype(int)
        df["history_weight"] = pd.to_numeric(df["history_weight"], errors="coerce").fillna(0.0)

        st.session_state.students_df = df[required_cols].reset_index(drop=True)
        st.success(f"🎉 AI 智能導入成功！已處理 {len(df)} 位領袖生（自動匹配欄位）")
        st.rerun()

    except Exception as e:
        st.error(f"❌ AI 智能導入失敗: {str(e)}")
        st.info("💡 提示：若 AI 無法解析，可使用傳統格式導入")

# ==========================================
# 系統完整備份 / 還原
# ==========================================
def export_system_backup(master_df):
    backup_data = {
        "master_report": master_df.to_dict(orient="records"),
        "roster_table": st.session_state.roster_df.to_dict(orient="index"),
        "manual_weights": st.session_state.get("manual_weights", pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)).to_dict(orient="index"),
        "leave_tracker": st.session_state.leave_tracker_input
    }
    return json.dumps(backup_data, ensure_ascii=False, indent=2)

def import_system_backup(uploaded_json_file):
    try:
        data = json.load(uploaded_json_file)
        if "master_report" in data and "roster_table" in data:
            raw_master = pd.DataFrame(data["master_report"])
            mapping_reverse = {
                "學生姓名 (Prefect Name)": "name",
                "年級 (Form)": "form",
                "班別 (Class)": "class",
                "職級 (Role)": "role",
                "學年固定總值班": "fixed_general_duty",
                "最終總計值班次數 (次)": "history_duties",
                "最終總計加權負荷 (點)": "history_weight",
                "備註": "remarks"
            }
            renamed_df = raw_master.rename(columns=mapping_reverse)

            required_cols = ["name", "form", "class", "role", "fixed_general_duty", "available", "history_duties", "history_weight", "remarks"]
            for col in required_cols:
                if col not in renamed_df.columns:
                    if col == "fixed_general_duty": renamed_df[col] = "NONE"
                    elif col == "available": renamed_df[col] = "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY"
                    elif col == "history_duties": renamed_df[col] = 0
                    elif col == "history_weight": renamed_df[col] = 0.0
                    else: renamed_df[col] = ""

            st.session_state.students_df = renamed_df[required_cols]

            restored_roster = pd.DataFrame.from_dict(data["roster_table"], orient="index")
            st.session_state.roster_df = restored_roster.reindex(index=ROWS_ROSTER, columns=DAYS).fillna("")

            if "manual_weights" in data:
                manual_df = pd.DataFrame.from_dict(data["manual_weights"], orient="index")
                st.session_state.manual_weights = manual_df.reindex(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)

            st.session_state.leave_tracker_input = data.get("leave_tracker", [])
            st.sidebar.success("🔮 備份已完美還原（包含手動調整負荷）！")
            st.rerun()
        else:
            st.sidebar.error("❌ 備份檔結構不符")
    except Exception as e:
        st.sidebar.error(f"❌ 還原失敗: {str(e)}")

# ==========================================
# A4 橫式彩色 PDF 生成引擎（NASA 深邃風格 - 最終版）
# ==========================================
def generate_pdf(roster_df, master_report_df, logo_b64=None):
    if not PDF_AVAILABLE:
        st.error("❌ PDF 引擎未就緒，請確認 packages.txt 已加入 weasyprint 並重新部署")
        return None

    if logo_b64 is None:
        if st.session_state.get("logo_data"):
            logo_b64 = base64.b64encode(st.session_state.logo_data).decode()
        else:
            try:
                with open("logo.png", "rb") as f:
                    logo_data = f.read()
                    logo_b64 = base64.b64encode(logo_data).decode()
                    st.session_state.logo_data = logo_data
            except FileNotFoundError:
                logo_b64 = None

    today = datetime.date.today().strftime("%Y-%m-%d")

    # ==================== 建立彩色值班表 HTML ====================
    html_table = "<table style='width:100%; border-collapse:collapse; font-size:11px; margin:15px 0;'>"

    # Header Row
    html_table += f"<tr><th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:2px solid {NASA_COLORS['accent_gold']};'>崗位</th>"
    for day in DAYS:
        html_table += f"<th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:1px solid {NASA_COLORS['accent_gold']};'>{day}</th>"
    html_table += "</tr>"

    # Data Rows
    for role in roster_df.index:
        # 角色欄（第一列）使用深藍 + 金色文字 + 粗金邊框
        html_table += f"<tr><td style='background-color:{NASA_COLORS['header_bg']}; color:{NASA_COLORS['accent_gold']}; font-weight:bold; padding:10px; text-align:center; border:3px solid {NASA_COLORS['accent_gold']};'>{role}</td>"

        for day in DAYS:
            val = str(roster_df.at[role, day]).strip()
            style = get_cell_style(val, role, day)
            html_table += f"<td style='{style}'>{val if val else '&nbsp;'}</td>"
        html_table += "</tr>"

    html_table += "</table>"

    # 工作負荷統計表
    report_table = master_report_df.to_html(index=False, classes='table')

    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 12mm; }}
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.4; }}
        .header-container {{ text-align: center; margin-bottom: 15px; }}
        h1 {{ color:{NASA_COLORS['header_bg']}; font-size: 24px; margin: 5px 0; }}
        h2 {{ color:{NASA_COLORS['accent_gold']}; font-size: 15px; margin: 0 0 8px 0; font-weight: 600; }}
        .date-sub {{ font-size: 11px; color: #666; margin-bottom: 12px; }}
        h3 {{ color:{NASA_COLORS['header_bg']}; border-left: 5px solid {NASA_COLORS['accent_gold']}; padding-left: 10px; margin-top: 20px; font-size: 15px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 11px; }}
        th, td {{ border: 1px solid #BDC3C7; padding: 8px 10px; text-align: center; }}
        th {{ background-color: {NASA_COLORS['header_bg']}; color: white; font-weight: bold; }}
    </style></head><body>
    <div class="header-container">
    """
    if logo_b64:
        html += f'<img src="data:image/png;base64,{logo_b64}" style="height:60px; margin-bottom:8px;">'
    html += f"""
        <h1>Sing Yin Secondary School</h1>
        <h2>Study Prefect Duty Roster & Workload Audit</h2>
        <div class="date-sub">Report Generated: {today}</div>
    </div>
    <h3>📅 本週值班表 (Weekly Duty Roster)</h3>
    {html_table}
    <div style="page-break-before: always;"></div>
    <h3>📊 累積動態工作負荷審計表</h3>
    {report_table}
    </body></html>
    """
    return HTML(string=html).write_pdf()