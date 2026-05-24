# 🦅 Sing Yin Secondary School Study Prefect Duty Roster System

**版本**：v1.3 模組化 + AI 智能解析版  
**最新更新**：2026 年 5 月 25 日  
**適用對象**：Study Prefect Team Advisor、Head Study Prefect、Assistant Head Study Prefect

這是一個專為 **Sing Yin Secondary School** 設計的 **Study Prefect 值班表生成平台**，完全符合學校男校 F.3–F.5 領袖生排班規則。

---

## ✨ 主要功能

- **智能公平排班演算法**：自動考慮歷史負荷、可用日子、職級、老帶新、固定總值班、連續值班限制
- **AI 智能解析 Remarks**：自動理解「固定週一」「可用三五」「隊長」「老帶新」等中文描述，自動更新欄位
- **每日聖經金句**：每天自動顯示一句鼓勵經文（50+ 句，可自行擴充）
- **彩色 PDF 公告版**：一鍵導出 A4 橫式彩色班表（含校徽）
- **多格式導出**：Excel、Markdown、JSON 完整備份
- **智慧替補推薦**：突發請假時即時推薦最優替補
- **雙軌編輯介面**：視覺公告版 + 互動式手動修改版
- **Cloud 備份還原**：解決 Streamlit Cloud 休眠重置問題
- **完全模組化架構**：易維護、易擴充

---

## 📁 專案檔案結構
study-prefect-duty-roster/
├── app.py                    # 主程式入口（唯一執行檔案）
├── config.py                 # 常數、每日金句、WEIGHTS
├── utils.py                  # PDF、備份、導入工具
├── data.py                   # 示範名冊、欄位映射
├── core.py                   # 排班演算法、驗證、替補
├── ui_components.py          # 所有 UI 元件（含 AI 按鈕）
├── ai_parser.py              # AI 智能解析 Remarks
├── requirements.txt          # Python 套件清單
├── packages.txt              # Streamlit Cloud 系統套件（PDF 用）
├── .streamlit/config.toml    # Streamlit 主題與伺服器設定
└── README.md                 # 本說明文件
text---

## 🚀 部署到 Streamlit Cloud（最簡單方式）

1. 把以上所有檔案上傳到 GitHub 倉庫
2. 進入 [Streamlit Cloud](https://share.streamlit.io) → New app
3. Repository 選你的倉庫
4. Branch 選 `main`
5. Main file path 填 `app.py`
6. 點擊 **Deploy**

**重要**：第一次部署可能需要 1–2 分鐘讓 Cloud 安裝 WeasyPrint 依賴，之後就會非常快。

---

## 🤖 如何使用 AI 智能解析 Remarks

1. 在側邊欄「👥 在線名冊即時維護」區塊
2. 填寫或修改任何同學的 **Remarks** 欄位（例如：「固定週一」「可用三五」「隊長」「老帶新」）
3. 點擊 **🚀 執行 AI 智能解析 Remarks** 按鈕
4. AI 會自動更新：
   - `fixed_general_duty`
   - `available`
   - `role`
   - 並在 remarks 加上標記

---

## 🔧 自訂設定

### 增加每日聖經金句
編輯 `config.py` 中的 `DAILY_VERSES` 字典即可（key 為星期 0–6）。

### 修改排班權重
在 `config.py` 的 `WEIGHTS` 字典調整即可。

### 新增 AI 解析規則
在 `ai_parser.py` 的 `ai_parse_remarks` 函數中新增關鍵字即可。

---

## 📬 技術支援

- **開發者**：LI CHuangjie, Jacky
- **版本控制**：本專案已完全模組化，方便未來維護
- **問題回報**：請在 GitHub Issues 提出

---

**感謝使用 Sing Yin Study Prefect Duty Roster System！**  
願每一位領袖生在服事中都經歷神的恩典與力量。

**「你們要先求他的國和他的義，這些東西都要加給你們了。」——馬太福音 6:33**
