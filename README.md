# Sing Yin Study Prefect Duty Roster Generator

**Sing Yin Secondary School Study Prefect Team 專用值班表生成系統**  
v2.3 (Legacy & Deep Space Integrated - Final)  
NASA Deep Space 沉穩專業風格｜完整彩色 PDF｜AI 智能導入｜公平排班

---

## ✨ 主要功能

- **AI 智能名冊導入**：支援任意格式的 Excel/CSV，自動匹配欄位
- **智能公平排班**：根據歷史負荷自動調整，Assistant Head 只能排 Assist. in charge
- **視覺公告版**：沉穩 NASA 風格彩色表格（網頁即時顯示）
- **彩色 PDF 匯出**：含校徽、背景填充、專業列印優化
- **智慧替補推薦**：請假時自動推薦最低負荷替補
- **Cloud 備份/還原**：解決 Streamlit Cloud 休眠問題
- **每日聖經金句**：每日自動更新靈修提醒
- **完整手動調整**：即時編輯排班表與負荷指數

---

## 🚀 快速部署（Streamlit Cloud）

1. Fork 本專案
2. 在 Streamlit Cloud 建立新 App，連結你的 GitHub 倉庫
3. 確保專案根目錄有以下檔案：
   - `app.py`
   - `requirements.txt`
   - `packages.txt`
   - `.streamlit/config.toml`（可選）
4. 部署完成後即可使用

---

## 📁 檔案結構

- `app.py` - 主程式入口
- `config.py` - 常數、顏色系統、金句
- `data.py` - 示範資料與格式範例
- `ai_parser.py` - Gemini AI 智能導入與備註解析
- `core.py` - 排班演算法、驗證、替補推薦
- `utils.py` - PDF 生成、備份還原、匯出工具
- `ui_components.py` - 側邊欄、按鈕、金句顯示
- `requirements.txt` - Python 依賴
- `packages.txt` - WeasyPrint 系統依賴

---

## 📧 聯絡方式

有任何問題或需要客製化功能，請聯絡 email：  
**s10777@syss.edu.hk**

---

**Made with ❤️ for Sing Yin Secondary School Study Prefect Team**