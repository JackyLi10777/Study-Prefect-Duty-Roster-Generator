# utils.py
import streamlit as st
import pandas as pd
import io
import json
import datetime
import base64
import google.generativeai as genai

# ==========================================
# 從 config 引入必要常數
# ==========================================
from config import DAYS, ROWS_ROSTER

# ==========================================
# 0. PDF 支援強固檢查
# ==========================================
try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    PDF_AVAILABLE = False
    st.warning("⚠️ WeasyPrint 未就緒（PDF 功能暫時無法使用）。請確認 GitHub 已加入 packages.txt 並重新部署。")

# ==========================================
# Gemini 配置
# ==========================================
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
else:
    model = None

# ==========================================
# 1. 名冊導入引擎（完整版）
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
# AI 智能名冊導入（任意格式自動匹配）
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

        sample_text = df.head(8).to_string(index=False)

        prompt = f"""
請分析以下 Excel/CSV 表格內容，將欄位自動對應到標準欄位名稱。
只需輸出純 JSON，不要任何額外文字或說明。

標準欄位定義：
- "name": 姓名
- "form": 年級 (F.3、F.4、F.5)
- "class": 班別 (如 5A、4B)
- "role": 職級 (Study Prefect 或 Assistant Head Study Prefect)
- "fixed_general_duty": 學年固定總值班 (MONDAY/TUESDAY/.../NONE)
- "available": 可用日子 (逗號分隔，如 MONDAY,WEDNESDAY,FRIDAY)
- "history_duties": 歷史累計次數
- "history_weight": 歷史累計點數
- "remarks": 備註

表格前8行內容：
{sample_text}

請輸出以下格式的 JSON：
{{
  "name": "實際欄位名稱",
  "form": "實際欄位名稱",
  ...
}}
"""

        if model is None:
            st.error("❌ Gemini API 未設定，請在 .streamlit/secrets.toml 加入 GEMINI_API_KEY")
            return

        with st.spinner("🤖 AI 正在智能分析您的名冊格式..."):
            response = model.generate_content(prompt)
            json_text = response.text.strip()

            if json_text.startswith("```json"):
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif json_text.startswith("```"):
                json_text = json_text.split("```")[1].strip()

            mapping = json.loads(json_text)

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
        st.info("💡 提示：若 AI 無法解析，可使用傳統格式或檢查檔案是否損壞")

# ==========================================
# 2. 系統完整備份 / 還原
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
# 3. A4 橫式 PDF 生成引擎
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
    html_table = roster_df.to_html(classes='table')
    report_table = master_report_df[["學生姓名 (Prefect Name)", "年級 (Form)", "班別 (Class)", "職級 (Role)", "當週新增 (次)", "最終總計加權負荷 (點)"]].to_html(index=False, classes='table')
    
    html = f"""
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 20mm; }}
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.4; }}
        .header-container {{ text-align: center; margin-bottom: 25px; }}
        h1 {{ color:#0C2340; font-size: 26px; margin: 5px 0; letter-spacing: 1px; }}
        h2 {{ color:#D4AF37; font-size: 16px; margin: 0 0 10px 0; font-weight: 600; text-transform: uppercase; }}
        .date-sub {{ font-size: 11px; color: #666; margin-bottom: 20px; }}
        h3 {{ color:#0C2340; border-left: 5px solid #D4AF37; padding-left: 10px; margin-top: 30px; font-size: 16px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 11px; }}
        th, td {{ border: 1px solid #D1D5DB; padding: 8px 10px; text-align: center; }}
        th {{ background-color: #0C2340; color: white; font-weight: bold; font-size: 10px; }}
        td {{ font-weight: bold; color: #1F2937; }}
        tr:nth-child(even) td {{ background-color: #F9FAFB; }}
    </style></head><body>
    <div class="header-container">
    """
    if logo_b64:
        html += f'<img src="data:image/png;base64,{logo_b64}" style="height:65px; margin-bottom:10px;">'
    html += f"""
        <h1>Sing Yin Secondary School</h1>
        <h2>Study Prefect Duty Roster & Workload Audit</h2>
        <div class="date-sub">Report Generated Date: {today}</div>
    </div>
    <h3>📅 本週值班表 (Weekly Duty Roster)</h3>
    {html_table}
    <div style="page-break-before: always;"></div>
    <h3>📊 累積動態工作負荷審計表 (Workload Audit Report)</h3>
    {report_table}
    </body></html>
    """
    return HTML(string=html).write_pdf()