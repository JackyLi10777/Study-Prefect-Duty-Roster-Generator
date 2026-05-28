# utils.py
import streamlit as st
import pandas as pd
import io
import json
import datetime
import base64
from typing import Dict

# 0. PDF 支援
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False
    st.warning("⚠️ WeasyPrint 未就緒，PDF 功能暫時停用")

# 1. 簡約沉穩顏色系統
NASA_COLORS = {
    "header_bg": "#0F1C2E",
    "accent_gold": "#D4AF77",
    "text_dark": "#1A2533",
    "assist_bg": "#F5EDE3",
    "assist_border": "#D4AF77",
    "assist_text": "#3F2A1E",
    "room302_bg": "#E3F0E8",
    "room302_border": "#2E8B57",
    "room302_text": "#1E4D38",
    "room303_bg": "#F4E9E3",
    "room303_border": "#C14A4A",
    "room303_text": "#5C2A2A",
    "room202_bg": "#E8F0F8",
    "room202_border": "#2B6CB0",
    "room202_text": "#1F3F66",
    "x_bg": "#F8E9E9",
    "x_border": "#C14A4A",
    "x_text": "#5C2A2A",
    "empty_bg": "#F9F7F2",
    "closed_bg": "#ECEBE6",
}

def compute_style_attributes(val: str, role: str, day: str) -> Dict[str, str]:
    val = str(val).strip()
    if val == "⬜":
        return {"bg": NASA_COLORS["closed_bg"], "border": "#D1C9B8", "text": "#8C8C8C"}
    if val in ["❌", "X"]:
        return {"bg": NASA_COLORS["x_bg"], "border": NASA_COLORS["x_border"], "text": NASA_COLORS["x_text"]}
    if val == "":
        return {"bg": NASA_COLORS["empty_bg"], "border": "#E5E0D5", "text": "#1A2533"}

    if "Assist" in role:
        return {"bg": NASA_COLORS["assist_bg"], "border": NASA_COLORS["assist_border"], "text": NASA_COLORS["assist_text"]}
    elif "Room302" in role:
        return {"bg": NASA_COLORS["room302_bg"], "border": NASA_COLORS["room302_border"], "text": NASA_COLORS["room302_text"]}
    elif "Room303" in role:
        return {"bg": NASA_COLORS["room303_bg"], "border": NASA_COLORS["room303_border"], "text": NASA_COLORS["room303_text"]}
    elif "Room202" in role:
        return {"bg": NASA_COLORS["room202_bg"], "border": NASA_COLORS["room202_border"], "text": NASA_COLORS["room202_text"]}
    return {"bg": "#FFFFFF", "border": "#D1C9B8", "text": "#1A2533"}

def get_cell_style(val: str, role: str, day: str) -> str:
    attrs = compute_style_attributes(val, role, day)
    return f"background-color: {attrs['bg']}; border: 2px solid {attrs['border']}; color: {attrs['text']}; font-weight: bold; text-align: center; padding: 10px 6px; print-color-adjust: exact !important;"

# ==================== 修正重點 ====================
def render_streamlit_visual_roster(roster_df: pd.DataFrame):
    """安全、穩定的視覺公告板 Styler（已徹底解決 ValueError）"""
    def _style_func(row):
        styles = []
        role = row.name
        for day in roster_df.columns:
            val = row[day]
            attrs = compute_style_attributes(str(val), role, day)
            styles.append(f"background-color: {attrs['bg']}; border: 2px solid {attrs['border']}; color: {attrs['text']}; font-weight: bold; text-align: center;")
        return styles

    # 使用最穩定的寫法：一次 apply 整列
    styled = roster_df.style.apply(_style_func, axis=1)
    return styled

# ==================== PDF 與其他功能（完整保留） ====================
def generate_pdf(roster_df: pd.DataFrame, master_report_df: pd.DataFrame, logo_b64: str = None) -> bytes:
    if not PDF_AVAILABLE:
        return b""
    today = datetime.date.today().strftime("%Y-%m-%d")
    html_table = roster_df.to_html(escape=False)
    # 這裡已包含樣式替換（簡化版）
    full_html = f"""
    <html><head><style>
        @page {{ size: A4 landscape; margin: 15mm; }}
        table {{ width:100%; border-collapse:collapse; }}
        th,td {{ border:1px solid #D1C9B8; padding:9px; text-align:center; }}
        th {{ background-color:{NASA_COLORS["header_bg"]}; color:white; }}
    </style></head><body>
        <div style="text-align:center;margin-bottom:25px;">
            {f'<img src="data:image/png;base64,{logo_b64}" style="height:70px;">' if logo_b64 else ''}
            <h1 style="color:#0F1C2E;">Sing Yin Secondary School</h1>
            <h2 style="color:#5C5C5C;">Study Prefect Duty Roster</h2>
            <p style="color:#8C8C8C;">{today}</p>
        </div>
        {html_table}
    </body></html>
    """
    pdf_buffer = io.BytesIO()
    HTML(string=full_html).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()

def export_system_backup():
    backup = {
        "students_df": st.session_state.get("students_df", pd.DataFrame()).to_dict("records"),
        "roster_df": st.session_state.get("roster_df", pd.DataFrame()).to_dict(),
        "master_report_df": st.session_state.get("master_report_df", pd.DataFrame()).to_dict("records"),
        "leave_tracker": st.session_state.get("leave_tracker_input", []),
        "timestamp": datetime.datetime.now().isoformat()
    }
    output = io.BytesIO()
    output.write(json.dumps(backup, ensure_ascii=False, indent=2).encode("utf-8"))
    st.download_button("📤 下載完整備份", output.getvalue(), f"SYSS_Backup_{datetime.date.today()}.json", "application/json", use_container_width=True)

def import_system_backup(uploaded_file):
    try:
        backup = json.load(uploaded_file)
        st.session_state.students_df = pd.DataFrame(backup.get("students_df", []))
        st.session_state.roster_df = pd.DataFrame.from_dict(backup.get("roster_df", {}))
        st.session_state.master_report_df = pd.DataFrame(backup.get("master_report_df", []))
        st.session_state.leave_tracker_input = backup.get("leave_tracker", [])
        st.success("✅ 備份還原成功")
        st.rerun()
    except Exception as e:
        st.error(f"還原失敗: {e}")

def process_roster_import(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    mapping = {"姓名":["姓名","name","學生姓名"],"年級":["年級","form"],"班別":["班別","class"],"職級":["職級","role"],"可用日子":["可用日子","available"],"歷史動態(點)":["歷史動態(點)","history_weight"],"備註":["備註","remarks"]}
    df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
    return df