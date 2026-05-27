# ai_parser.py
import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from config import GEMINI_MODEL

# ==========================================
# Gemini AI 智能欄位映射引擎（舊版核心功能完整保留）
# ==========================================
def get_column_mapping_from_ai(df: pd.DataFrame) -> dict:
    """
    使用 Gemini AI 智能辨識使用者上傳的任意格式 Excel/CSV，
    自動對應到系統標準欄位名稱。
    補回舊版本所有 AI 映射功能。
    """
    if df.empty or len(df.columns) < 2:
        return {}

    # 準備給 AI 的樣本資料（取前 3 列作為範例）
    sample = df.head(3).to_dict(orient="records")
    sample_text = json.dumps(sample, ensure_ascii=False, indent=2)

    prompt = f"""
你是一位專業的 Excel 資料清理專家。
以下是一個 DataFrame 的前 3 列資料（JSON 格式）：

{sample_text}

請幫我把欄位名稱對應到以下標準欄位（只輸出 JSON，不要其他文字）：
{{
  "姓名": "name",
  "年級": "form",
  "班別": "class",
  "職級": "role",
  "學年固定總值班": "fixed_general_duty",
  "可用日子": "available",
  "歷史累計(次)": "history_duties",
  "歷史動態(點)": "history_weight",
  "備註": "remarks"
}}

如果某個欄位無法對應，請填 null。
只輸出純 JSON 物件，不要任何解釋。
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        mapping_text = response.text.strip()

        # 清理可能的多餘 markdown 標記
        if mapping_text.startswith("```json"):
            mapping_text = mapping_text.split("```json")[1].split("```")[0].strip()
        elif mapping_text.startswith("```"):
            mapping_text = mapping_text.split("```")[1].strip()

        mapping = json.loads(mapping_text)
        return mapping

    except Exception as e:
        st.warning(f"⚠️ AI 欄位映射失敗，使用傳統映射方式。錯誤: {str(e)}")
        # 回傳一個基礎映射作為降級方案
        return {
            "姓名": "name",
            "name": "name",
            "年級": "form",
            "form": "form",
            "班別": "class",
            "class": "class",
            "職級": "role",
            "role": "role",
            "備註": "remarks",
            "remarks": "remarks"
        }

# ==========================================
# AI 智能解析備註欄（舊版核心功能完整保留）
# ==========================================
def ai_parse_remarks(remarks: str) -> dict:
    """
    使用 Gemini AI 智能解析「備註」欄位的文字，
    自動判斷請假、特殊限制、優先級等。
    這是舊版本中極重要的功能，已完整補回。
    """
    if not remarks or str(remarks).strip() == "":
        return {"action": "none", "reason": ""}

    prompt = f"""
你是一位學校領袖生排班管理員。
請解析以下備註文字，並以 JSON 格式回傳（只輸出 JSON，不要其他文字）：

備註：{remarks}

可能的判斷結果：
- "action": "leave" （請假）
- "action": "restricted_days" （限制某些日子）
- "action": "priority" （優先排班）
- "action": "none" （無特殊處理）

同時回傳 "reason" 說明原因。
只輸出純 JSON，例如：{{"action": "leave", "reason": "生病請假一週"}}
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # 清理 markdown
        if result_text.startswith("```json"):
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif result_text.startswith("```"):
            result_text = result_text.split("```")[1].strip()

        result = json.loads(result_text)
        return result

    except Exception:
        # 降級處理：當 AI 失敗時回傳安全預設值
        return {"action": "none", "reason": "AI 解析失敗，使用手動處理"}

# ==========================================
# 公開的 AI 輔助函數（供 utils.py 呼叫）
# ==========================================
def smart_ai_column_mapping(df: pd.DataFrame) -> dict:
    """
    公開介面：供 utils.py 中的 smart_process_roster_import 呼叫。
    這是舊版本中 AI 導入流程的核心橋接函數。
    """
    return get_column_mapping_from_ai(df)