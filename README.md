# Sing Yin Study Prefect Duty Roster System

**Sing Yin Secondary School Study Prefect Team 專用值班排班平台**

![Version](https://img.shields.io/badge/Version-v2.0-blue)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

### ✨ 最新功能（v2.0）

- **🤖 AI 智能名冊導入**：支援**任意格式**的 Excel / CSV，無需固定欄位名稱，AI 自動匹配姓名、年級、職級、可用日子等
- **每日聖經金句**（可刷新）
- **公平排班演算法**（老帶新機制 + 固定值班 + 避免連續值班 + 歷史負荷平衡）
- **手動調整本次值班負荷指數**
- **智慧替補推薦系統**
- **一鍵清空本週排班** + 確認機制
- **彩色 PDF 公告班表**（含校徽）
- **Excel + Markdown 多格式導出**
- **Cloud 備份 / 還原系統**（解決 Streamlit Cloud 休眠問題）
- **名冊即時修改**（data_editor）
- **完整驗證系統**（姓名錯誤、重複、請假衝突、空缺提示）

---

### 📂 專案結構

```
Study-Prefect-Duty-Roster-Generator/
├── app.py                  # 主程式入口
├── config.py               # 常數與金句
├── core.py                 # 排班演算法核心
├── utils.py                # PDF、備份、AI智能導入
├── ui_components.py        # 側邊欄與 UI 元件
├── data.py                 # 示範資料
├── ai_parser.py            # Remarks AI 解析
├── .streamlit/
│   └── secrets.toml        # Gemini API 金鑰
├── requirements.txt
├── packages.txt
├── logo.png                # 校徽（放在根目錄）
└── README.md
```

---

### 🚀 快速部署（Streamlit Cloud）

1. Fork 此專案
2. 在 GitHub 根目錄新增 `logo.png`（校徽）
3. 建立 `.streamlit/secrets.toml`：
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key-here"
   ```
4. 在 Streamlit Cloud 連結您的 GitHub 儲存庫
5. 在 **Advanced settings** 中設定：
   - Python version: **3.12**
   - requirements.txt
   - packages.txt（內含 weasyprint 相關套件）

---

### 📋 使用說明

#### 1. 名冊導入（最推薦使用 AI 智能導入）
- 上傳您的 Prefect 名冊（Excel / CSV）
- 點擊 **「🤖 AI 智能自動匹配」**（支援任意欄位名稱）
- 或使用傳統「📋 傳統格式導入」

#### 2. 每日金句
- 主畫面會顯示每日聖經金句
- 可點擊「🔄 刷新金句」隨時更換

#### 3. 生成值班表
- 在側邊欄設定請假人員與特殊不開放時段
- 點擊主畫面「🚀 智能計算：生成本週全新公平值班表」

#### 4. 手動調整
- 可在「🔧 手動調整本次值班負荷指數」直接修改每個崗位的點數
- 系統會即時更新累計負荷與公平性圖表

#### 5. 匯出
- **PDF**：公告用彩色班表（含校徽）
- **Excel**：完整值班表 + 工作負荷統計
- **Markdown**：方便複製到文件

---

### 🔑 API 金鑰設定

- **Gemini API Key**（必填）：用於 AI 智能名冊導入與 Remarks 解析
- 取得方式：前往 [Google AI Studio](https://aistudio.google.com/app/apikey) 建立免費 API Key

---

### 📸 主要功能截圖

（請自行上傳截圖到 GitHub）

- 主畫面（集中常用功能）
- AI 智能名冊導入
- 值班表視覺版 + 手動修改版
- 累計工作負荷公平性監控圖表

---

### 📬 聯絡與反饋

**advisor / Head Study Prefect / Assistant Head Study Prefect**  
如有任何問題或功能建議，請寄信至：**s10777@syss.edu.hk**

---

**Made with ❤️ for Sing Yin Secondary School Study Prefect Team**

最後更新：2026 年 5 月