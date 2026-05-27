# utils.py
import streamlit as st
import pandas as pd
import io
import json
import datetime
import base64
import google.generativeai as genai

from config import DAYS, ROWS_ROSTER, NASA_COLORS, get_role_style, GEMINI_MODEL
from ai_parser import get_column_mapping_from_ai

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
# 單元格樣式計算核心（背景填充加強版）
# ==========================================
def compute_style_attributes(val, role, day):
    """
    高維度抽象核心：統一計算單元格的顏色與邊框屬性，
    供 PDF 與 Streamlit 視覺控告板共用。
    補回舊版所有狀態處理邏輯。
    """
    val = str(val).strip()

    if val == "X":
        return {
            "bg": NASA_COLORS['x_bg'],
            "text": NASA_COLORS['x_text'],
            "border": f"2px solid {NASA_COLORS['x_border']}",
        }

    if 'Room202' in role and day in ['TUESDAY', 'FRIDAY']:
        return {
            "bg": NASA_COLORS['closed_bg'],
            "text": "#546E7A",
            "border": "2px solid #90A4AE",
        }

    if val == "":
        return {
            "bg": NASA_COLORS['empty_bg'],
            "text": "#333333",
            "border": "1px solid #E5E7EB",
        }

    style = get_role_style(role, day)
    return {
        "bg": style.get('bg', '#FFFFFF'),
        "text": style.get('text', '#000000'),
        "border": style.get('border', '1px solid #BDC3C7'),
    }

# ==========================================
# PDF 專用顏色樣式函數（背景色明顯加強版）
# ==========================================
def get_cell_style(val, role, day):
    """
    供 PDF 生成使用的單元格樣式字串。
    背景色使用 !important 強制填充格子。
    """
    attrs = compute_style_attributes(val, role, day)
    return (
        f"background-color: {attrs['bg']} !important; "
        f"color: {attrs['text']} !important; "
        f"border: {attrs['border']} !important; "
        f"font-weight: bold !important; "
        f"text-align: center !important; "
        f"padding: 10px 8px !important;"
    )

# ==========================================
# Streamlit 視覺控告板專用渲染器（補回舊版功能）
# ==========================================
def render_streamlit_visual_roster(df: pd.DataFrame):
    """
    供主界面使用的 Pandas Styler 渲染器，讓網頁視覺公告版也有完整顏色。
    這是舊版本中「視覺控告板彩色顯示」功能的完整補回。
    """
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    for role in df.index:
        for day in df.columns:
            val = df.at[role, day]
            attrs = compute_style_attributes(val, role, day)
            style_df.at[role, day] = (
                f"background-color: {attrs['bg']}; "
                f"color: {attrs['text']}; "
                f"font-weight: bold;"
            )
    return df.style.apply(lambda _: style_df, axis=None)

# ==========================================
# 名冊導入引擎（傳統格式）
# ==========================================
def process_roster_import(uploaded_file):
    """傳統格式導入引擎（舊版功能完整保留）"""
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
# AI 智能名冊導入
# ==========================================
def smart_process_roster_import(uploaded_file):
    """AI 智能名冊導入（舊版功能完整保留）"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty or len(df.columns) < 2:
            st.error("❌ 檔案為空或格式不正確")
            return

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
# 系統完整備份 / 還原（舊版功能完整保留）
# ==========================================
def export_system_backup(master_df):
    """匯出完整系統備份（包含手動調整負荷）"""
    backup_data = {
        "master_report": master_df.to_dict(orient="records"),
        "roster_table": st.session_state.roster_df.to_dict(orient="index"),
        "manual_weights": st.session_state.get("manual_weights", pd.DataFrame(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)).to_dict(orient="index"),
        "leave_tracker": st.session_state.get("leave_tracker_input", [])
    }
    return json.dumps(backup_data, ensure_ascii=False, indent=2)

def import_system_backup(uploaded_json_file):
    """還原完整系統備份（補回舊版完整還原邏輯）"""
    try:
        data = json.load(uploaded_json_file)
        if "master_report" in data and "roster_table" in data:
            # 還原學生名冊
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

            # 還原排班表
            restored_roster = pd.DataFrame.from_dict(data["roster_table"], orient="index")
            st.session_state.roster_df = restored_roster.reindex(index=ROWS_ROSTER, columns=DAYS).fillna("")

            # 還原手動權重
            if "manual_weights" in data:
                manual_df = pd.DataFrame.from_dict(data["manual_weights"], orient="index")
                st.session_state.manual_weights = manual_df.reindex(index=ROWS_ROSTER, columns=DAYS).fillna(0.0)

            # 還原請假清單
            st.session_state.leave_tracker_input = data.get("leave_tracker", [])

            st.sidebar.success("🔮 備份已完美還原（包含手動調整負荷）！")
            st.rerun()
        else:
            st.sidebar.error("❌ 備份檔結構不符")
    except Exception as e:
        st.sidebar.error(f"❌ 還原失敗: {str(e)}")

# ==========================================
# A4 橫式彩色 PDF 生成引擎（背景填充加強版）
# ==========================================
def generate_pdf(roster_df, master_report_df, logo_b64=None):
    """最終 PDF 生成引擎（已加強背景色填充與列印色彩保留）"""
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

    html_table = "<table style='width:100%; border-collapse:collapse; font-size:11px; margin:15px 0;'>"

    # Header Row
    html_table += f"<tr><th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:2px solid {NASA_COLORS['accent_gold']};'>崗位</th>"
    for day in DAYS:
        html_table += f"<th style='background-color:{NASA_COLORS['header_bg']}; color:white; padding:10px; text-align:center; border:2px solid {NASA_COLORS['accent_gold']};'>{day}</th>"
    html_table += "</tr>"

    # Data Rows
    for role in roster_df.index:
        html_table += f"<tr><td style='background-color:{NASA_COLORS['header_bg']}; color:{NASA_COLORS['accent_gold']}; font-weight:bold; padding:10px; text-align:center; border:2px solid {NASA_COLORS['accent_gold']};'>{role}</td>"

        for day in DAYS:
            val = str(roster_df.at[role, day]).strip()
            style = get_cell_style(val, role, day)
            html_table += f"<td style='{style}'>{val if val else '&nbsp;'}</td>"
        html_table += "</tr>"

    html_table += "</table>"

    report_table = master_report_df.to_html(index=False, classes='table')

    # 關鍵修正：強制 PDF 保留背景色
    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 12mm; }}
        html, body {{
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}
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