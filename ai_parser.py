# ai_parser.py
import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import time

# ==========================================
# Gemini 配置（Streamlit Cloud 相容）
# ==========================================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 未找到 GEMINI_API_KEY，請在 .streamlit/secrets.toml 中新增 GEMINI_API_KEY = '您的金鑰'")
    genai.configure(api_key=None)
else:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    }
)

SYSTEM_PROMPT = """
你是一位 Sing Yin Secondary School Study Prefect Team 的資深管理員。
請根據學生「備註 (Remarks)」欄位的中文內容，智能解析並輸出以下 JSON 格式：

{
  "fixed_general_duty": "MONDAY" 或 "TUESDAY" 或 "WEDNESDAY" 或 "THURSDAY" 或 "FRIDAY" 或 "NONE",
  "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY" （用逗號分隔，可用日子）,
  "role": "Study Prefect" 或 "Assistant Head Study Prefect",
  "remarks_processed": "處理後的備註摘要"
}

規則：
- 如果備註提到「固定週一總值班」、「每週一值班」→ fixed_general_duty = "MONDAY"
- 如果提到「隊長」、「Assistant Head」→ role = "Assistant Head Study Prefect"
- 如果提到「F.3」且需要「老帶新」→ 優先讓 F.4/F.5 帶他
- 可用日子請盡量完整推斷，沒有提到的日子預設全可用
- 只輸出純 JSON，不要任何額外文字
"""

def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    if students_df.empty:
        st.warning("名冊為空，無法進行 AI 解析")
        return students_df

    df = students_df.copy()
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, row in df.iterrows():
        remarks = str(row.get("remarks", "")).strip()
        if not remarks or remarks.lower() == "nan" or remarks == "":
            continue

        status_text.text(f"AI 正在解析第 {idx+1} 位學生：{row.get('name', '未知')}")

        try:
            response = model.generate_content(
                f"{SYSTEM_PROMPT}\n\n學生備註：{remarks}\n\n請直接輸出 JSON："
            )
            json_text = response.text.strip()
            
            # 清理可能的 markdown 包裹
            if json_text.startswith("```json"):
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif json_text.startswith("```"):
                json_text = json_text.split("```")[1].strip()

            parsed = json.loads(json_text)

            # 更新欄位
            if "fixed_general_duty" in parsed:
                df.at[idx, "fixed_general_duty"] = parsed["fixed_general_duty"]
            if "available" in parsed:
                df.at[idx, "available"] = parsed["available"]
            if "role" in parsed:
                df.at[idx, "role"] = parsed["role"]
            if "remarks_processed" in parsed:
                df.at[idx, "remarks"] = parsed["remarks_processed"]

        except Exception as e:
            st.warning(f"第 {idx+1} 位學生解析失敗: {str(e)}")
            time.sleep(0.5)

        progress_bar.progress((idx + 1) / len(df))

    progress_bar.empty()
    status_text.success("✅ AI Gemini 解析完成！所有欄位已自動更新")
    return df
