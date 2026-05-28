# ai_parser.py
# ==========================================
# AI 智能名冊解析與備註分析模組
# Gemini 3.5 Flash + 完整降級機制
# ==========================================
import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from config import GEMINI_MODEL

# 初始化 Gemini（僅第一次執行）
if "gemini_configured" not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        st.session_state.gemini_configured = True
    except Exception:
        st.session_state.gemini_configured = False


def get_column_mapping_from_ai(df: pd.DataFrame) -> dict:
    """使用 Gemini 智能判斷欄位對應"""
    if not st.session_state.get("gemini_configured", False):
        return {}

    sample_text = df.head(3).to_csv(index=False)

    prompt = f"""
你是 Excel 欄位對應專家。
以下是用戶上傳的名冊前 3 列資料（CSV格式）：
{sample_text}

請嚴格按照以下 JSON 格式回傳欄位對應關係（不要有任何額外文字）：
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
        mapping_str = response.text.strip()
        # 移除可能的多餘 markdown
        if mapping_str.startswith("```json"):
            mapping_str = mapping_str.split("```json")[1].split("```")[0]
        elif mapping_str.startswith("```"):
            mapping_str = mapping_str.split("```")[1]
        mapping = json.loads(mapping_str)
        return mapping
    except Exception as e:
        st.warning(f"AI 欄位對應失敗，使用傳統映射。錯誤: {e}")
        return {}


def smart_process_roster_import(uploaded_file) -> pd.DataFrame:
    """AI 智能 + 傳統備援的名冊導入"""
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # 先嘗試 AI 智能對應
    ai_mapping = get_column_mapping_from_ai(df)

    # 傳統強制映射（高容錯）
    manual_mapping = {
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

    final_mapping = {}
    for target, candidates in manual_mapping.items():
        for col in df.columns:
            if any(cand.lower() in str(col).lower() for cand in candidates):
                final_mapping[col] = target
                break
        # AI 優先覆蓋
        if target in ai_mapping and ai_mapping[target]:
            for col in df.columns:
                if str(col).strip() == ai_mapping[target]:
                    final_mapping[col] = target
                    break

    if final_mapping:
        df = df.rename(columns={k: v for k, v in final_mapping.items() if v in df.columns})

    # 確保必要欄位存在
    required = ["姓名", "年級", "職級", "可用日子"]
    for col in required:
        if col not in df.columns:
            df[col] = ""

    return df


def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    """AI 自動解析備註欄（偵測請假、固定值班等）"""
    if not st.session_state.get("gemini_configured", False):
        st.warning("AI 功能未啟用")
        return students_df

    df = students_df.copy()
    if "備註" not in df.columns:
        return df

    for idx, row in df.iterrows():
        remark = str(row.get("備註", "")).strip()
        if not remark or remark == "nan":
            continue

        prompt = f"""
        分析以下學生備註，判斷是否請假或有特殊固定值班：
        備註：{remark}

        只回傳純 JSON，不要任何其他文字：
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
            continue  # 單筆失敗不影響整體

    return df