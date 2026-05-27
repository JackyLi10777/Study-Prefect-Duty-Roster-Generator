# Sing Yin Study Prefect Duty Roster System

**Sing Yin Secondary School Study Prefect Team 專用值班排班平台（v2.0 Final）**

![Version](https://img.shields.io/badge/Version-v2.0_Final-blue)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

### ✨ 主要功能（v2.0 Final）

- **🤖 AI 智能名冊導入**：支援**任意格式** Excel / CSV，自動匹配欄位，無需固定格式
- **嚴格角色限制**：
  - Assistant Head Study Prefect 只能排 **Assist. in charge**
  - 普通 Study Prefect 只能排 Room 202/302/303
- **同一天不可重複排班**：系統嚴格防止同一人同一天出現在多個崗位
- **公平排班演算法**：歷史負荷平衡 + 老帶新機制 + 避免連續值班 + 固定值班優先
- **彩色視覺公告版 + 彩色 PDF**：不同崗位使用不同顏色醒目顯示（金 / 綠 / 紅 / 藍）
- **手動調整本次負荷指數**：可即時修改每個崗位的點數（已修復清空錯誤）
- **智慧替補推薦系統**：依總點數由低到高推薦合適人選
- **每日聖經金句**：超過 200 句，專為 Head Study Prefect 設計（僕人領導、公平、公義、老帶新等主題）
- **完整使用說明書**：內建於網頁中（可展開）
- **Cloud 備份 / 還原系統**：解決 Streamlit Cloud 休眠重置問題
- **多格式匯出**：PDF（含校徽）、Excel、Markdown

---

### 📂 專案結構

```
Study-Prefect-Duty-Roster-Generator/
├── app.py                  # 主程式入口（含使用說明書）
├── core.py                 # 排班核心演算法（角色限制 + 同一天不可重複）
├── utils.py                # PDF 生成、備份還原、AI 智能導入
├── ui_components.py        # 側邊欄與 UI 元件
├── config.py               # 常數 + 大量聖經金句（Head Prefect 專用）
├── data.py                 # 示範資料與格式範例
├── ai_parser.py            # Remarks AI 解析
├── .streamlit/
│   └── secrets.toml        # Gemini API Key
├── requirements.txt
├── packages.txt
├── logo.png
└── README.md
```

---

### 🚀 快速部署（Streamlit Cloud）

1. Fork 本專案
2. 在 GitHub 根目錄放入 `logo.png`（校徽）
3. 建立 `.streamlit/secrets.toml` 並填入 Gemini API Key：
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key-here"
   ```
4. 在 Streamlit Cloud 連結倉庫並部署
5. 建議在 **Advanced settings** 設定 Python 3.12

---

### 📖 使用方式

1. **名冊導入**：推薦使用側邊欄的「🤖 AI 智能自動匹配」
2. **生成排班**：設定請假與特殊不開放時段後，點擊主畫面大按鈕
3. **微調**：可使用「手動修改版」或「手動調整負荷指數」
4. **匯出**：支援彩色 PDF（含校徽）、Excel、Markdown
5. **備份**：建議每次生成後下載 JSON 備份

詳細操作請參考網頁內建的「📖 使用說明書」（v2.0 Final）。

---

### 📬 聯絡與反饋

**Sing Yin Secondary School Study Prefect Team**  
如有任何問題、建議或功能需求，歡迎寄信至：**s10777@syss.edu.hk**

---

**Made with ❤️ for Sing Yin Secondary School Study Prefect Team**

最後更新：2026 年 5 月（v2.0 Final 穩定版）

---

### 更新重點

- 標題與版本更新為 **v2.0 Final**
- 新增「嚴格角色限制」與「同一天不可重複排班」說明
- 強調彩色 PDF 與超過 200 句聖經金句
- 簡化部署說明
- 加入內建使用說明書的提醒