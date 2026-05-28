# ai_parser.py
import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from config import GEMINI_MODEL

# ==================== Gemini 初始化 ====================
if "gemini_configured" not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        st.session_state.gemini_configured = True
        st.success("✅ Gemini API 已連線")
    except Exception:
        st.session_state.gemini_configured = False
        st.warning("⚠️ Gemini API 未設定，將使用傳統解析")

# ==================== AI 欄位智能對應 ====================
def get_column_mapping_from_ai(df: pd.DataFrame) -> dict:
    if not st.session_state.get("gemini_configured", False):
        return {}
    
    sample = df.head(3).to_csv(index=False)
    prompt = f"""
你是 Excel 欄位對應專家。
以下是用戶上傳的名冊前 3 列（CSV）：
{sample}

請嚴格回傳以下 JSON，不要任何其他文字：
{{
  "姓名": "正確欄位名或 null",
  "年級": "正確欄位名或 null",
  "班別": "正確欄位名或 null",
  "職級": "正確欄位名或 null",
  "固定總值班": "正確欄位名或 null",
  "可用日子": "正確欄位名或 null",
  "歷史累計(次)": "正確欄位名或 null",
  "歷史動態(點)": "正確欄位名或 null",
  "備註": "正確欄位名或 null"
}}
"""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"): 
            text = text.split("```json")[1].split("```")[0]
        elif text.startswith("```"): 
            text = text.split("```")[1]
        return json.loads(text)
    except:
        return {}

# ==================== 智能名冊導入 ====================
def smart_process_roster_import(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # AI 嘗試
    ai_map = get_column_mapping_from_ai(df)

    # 傳統高容錯映射
    mapping = {
        "姓名": ["姓名", "name", "學生姓名", "Prefect Name"],
        "年級": ["年級", "form", "Form"],
        "班別": ["班別", "class", "Class"],
        "職級": ["職級", "role", "Role"],
        "固定總值班": ["固定總值班", "fixed_general_duty"],
        "可用日子": ["可用日子", "available", "Available Days"],
        "歷史累計(次)": ["歷史累計(次)", "history_duties"],
        "歷史動態(點)": ["歷史動態(點)", "history_weight"],
        "備註": ["備註", "remarks", "Remarks"]
    }

    rename_dict = {}
    for target, candidates in mapping.items():
        for col in df.columns:
            col_str = str(col).strip()
            if any(c.lower() in col_str.lower() for c in candidates) or (target in ai_map and ai_map[target] == col_str):
                rename_dict[col] = target
                break

    if rename_dict:
        df = df.rename(columns=rename_dict)

    # 確保必要欄位
    for col in ["姓名", "年級", "職級", "可用日子"]:
        if col not in df.columns:
            df[col] = ""

    return df

# ==================== AI 解析備註 ====================
def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    if not st.session_state.get("gemini_configured", False):
        st.warning("AI 功能未啟用")
        return students_df

    df = students_df.copy()
    if "備註" not in df.columns:
        return df

    for idx, row in df.iterrows():
        remark = str(row.get("備註", "")).strip()
        if not remark or remark.lower() == "nan":
            continue

        prompt = f"""
分析以下備註，只回傳純 JSON：
備註：{remark}

{{"is_leave": true/false, "fixed_duty": "MONDAY,TUESDAY..." 或 null, "note": "簡短說明"}}
"""
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            result = json.loads(response.text.strip())
            if result.get("is_leave"):
                df.at[idx, "備註"] = "請假"
            if result.get("fixed_duty"):
                df.at[idx, "固定總值班"] = result["fixed_duty"]
        except:
            continue

    return df