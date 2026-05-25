# ai_parser.py
import streamlit as st
import pandas as pd
import openai
import json

def ai_parse_remarks(students_df: pd.DataFrame) -> pd.DataFrame:
    if students_df.empty:
        st.warning("名冊為空，無法進行 AI 解析")
        return students_df

    # === 從 Streamlit Secrets 讀取 API Key（推薦 Cloud 部署方式）===
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("❌ 請在 .streamlit/secrets.toml 中新增 OPENAI_API_KEY = \"您的金鑰\"")
        return students_df

    openai.api_key = st.secrets["OPENAI_API_KEY"]

    df = students_df.copy()

    for idx, row in df.iterrows():
        remarks = str(row.get('remarks', '')).strip()
        if not remarks or remarks.lower() in ["", "nan", "none", "無"]:
            continue

        prompt = f"""
你是 Sing Yin Secondary School Study Prefect 管理員。
請根據以下「備註」智能解析並更新三個欄位：

學生姓名: {row.get('name', '')}
年級: {row.get('form', '')}
備註: {remarks}

請嚴格以 JSON 格式回覆，不要有任何多餘文字：
{{
  "fixed_general_duty": "NONE" 或 "MONDAY" 或 "TUESDAY" 或 "WEDNESDAY" 或 "THURSDAY" 或 "FRIDAY",
  "available": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY" （逗號分隔，可用日子）,
  "role": "Study Prefect" 或 "Assistant Head Study Prefect"
}}
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            result = response.choices[0].message.content.strip()

            parsed = json.loads(result)

            # 更新欄位
            if "fixed_general_duty" in parsed:
                df.at[idx, "fixed_general_duty"] = str(parsed["fixed_general_duty"]).strip().upper()
            if "available" in parsed:
                df.at[idx, "available"] = str(parsed["available"]).strip().upper()
            if "role" in parsed:
                df.at[idx, "role"] = str(parsed["role"]).strip()

        except Exception as e:
            st.warning(f"AI 解析第 {idx+1} 位學生失敗: {str(e)}")
            continue

    st.success("✅ AI 已成功解析並更新所有 Remarks")
    return df
