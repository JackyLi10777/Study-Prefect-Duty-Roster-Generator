# ai_parser.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
AI 智能解析模組 - Remarks 自動解析 + 智能名冊欄位映射

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（已完整整合最新 ROOMS_CONFIG 與業務規則）
"""

import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re

from config import GEMINI_MODEL, ROOMS_CONFIG

# ====================== Gemini 配置 ======================
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(GEMINI_MODEL)
else:
    model = None
    st.warning("⚠️ Gemini API 未設定，AI 功能將無法使用")

# ====================== AI 系統提示 - Remarks 智能解析 ======================
REMARKS_SYSTEM_PROMPT = """
你是一位 Sing Yin Secondary School Study Prefect Team 的專業排班助理。
請根據「備註 (remarks)」欄位的中文內容，智能解析並更新以下欄位。
只輸出純 JSON，不要任何額外文字、解釋或 markdown。

可解析的欄位規則：
- "fixed_general_duty": 學年固定總值班 → MONDAY / TUESDAY / WEDNESDAY / THURSDAY / FRIDAY / NONE
- "available": 可用日子 → 用逗號分隔，例如 "MONDAY,WEDNESDAY,FRIDAY"
- "role": 職級 → "Study Prefect" 或 "Assistant Head Study Prefect"

如果備註中提到「老帶新」「新任」「F.3」「Assistant Head」「固定值班」「Room302 優先」「Room303 經驗豐富」「領導核心」「老帶新」等關鍵字，請合理判斷並更新。

範例輸入：
remarks: "老帶新，F.3 優先，固定星期三值班，領導核心"

正確輸出 JSON：
{
  "fixed_general_duty": "WEDNESDAY",
  "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
  "role": "Assistant Head Study Prefect"
}

請嚴格遵守，只輸出 JSON。
"""

# ====================== AI 系統提示 - 智能名冊導入欄位映射 ======================
IMPORT_MAPPING_PROMPT = """
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
{table_sample}

請輸出以下格式的 JSON：
{
  "name": "實際欄位名稱",
  "form": "實際欄位名稱",
  ...
}
"""

# ====================== 核心函數 ======================
def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    """
    使用 Gemini AI 解析 Remarks 欄位，並自動更新 fixed_general_duty、available、role
    """
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
        if not remarks or remarks.lower() in ["nan", "", "none"]:
            progress_bar.progress((idx + 1) / total_rows)
            continue

        try:
            prompt = f"{REMARKS_SYSTEM_PROMPT}\n\n備註內容：{remarks}"
            response = model.generate_content(prompt)
            json_text = response.text.strip()

            # 清理可能的 markdown 包裝
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

        except Exception as e:
            # 單筆失敗不中斷整體流程
            st.warning(f"第 {idx+1} 筆 Remarks 解析失敗: {str(e)}")
            pass

        progress_bar.progress((idx + 1) / total_rows)

    progress_bar.empty()
    st.success("✅ AI 已成功解析並更新 Remarks 欄位")
    return updated_df


def get_column_mapping_from_ai(df: pd.DataFrame) -> dict:
    """
    使用 Gemini 分析表格前幾行，自動產生欄位映射
    """
    if model is None:
        raise Exception("Gemini API 未設定")

    sample_text = df.head(8).to_string(index=False)
    prompt = IMPORT_MAPPING_PROMPT.format(table_sample=sample_text)

    response = model.generate_content(prompt)
    json_text = response.text.strip()

    # 清理 markdown
    if json_text.startswith("```json"):
        json_text = json_text.split("```json")[1].split("```")[0].strip()
    elif json_text.startswith("```"):
        json_text = json_text.split("```")[1].strip()

    return json.loads(json_text)


print("✅ ai_parser.py 已載入完成 - AI 智能解析模組就緒")
