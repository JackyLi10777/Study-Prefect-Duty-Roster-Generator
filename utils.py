# ==========================================
# A4 橫式彩色 PDF 生成引擎（NASA 深邃風格 - 最終修正版）
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
        # 角色欄（第一列）- 深太空藍 + 金色文字 + 粗金邊框（NASA 儀表板風格）
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