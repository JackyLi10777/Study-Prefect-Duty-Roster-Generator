# Sing Yin Study Prefect Duty Roster Generator

**聖言中學導學風紀當值排班平台**  
Sing Yin Secondary School Study Prefect Team 專用值班表生成系統  
**v2.1 Final**｜簡約大氣・沉穩專業・完全相容 Streamlit Cloud

---

## ✨ 主要功能

- **AI 智能名冊導入**：支援任意格式的 Excel / CSV，AI 自動辨識並匹配欄位
- **智能公平排班**：根據歷史負荷、年級配對（老帶新）自動生成公平值班表
- **Assistant Head 限制**：只能排「Assist. in charge」，絕對不可排任何 Room
- **視覺公告版**：專業彩色顯示（不同崗位不同背景色），一目了然
- **彩色 PDF 匯出**：含校徽、角色背景色、每日聖經金句，適合列印公告
- **智慧替補推薦**：請假時自動推薦最低累計負荷的合格替補人員
- **全局負荷調節**：新增直觀滑桿，可快速調整整體負荷倍率（0.8～2.0）
- **手動精細調整**：可針對每個崗位個別修改本次負荷點數
- **Cloud 備份 / 還原**：完整 JSON 備份系統，徹底解決 Streamlit Cloud 休眠資料遺失問題
- **每日聖經金句**：每日自動更新，點擊即可刷新
- **完整歷史負荷監控**：即時統計 + Plotly 公平性柱狀圖

---

## 🚀 快速部署（Streamlit Cloud）

1. Fork 本專案到你的 GitHub 帳號
2. 前往 [Streamlit Cloud](https://share.streamlit.io/) 建立新 App
3. 連結你的 GitHub 倉庫
4. 確保專案根目錄包含以下檔案：
   - `app.py`
   - `requirements.txt`
   - `packages.txt`（必須包含 `weasyprint`）
5. 部署完成後即可使用

---

## 📁 檔案結構

- `app.py`　　　　　　　→ 主程式入口  
- `config.py`　　　　　　→ 常數、業務規則、顏色系統、金句  
- `data.py`　　　　　　　→ 示範名冊、格式範例、空表格  
- `ai_parser.py`　　　　　→ Gemini AI 智能導入與 Remarks 解析  
- `core.py`　　　　　　　→ 公平排班演算法、驗證、替補推薦  
- `utils.py`　　　　　　　→ PDF 生成、備份還原、匯出工具  
- `ui_components.py`　　　→ 側邊欄、每日金句、控制按鈕  

---

## 📧 聯絡方式

**Head Study Prefect 26-27**  
**LI Chuangjie Jacky**  
有任何問題、建議或需要客製化功能，請聯絡：  
**s10777@syss.edu.hk**

---

**Made with ❤️ for Sing Yin Secondary School Study Prefect Team**

---

**更新日期**：2026 年 5 月 30 日
