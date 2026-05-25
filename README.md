# Sing Yin Study Prefect Duty Roster System

**版本**：v2.0  
**最後更新**：2026 年 5 月 25 日

一個專為 **Sing Yin Secondary School Study Prefect Team** 設計的智能值班排班管理平台。

---

## ✨ 主要功能

- ✅ **智能公平排班**：自動考慮歷史負荷、可用日子、老帶新（F.3 由 F.4/F.5 帶）、固定總值班
- ✅ **DeepSeek / Gemini AI 智能解析 Remarks**：自動理解中文備註並更新欄位
- ✅ **手動調整負荷**：可針對每次值班手動修改累計負荷點數
- ✅ **智慧替補推薦**：請假時自動推薦最適合人員
- ✅ **彩色 PDF 公告班表**（支援 GitHub 預設校徽 + 顯示開關）
- ✅ **Cloud 完整備份 / 還原**（解決 Streamlit Cloud 休眠重置問題）
- ✅ **每日聖經金句** + **一鍵刷新金句**功能
- ✅ **名冊即時編輯** + **多格式導出**（PDF、Excel、Markdown）
- ✅ **老帶新機制**：自動根據名冊年級判斷

---

## 📂 專案檔案結構
Study-Prefect-Duty-Roster-Generator/
├── app.py
├── config.py
├── core.py
├── utils.py
├── ui_components.py
├── data.py
├── ai_parser.py
├── requirements.txt
├── packages.txt
├── .streamlit/
│   └── secrets.toml          # ← 存放 API Key
├── logo.png                  # ← 校徽（放在根目錄）
├── README.md
└── .gitignore
text---

## 🚀 部署方式（Streamlit Cloud）

1. Fork 或 Clone 本專案到 GitHub
2. 前往 [Streamlit Cloud](https://share.streamlit.io/) 建立新 App
3. 填入 Repository URL 並部署
4. 在 **Advanced settings** 中設定 **Secrets**（見下方）

---

## 🔑 API 金鑰設定

在 `.streamlit/secrets.toml` 中加入以下內容：

```toml
# Gemini API（目前使用）
GEMINI_API_KEY = "AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 或者使用 Groq（可替換）
# GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

🖼️ 校徽設定

將校徽圖片重新命名為 logo.png
放到專案根目錄
部署後，側邊欄即可看到「🖼️ 顯示校徽」開關


📖 使用說明
詳細使用說明已在程式內建，請開啟網站後點擊「📖 查看完整使用說明書」。

📧 聯絡開發者
如有任何問題、建議或需要客製化功能，歡迎直接聯絡：
Email：s10777@syss.edu.hk

📄 License
本專案為 Sing Yin Secondary School Study Prefect Team 內部使用工具。

Made with ❤️ for Sing Yin Prefects
