# 博客來 × 誠品｜暢銷榜搜尋與趨勢圖（Flask 版）

功能：
- 每日擷取「藝術設計」「人文社科」兩大類（可自行換成實際分類 URL）
- 書名搜尋：顯示是否上榜、哪個榜單與名次
- 趨勢圖：近 90 天／180 天 名次折線圖
- 通路與分類篩選：博客來 / 誠品 / 全部

## 安裝（本地開發）
```bash
python3 -m venv venv
source venv/bin/activate  # Windows 用 venv\Scripts\activate
pip install -r requirements.txt
```

## 擷取資料
```bash
python fetch_bestsellers.py
```
> 第一次執行會建立 `data/bestsellers.csv`。重跑同一天資料會自動去重。

## 啟動網站
```bash
python app.py
# 瀏覽器打開 http://localhost:5000
```

## 部署到 Render（建議）
1) 把整個專案上傳到 GitHub  
2) 在 Render 建立 **Web Service**：  
   - Start Command：`gunicorn app:app`  
3) 建立 **Cron Job**（每天更新資料）：  
   - Command：`python fetch_bestsellers.py`

## 調整分類網址
- 打開 `config.json`，把預設的列表 URL 改成真正的「藝術設計 / 人文社科」暢銷榜頁面。
- 網站常改版，若解析失敗請微調 `fetch_bestsellers.py` 內的 CSS selector。

## 注意
- 請遵守各站使用條款與 robots.txt，維持低頻爬取。
