# ai_parser.py
import streamlit as st
import pandas as pd
import json
import time
from openai import OpenAI

# ==========================================
# Groq 配置（2026 年 5 月最新推薦）
# ==========================================
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ 未找到 GROQ_API_KEY，請在 .streamlit/secrets.toml 中新增 GROQ_API_KEY")
    client = None
else:
    client = OpenAI(
        api_key=st.secrets["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1"
    )

# 使用 Groq 最強免費高速模型
MODEL_NAME = "llama3-70b-8192"

SYSTEM_PROMPT = """
你是一位 Sing Yin Secondary School Study Prefect Team 的資深管理員。
請根據學生「備註 (Remarks)」欄位的中文內容，智能解析並輸出以下純 JSON 格式，不要任何額外文字：

{
  "fixed_general_duty": "MONDAY" 或 "TUESDAY" 或 "WEDNESDAY" 或 "THURSDAY" 或 "FRIDAY" 或 "NONE",
  "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY" （用逗號分隔，可用日子）,
  "role": "Study Prefect" 或 "Assistant Head Study Prefect",
  "remarks_processed": "處理後的備註摘要"
}

解析規則：
- 如果備註提到「固定週一總值班」、「每週一值班」→ fixed_general_duty = "MONDAY"
- 如果提到「固定週二」→ "TUESDAY"，以此類推
- 如果提到「隊長」、「Assistant Head」、「副隊長」→ role = "Assistant Head Study Prefect"
- 如果沒有提到固定值班 → "NONE"
- 可用日子請盡量完整推斷，沒有提到的日子預設全可用
- 只輸出純 JSON，不要任何說明或 markdown
"""

def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    if students_df.empty:
        st.warning("名冊為空，無法進行 AI 解析")
        return students_df

    if client is None:
        st.error("Groq API 未正確配置，請檢查 secrets.toml")
        return students_df

    df = students_df.copy()
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, row in df.iterrows():
        remarks = str(row.get("remarks", "")).strip()
        if not remarks or remarks.lower() in ["nan", "", "none"]:
            continue

        status_text.text(f"Groq AI 正在解析第 {idx+1} 位學生：{row.get('name', '未知')}")

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"學生備註：{remarks}\n請直接輸出 JSON："}
                ],
                temperature=0.3,
                max_tokens=800
            )

            json_text = response.choices[0].message.content.strip()

            # 清理可能的 markdown 包裹
            if json_text.startswith("```json"):
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif json_text.startswith("```"):
                json_text = json_text.split("```")[1].strip()

            parsed = json.loads(json_text)

            # 更新欄位
            if "fixed_general_duty" in parsed:
                df.at[idx, "fixed_general_duty"] = str(parsed["fixed_general_duty"]).upper()
            if "available" in parsed:
                df.at[idx, "available"] = str(parsed["available"]).upper()
            if "role" in parsed:
                df.at[idx, "role"] = str(parsed["role"])
            if "remarks_processed" in parsed:
                df.at[idx, "remarks"] = str(parsed["remarks_processed"])

        except Exception as e:
            st.warning(f"第 {idx+1} 位學生解析失敗: {str(e)}")
            time.sleep(0.3)

        progress_bar.progress((idx + 1) / len(df))

    progress_bar.empty()
    status_text.success("✅ Groq AI 解析完成！所有欄位已自動更新")
    return df
