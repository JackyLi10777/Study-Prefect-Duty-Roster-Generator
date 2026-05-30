# ai_parser.py
"""
聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
AI 智能解析模組 - Gemini 驅動的備註解析 + 任意格式名冊欄位智能映射

作者：Head Study Prefect 26-27 LI Chuangjie Jacky
版本：v2.3 Final（完整支援 Remarks 解析、AI 欄位映射、錯誤防護、Streamlit Cloud 相容）
"""

import streamlit as st
import pandas as pd
import google.generativeai as genai
import json

from config import GEMINI_MODEL

# ====================== Gemini 配置（Streamlit Cloud 相容） ======================
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel(GEMINI_MODEL)
    except Exception as e:
        model = None
        st.error(f"❌ Gemini 初始化失敗: {str(e)}")
else:
    model = None


# ====================== AI 系統提示 - Remarks 智能解析 ======================
REMARKS_SYSTEM_PROMPT = """
你是一位 Sing Yin Secondary School Study Prefect Team 的專業排班助理。
請根據「備註 (remarks)」欄位的中文內容，智能解析並更新以下欄位。
只輸出純 JSON，不要任何額外文字、解釋或 markdown。

可解析的欄位規則：
- "fixed_general_duty": 學年固定總值班 → MONDAY / TUESDAY / WEDNESDAY / THURSDAY / FRIDAY / NONE
- "available": 可用日子 → 用逗號分隔，例如 "MONDAY,WEDNESDAY,FRIDAY"
- "role": 職級 → "Study Prefect" 或 "Assistant Head Study Prefect"

如果備註中提到「老帶新」「新任」「F.3」「Assistant Head」「固定值班」「Room302 優先」「Room303 經驗豐富」「領導核心」等關鍵字，請合理判斷並更新。

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


def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    """
    使用 Gemini AI 解析 Remarks 欄位，並自動更新 fixed_general_duty、available、role
    支援進度條、單筆錯誤不中斷、嚴格錯誤處理
    """
    if model is None:
        st.error("❌ Gemini API 未設定，請在 .streamlit/secrets.toml 加入 GEMINI_API_KEY")
        return students_df

    if students_df.empty or "remarks" not in students_df.columns:
        st.warning("名冊為空或缺少 remarks 欄位，無法進行 AI 解析")
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

            # 更新欄位（安全更新）
            if "fixed_general_duty" in parsed and parsed["fixed_general_duty"]:
                updated_df.at[idx, "fixed_general_duty"] = str(parsed["fixed_general_duty"]).upper().strip()
            if "available" in parsed and parsed["available"]:
                updated_df.at[idx, "available"] = str(parsed["available"]).upper().strip()
            if "role" in parsed and parsed["role"]:
                updated_df.at[idx, "role"] = str(parsed["role"]).strip()

        except Exception as e:
            # 單筆失敗不中斷整體流程
            st.warning(f"第 {idx+1} 行 Remarks 解析失敗，已跳過（{str(e)[:80]}...）")

        progress_bar.progress((idx + 1) / total_rows)

    progress_bar.empty()
    st.success("✅ AI 已成功解析並更新所有 Remarks 欄位")
    return updated_df


# ====================== AI 系統提示 - 智能名冊欄位映射 ======================
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


def get_column_mapping_from_ai(df: pd.DataFrame) -> dict:
    """
    使用 Gemini 分析表格前幾行，自動產生欄位映射
    嚴格錯誤處理，支援 Streamlit Cloud
    """
    if model is None:
        raise Exception("Gemini API 未設定，請確認 secrets.toml")

    if df.empty or len(df.columns) < 2:
        raise Exception("上傳的檔案為空或欄位不足")

    sample_text = df.head(8).to_string(index=False)
    prompt = IMPORT_MAPPING_PROMPT.format(table_sample=sample_text)

    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip()

        # 清理 markdown
        if json_text.startswith("```json"):
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif json_text.startswith("```"):
            json_text = json_text.split("```")[1].strip()

        mapping = json.loads(json_text)
        return mapping
    except Exception as e:
        raise Exception(f"AI 欄位映射失敗: {str(e)[:100]}")


print("✅ ai_parser.py 已載入完成 - Gemini AI 解析引擎就緒")