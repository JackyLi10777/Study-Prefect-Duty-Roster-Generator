# utils.py
import streamlit as st
import pandas as pd
import io
import json
import datetime
import base64
from typing import Dict, Any

# ==========================================
# 0. PDF 支援強固檢查
# ==========================================
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception):
    PDF_AVAILABLE = False
    st.warning("⚠️ WeasyPrint 未就緒，PDF 匯出功能暫時停用")

# ==========================================
# 1. 簡約沉穩 NASA 風格顏色系統（背景色明顯）
# ==========================================
NASA_COLORS = {
    "header_bg": "#0F1C2E",
    "accent_gold": "#D4AF77",
    "text_dark": "#1A2533",
    "assist_bg": "#F5EDE3",      # 溫暖金米
    "assist_border": "#D4AF77",
    "assist_text": "#3F2A1E",
    "room302_bg": "#E3F0E8",     # 清新沉穩綠
    "room302_border": "#2E8B57",
    "room302_text": "#1E4D38",
    "room303_bg": "#F4E9E3",     # 沉穩紅
    "room303_border": "#C14A4A",
    "room303_text": "#5C2A2A",
    "room202_bg": "#E8F0F8",     # 專業藍
    "room202_border": "#2B6CB0",
    "room202_text": "#1F3F66",
    "x_bg": "#F8E9E9",
    "x_border": "#C14A4A",
    "x_text": "#5C2A2A",
    "empty_bg": "#F9F7F2",
    "closed_bg": "#ECEBE6",
}

def compute_style_attributes(val: str, role: str, day: str) -> Dict[str, str]:
    """統一計算樣式屬性（網頁 + PDF 共用）"""
    val = str(val).strip()
    if val == "⬜":
        return {"bg": NASA_COLORS["closed_bg"], "border": "#D1C9B8", "text": "#8C8C8C", "style": "italic"}
    if val == "❌" or val.upper() == "X":
        return {"bg": NASA_COLORS["x_bg"], "border": NASA_COLORS["x_border"], "text": NASA_COLORS["x_text"], "style": "bold"}
    if val == "":
        return {"bg": NASA_COLORS["empty_bg"], "border": "#E5E0D5", "text": "#1A2533", "style": "normal"}

    # 角色背景色
    if "Assist" in role:
        return {"bg": NASA_COLORS["assist_bg"], "border": NASA_COLORS["assist_border"], "text": NASA_COLORS["assist_text"], "style": "bold"}
    elif "Room302" in role:
        return {"bg": NASA_COLORS["room302_bg"], "border": NASA_COLORS["room302_border"], "text": NASA_COLORS["room302_text"], "style": "bold"}
    elif "Room303" in role:
        return {"bg": NASA_COLORS["room303_bg"], "border": NASA_COLORS["room303_border"], "text": NASA_COLORS["room303_text"], "style": "bold"}
    elif "Room202" in role:
        return {"bg": NASA_COLORS["room202_bg"], "border": NASA_COLORS["room202_border"], "text": NASA_COLORS["room202_text"], "style": "bold"}

    return {"bg": "#FFFFFF", "border": "#D1C9B8", "text": "#1A2533", "style": "normal"}


def get_cell_style(val: str, role: str, day: str) -> str:
    """返回完整的 inline style 字串（供 PDF 使用）"""
    attrs = compute_style_attributes(val, role, day)
    return (
        f"background-color: {attrs['bg']}; "
        f"border: 2px solid {attrs['border']}; "
        f"color: {attrs['text']}; "
        f"font-weight: {attrs['style']}; "
        f"text-align: center; "
        f"padding: 10px 6px; "
        f"print-color-adjust: exact !important;"
    )


def render_streamlit_visual_roster(roster_df: pd.DataFrame) -> pd.DataFrame:
    """讓網頁視覺公告板也顯示相同顏色"""
    def style_func(val, role, day):
        attrs = compute_style_attributes(str(val), role, day)
        return f"background-color: {attrs['bg']}; border: 2px solid {attrs['border']}; color: {attrs['text']}; font-weight: bold; text-align: center;"
    
    styled = roster_df.style
    for i, role in enumerate(roster_df.index):
        for j, day in enumerate(roster_df.columns):
            styled = styled.apply(lambda x, r=role, d=day: [style_func(x, r, d)] * len(x) if x.name == role else [""], axis=1)
    return styled


def generate_pdf(roster_df: pd.DataFrame, master_report_df: pd.DataFrame, logo_b64: str = None) -> bytes:
    """生成 PDF - 沉穩專業版 + 明顯背景色"""
    if not PDF_AVAILABLE:
        st.error("PDF 引擎未就緒")
        return b""

    today = datetime.date.today().strftime("%Y-%m-%d")

    # 建立 HTML 表格
    html_table = roster_df.to_html(escape=False, index=True)
    # 替換成帶樣式的表格
    for role in roster_df.index:
        for day in roster_df.columns:
            val = str(roster_df.at[role, day])
            style_str = get_cell_style(val, role, day)
            html_table = html_table.replace(
                f"<td>{val}</td>",
                f'<td style="{style_str}">{val}</td>'
            )

    full_html = f"""
    <html>
    <head>
        <style>
            @page {{ size: A4 landscape; margin: 15mm; }}
            body {{ font-family: "Noto Sans TC", sans-serif; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 11px; }}
            th, td {{ border: 1px solid #D1C9B8; padding: 9px 8px; text-align: center; }}
            th {{ background-color: {NASA_COLORS["header_bg"]}; color: white; font-weight: bold; }}
            .header {{ text-align: center; margin-bottom: 25px; }}
            .verse {{ font-size: 13px; color: #5C5C5C; margin: 30px 0; text-align: center; font-style: italic; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_b64}" style="height:70px;margin-bottom:12px;">' if logo_b64 else ''}
            <h1 style="color:#0F1C2E;margin:0;">Sing Yin Secondary School</h1>
            <h2 style="color:#5C5C5C;margin:8px 0 0 0;">Study Prefect Duty Roster</h2>
            <p style="color:#8C8C8C;font-size:12px;">Generated on {today}</p>
        </div>
        {html_table}
    </body>
    </html>
    """

    pdf_buffer = io.BytesIO()
    HTML(string=full_html).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()


def export_system_backup():
    """完整系統備份"""
    backup = {
        "students_df": st.session_state.get("students_df", pd.DataFrame()).to_dict("records"),
        "roster_df": st.session_state.get("roster_df", pd.DataFrame()).to_dict(),
        "master_report_df": st.session_state.get("master_report_df", pd.DataFrame()).to_dict("records"),
        "leave_tracker": st.session_state.get("leave_tracker_input", []),
        "timestamp": datetime.datetime.now().isoformat()
    }
    output = io.BytesIO()
    output.write(json.dumps(backup, ensure_ascii=False, indent=2).encode("utf-8"))
    st.download_button(
        label="📤 下載完整系統備份 (JSON)",
        data=output.getvalue(),
        file_name=f"SingYin_Prefect_Backup_{datetime.date.today()}.json",
        mime="application/json",
        use_container_width=True
    )


def import_system_backup(uploaded_file):
    """還原備份"""
    try:
        backup = json.load(uploaded_file)
        st.session_state.students_df = pd.DataFrame(backup.get("students_df", []))
        st.session_state.roster_df = pd.DataFrame.from_dict(backup.get("roster_df", {}))
        st.session_state.master_report_df = pd.DataFrame(backup.get("master_report_df", []))
        st.session_state.leave_tracker_input = backup.get("leave_tracker", [])
        st.success("✅ 備份已成功還原")
        st.rerun()
    except Exception as e:
        st.error(f"還原失敗: {e}")


def process_roster_import(uploaded_file):
    """傳統名冊導入（保留彈性欄位對應）"""
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # 彈性欄位對應（支援多種命名方式）
    mapping = {
        "姓名": "姓名", "name": "姓名", "學生姓名": "姓名",
        "年級": "年級", "form": "年級",
        "班別": "班別", "class": "班別",
        "職級": "職級", "role": "職級",
        "可用日子": "可用日子", "available": "可用日子",
        "歷史累計(次)": "歷史累計(次)",
        "歷史動態(點)": "歷史動態(點)",
        "備註": "備註", "remarks": "備註"
    }
    df = df.rename(columns=lambda x: mapping.get(str(x).strip(), x))
    return df