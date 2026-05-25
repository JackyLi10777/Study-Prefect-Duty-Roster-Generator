# ai_parser.py
import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re

# ==========================================
# Gemini 配置（與 utils.py 共用）
# ==========================================
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
else:
    model = None

# ==========================================
# AI 系統提示（精準解析 Remarks）
# ==========================================
SYSTEM_PROMPT = """
你是一位 Sing Yin Secondary School Study Prefect Team 的專業排班助理。
請根據「備註 (remarks)」欄位的中文內容，智能解析並更新以下欄位。
只輸出純 JSON，不要任何額外文字、解釋或 markdown。

可解析的欄位規則：
- "fixed_general_duty": 學年固定總值班 → MONDAY / TUESDAY / WEDNESDAY / THURSDAY / FRIDAY / NONE
- "available": 可用日子 → 用逗號分隔，例如 "MONDAY,WEDNESDAY,FRIDAY"
- "role": 職級 → "Study Prefect" 或 "Assistant Head Study Prefect"

如果備註中提到「老帶新」「新任」「F.3」「Assistant Head」「固定值班」「Room302 優先」「Room303 經驗豐富」等關鍵字，請合理判斷並更新。

範例輸入：
remarks: "老帶新，F.3 優先，固定星期三值班"

正確輸出 JSON：
{
  "fixed_general_duty": "WEDNESDAY",
  "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
  "role": "Study Prefect"
}

請嚴格遵守，只輸出 JSON。
"""

def ai_parse_remarks(students_df):
    """AI 解析 Remarks 欄位並更新名冊"""
    if model is None:
        st.error("❌ Gemini API 未設定，請在 .streamlit/secrets.toml 加入 GEMINI_API_KEY")
        return students_df

    if students_df.empty:
        st.warning("名冊為空，無法進行 AI 解析")
        return students_df

    updated_df = students_df.copy()

    progress_bar = st.progress(0)
    total_rows = len(students_df)

    for idx, row in students_df.iterrows():
        remarks = str(row.get("remarks", "")).strip()
        if not remarks or remarks.lower() == "nan" or remarks == "":
            progress_bar.progress((idx + 1) / total_rows)
            continue

        try:
            prompt = f"{SYSTEM_PROMPT}\n\n備註內容：{remarks}"
            response = model.generate_content(prompt)
            json_text = response.text.strip()

            # 清理可能的 markdown
            if json_text.startswith("```json"):
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif json_text.startswith("```"):
                json_text = json_text.split("```")[1].strip()

            parsed = json.loads(json_text)

            # 更新欄位
            if "fixed_general_duty" in parsed and parsed["fixed_general_duty"]:
                updated_df.at[idx, "fixed_general_duty"] = str(parsed["fixed_general_duty"]).upper()
            if "available" in parsed and parsed["available"]:
                updated_df.at[idx, "available"] = str(parsed["available"]).upper()
            if "role" in parsed and parsed["role"]:
                updated_df.at[idx, "role"] = str(parsed["role"])

        except Exception:
            # 單筆失敗不中斷整體流程
            pass

        progress_bar.progress((idx + 1) / total_rows)

    progress_bar.empty()
    st.success("✅ AI 已成功解析並更新所有 Remarks 欄位")
    return updated_df