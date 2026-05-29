# Sing Yin Secondary School Study Prefect Duty Roster Platform  
**聖言中學導學風紀當值排班平台**

**專為聖言中學 Study Prefect Team 打造的專業、公平、穩定排班管理系統**

**版本**：v2.3 Final  
**作者**：Head Study Prefect 26-27 LI Chuangjie Jacky  
**部署平台**：Streamlit Cloud（已徹底解決休眠資料遺失問題）

---

## ✨ 主要功能

- **AI 智能名冊導入**：支援任意格式 Excel / CSV，Gemini AI 自動匹配欄位與解析備註
- **公平排班演算法**：歷史負荷 + 全局負荷倍率滑桿（0.5~2.5×）+ F.3 老帶新優先
- **嚴格遵守校規**：
  - Assistant Head Study Prefect 只能排 "Assist. in charge"
  - Room 302（每日 1 人）、Room 303（每日 2 人）、Room 202（每日 2 人）
  - Room 202 星期二、四常規不開放顯示 ⬜
  - 每人每日僅能值班一次
- **全局負荷調節滑桿**：主畫面即時調整倍率，考試週可提高負荷讓累計較低同學快速平衡
- **智慧替補推薦**：請假時自動推薦最低累計負荷學生
- **完整視覺公告版**：角色背景色區分（Assist 金米、302 綠、303 黃、202 紅）
- **專業 PDF 匯出**：含校徽、彩色表格、每日聖經金句，適合列印公告
- **多格式下載**：PDF、Excel、Markdown
- **雲端備份 / 還原**：完整 JSON 備份，徹底解決 Streamlit Cloud 休眠資料遺失
- **每日聖經金句**：自動隨機顯示 + 莊重神聖區塊
- **即時統計與公平監控**：側邊欄 + Plotly 柱狀圖
- **響應式介面**：電腦與行動裝置皆友好

---

## 🚀 快速部署（Streamlit Cloud）

1. Fork 本專案至你的 GitHub
2. 前往 [Streamlit Cloud](https://share.streamlit.io) 建立新 App
3. 連結你的 GitHub 倉庫
4. 確保專案根目錄包含以下檔案：
   - `app.py`
   - `requirements.txt`
   - `packages.txt`
   - `.streamlit/config.toml`（可選）
5. 部署完成後即可使用

---

## 📁 檔案結構
study-prefect-duty-roster-generator/
├── app.py                    # 主程式入口
├── config.py                 # 常數、顏色、每日金句、校規設定
├── data.py                   # 示範資料、初始化
├── ai_parser.py              # Gemini AI 智能匯入與備註解析
├── core.py                   # 排班核心演算法、公平性審計
├── utils.py                  # PDF 生成、備份還原、多格式匯出
├── ui_components.py          # 所有 UI 元件（彩色表格、滑桿、替補面板）
├── requirements.txt
├── packages.txt              # WeasyPrint 系統依賴
├── .streamlit/config.toml    # Streamlit Cloud 設定
└── README.md
text---

## 📧 聯絡方式

有任何問題、客製化需求或 Bug 回報，請聯絡：  
**s10777@syss.edu.hk**  
（Head Study Prefect 26-27 LI Chuangjie Jacky）

---

**Made with ❤️ for Sing Yin Secondary School Study Prefect Team**
