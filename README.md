# Sing Yin Secondary School Study Prefect Duty Roster

**Sing Yin Secondary School Study Prefect 值班排班系統**  
一套專為 Sing Yin Secondary School Study Prefect Team 設計的智能排班管理平台。

---

## ✨ 主要功能

- **智能公平排班**：自動考慮歷史負荷、可用日子、老帶新機制（F.3 由 F.4/F.5 帶）、固定總值班、職級限制
- **DeepSeek V4 AI 智能解析**：自動理解中文備註，智能更新固定值班、可用日子、職級
- **手動調整負荷**：可針對每個崗位本次值班手動修改累計負荷點數，即時更新最終總計
- **智慧替補推薦**：請假時自動推薦最合適替補人員（按總負荷由低到高排序）
- **彩色 PDF 公告班表**：支援校徽顯示，適合列印公告
- **多格式導出**：Excel、Markdown、PDF
- **Cloud 備份 / 還原**：解決 Streamlit Cloud 休眠重置問題
- **每日聖經金句** + 校徽顯示開關
- **完整使用說明書** + 直接反饋功能

---

## 📁 專案結構
Study-Prefect-Duty-Roster-Generator/
├── app.py                     # 主程式入口
├── ui_components.py           # 側邊欄與控制元件
├── core.py                    # 排班演算法與驗證
├── ai_parser.py               # DeepSeek V4 AI 解析
├── utils.py                   # PDF、備份、導入等工具
├── data.py                    # 示範資料與格式範例
├── config.py                  # 常數與設定
├── .streamlit/
│   └── secrets.toml           # API 金鑰（請勿上傳 GitHub）
├── requirements.txt
├── packages.txt               # WeasyPrint 系統依賴
├── logo.png                   # 預設校徽（請自行上傳）
└── README.md
text---

## 🚀 如何部署到 Streamlit Cloud

1. Fork 或 Clone 本專案到您的 GitHub
2. 在專案根目錄建立 `.streamlit/secrets.toml` 並加入以下內容：

```toml
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

確保根目錄有 logo.png（校徽）
在 Streamlit Cloud 建立新 App，連結您的 GitHub 倉庫即可自動部署


🔑 如何取得 DeepSeek API Key

前往 https://platform.deepseek.com/
使用 GitHub 或 Google 帳號登入
左側點擊 API Key → 建立新 Key
複製 Key 貼到 secrets.toml


📋 使用說明
詳細使用說明請在程式內點擊「📖 查看完整使用說明書」。
主要操作流程：

側邊欄載入或編輯名冊
點擊 AI 智能解析 Remarks（強烈建議）
主畫面設定特殊不開放時段 → 生成排班
使用 手動調整負荷 微調
導出 PDF / Excel / 備份


📧 聯絡與反饋
有任何問題、建議或需要客製化功能，請直接寄信給開發者：
Email： s10777@syss.edu.hk

感謝使用 Sing Yin Study Prefect Duty Roster！
祝 Study Prefect Team 服務順利、公平公正！

開發者：Jacky Li
版本：v1.4（2026.05.25）
技術：Streamlit + DeepSeek V4 + WeasyPrint + Pandas
