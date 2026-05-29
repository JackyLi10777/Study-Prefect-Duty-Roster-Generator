# utils.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
工具模組 - PDF 專業生成、JSON 備份還原、多格式匯出

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（Streamlit Cloud 完全相容，解決休眠資料遺失問題）
"""

import streamlit as st
import pandas as pd
import json
import base64
import datetime
import io
from typing import Dict, Any, Optional
import weasyprint   # Streamlit Cloud 已透過 packages.txt 安裝

from config import (
    DAYS, ROWS_ROSTER, VERSION, APP_TITLE, PROJECT_FULL_NAME,
    get_role_style, DAILY_VERSES, NASA_COLORS
)
from data import get_demo_dataframe


# ====================== PDF 專業生成（含校徽、彩色格位、神聖金句） ======================
def generate_pdf(
    roster_df: pd.DataFrame,
    students_df: pd.DataFrame,
    audit_report: pd.DataFrame,
    global_multiplier: float = 1.0,
    logo_base64: Optional[str] = None
) -> bytes:
    """生成專業彩色 PDF 值班公告版（含校徽、角色背景色、金句、公平性統計）"""
    today = datetime.date.today().strftime("%Y年%m月%d日")

    # 取得當日金句
    weekday = today.weekday() % 5   # 星期一~五
    verse = random.choice(DAILY_VERSES.get(weekday, ["「你要專心仰賴耶和華...」——箴言 3:5"]))

    # HTML 模板（沉穩專業 + 角色顏色）
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4 landscape; margin: 15mm; }}
            body {{ font-family: "Noto Sans CJK TC", Arial, sans-serif; margin: 0; padding: 0; }}
            .header {{ text-align: center; margin-bottom: 10px; }}
            .title {{ font-size: 28px; font-weight: bold; color: #0B1E3D; letter-spacing: 3px; }}
            .subtitle {{ font-size: 18px; color: #D4AF37; margin-bottom: 5px; }}
            .date {{ font-size: 16px; color: #555; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ border: 2px solid #0B1E3D; padding: 8px 10px; text-align: center; font-size: 15px; }}
            th {{ background-color: #0B1E3D; color: white; font-weight: bold; }}
            .assist {{ background-color: #F5E8C7 !important; color: #8B5A2B; font-weight: bold; }}
            .room302 {{ background-color: #E6F4EA !important; color: #137333; }}
            .room303 {{ background-color: #FFF3E0 !important; color: #E67E22; }}
            .room202 {{ background-color: #FCE8E6 !important; color: #C5221F; }}
            .closed {{ background-color: #F1F1F1 !important; color: #777; font-size: 18px; }}
            .verse {{ 
                margin-top: 25px; padding: 20px; background: linear-gradient(135deg, #1C2526, #2C3E50); 
                color: #F4D03F; font-size: 18px; text-align: center; border-radius: 12px; 
                box-shadow: 0 8px 20px rgba(0,0,0,0.3); line-height: 1.6;
            }}
            .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_base64}" width="90" style="vertical-align:middle;margin-right:15px;">' if logo_base64 else ''}
            <span class="title">{PROJECT_FULL_NAME}</span><br>
            <span class="subtitle">值班公告版 • {today}</span><br>
            <span class="date">全域負荷倍率：{global_multiplier}×</span>
        </div>

        <table>
            <thead>
                <tr>
                    <th>崗位 / 日期</th>
                    {''.join(f"<th>{day}</th>" for day in DAYS)}
                </tr>
            </thead>
            <tbody>
    """

    for row in ROWS_ROSTER:
        html += f"<tr><td style='font-weight:bold;'>{row}</td>"
        for day in DAYS:
            val = roster_df.at[row, day]
            if val == "⬜":
                html += f"<td class='closed'>⬜</td>"
            elif val == "❌":
                html += f"<td style='background:#fee;'>❌</td>"
            elif val:
                # 根據角色上色
                base_role = row.split(" - ")[0].strip()
                style = get_role_style(base_role)
                color_class = ""
                if "Assist" in base_role:
                    color_class = "assist"
                elif "302" in base_role:
                    color_class = "room302"
                elif "303" in base_role:
                    color_class = "room303"
                elif "202" in base_role:
                    color_class = "room202"
                html += f"<td class='{color_class}'>{val}</td>"
            else:
                html += "<td></td>"
        html += "</tr>"

    html += f"""
            </tbody>
        </table>

        <div class="verse">
            <strong>每日聖經金句</strong><br>
            {verse}
        </div>

        <div class="footer">
            聖言中學導學風紀當值排班平台 v{VERSION}<br>
            公平性監控報告已附於下方 • 由 Head Study Prefect 26-27 LI Chuangjie Jacky 製作
        </div>

        <h3 style="margin-top:40px; color:#0B1E3D;">累計工作負荷審計表</h3>
        {audit_report.to_html(index=False, classes="table", border=0)}
    </body>
    </html>
    """

    # 生成 PDF
    pdf_bytes = weasyprint.HTML(string=html).write_pdf()
    return pdf_bytes


# ====================== JSON 完整備份 / 還原（解決 Streamlit Cloud 休眠問題） ======================
def export_system_backup() -> Dict[str, Any]:
    """匯出完整系統備份（名冊 + 排班表 + 手動負荷 + 設定）"""
    return {
        "version": VERSION,
        "timestamp": datetime.datetime.now().isoformat(),
        "students_df": st.session_state.get("students_df", get_demo_dataframe()).to_dict(orient="records"),
        "roster_df": st.session_state.get("roster_df", pd.DataFrame()).to_dict() if "roster_df" in st.session_state else None,
        "manual_weights": st.session_state.get("manual_weights", pd.DataFrame()).to_dict() if "manual_weights" in st.session_state else None,
        "global_load_multiplier": st.session_state.get("global_load_multiplier", 1.0),
        "leave_students": st.session_state.get("leave_students", []),
        "special_closures": st.session_state.get("special_closures", [])
    }


def import_system_backup(backup_data: Dict[str, Any]) -> bool:
    """還原完整系統備份"""
    try:
        st.session_state.students_df = pd.DataFrame(backup_data["students_df"])
        if backup_data.get("roster_df"):
            st.session_state.roster_df = pd.DataFrame.from_dict(backup_data["roster_df"])
        if backup_data.get("manual_weights"):
            st.session_state.manual_weights = pd.DataFrame.from_dict(backup_data["manual_weights"])
        st.session_state.global_load_multiplier = backup_data.get("global_load_multiplier", 1.0)
        st.session_state.leave_students = backup_data.get("leave_students", [])
        st.session_state.special_closures = backup_data.get("special_closures", [])
        return True
    except Exception as e:
        st.error(f"還原失敗: {str(e)}")
        return False


# ====================== 多格式快速匯出 ======================
def export_to_excel(roster_df: pd.DataFrame, report_df: pd.DataFrame) -> bytes:
    """匯出 Excel（含兩個 Sheet）"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        roster_df.to_excel(writer, sheet_name="值班表")
        report_df.to_excel(writer, sheet_name="負荷統計", index=False)
    return output.getvalue()


def export_to_markdown(roster_df: pd.DataFrame, report_df: pd.DataFrame) -> str:
    """匯出 Markdown"""
    md = "### 值班公告版\n\n"
    md += roster_df.to_markdown()
    md += "\n\n### 累計工作負荷統計\n\n"
    md += report_df.to_markdown(index=False)
    return md


# ====================== 傳統 Excel 導入處理 ======================
def process_roster_import(uploaded_file) -> Optional[pd.DataFrame]:
    """傳統 Excel / CSV 導入（自動轉換欄位）"""
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        st.success(f"✅ 已讀取 {len(df)} 筆資料")
        return df
    except Exception as e:
        st.error(f"導入失敗: {str(e)}")
        return None


print("✅ utils.py 已載入完成 - PDF 生成、備份還原、多格式匯出工具模組就緒")
