#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import os
from datetime import datetime, timedelta

import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, send_file, abort

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "bestsellers.csv")

app = Flask(__name__)

def load_df():
    if not os.path.exists(CSV_PATH):
        # 建立空檔提醒
        os.makedirs(DATA_DIR, exist_ok=True)
        return pd.DataFrame(columns=["date","channel","list_name","rank","title","author","isbn","url"])
    df = pd.read_csv(CSV_PATH, dtype=str)
    if df.empty:
        return df
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date","rank","title"])
    return df

@app.route("/", methods=["GET"])
def index():
    q = request.args.get("q", "", type=str).strip()
    channel = request.args.get("channel", "all")
    cat = request.args.get("cat", "all")  # art_design / humanities / all
    exact = request.args.get("exact", "0") == "1"

    df = load_df()
    results = []
    status = None

    if q:
        m = df["title"].astype(str).str.strip()
        m = (m == q) if exact else m.str.contains(q, case=False, na=False)
        if channel in ["books_com_tw","eslite"]:
            m &= (df["channel"] == channel)
        if cat in ["art_design","humanities"]:
            m &= (df["list_name"] == cat)

        sub = df[m].copy()
        if not sub.empty:
            # 是否上榜（看最近一天）
            latest_date = sub["date"].max()
            today_slice = sub[sub["date"] == latest_date]
            on_chart = not today_slice.empty
            best_rank_today = int(today_slice["rank"].min()) if on_chart else None
            status = {
                "on_chart": on_chart,
                "latest_date": latest_date.date().isoformat(),
                "best_rank_today": best_rank_today
            }

            # 羅列所有命中紀錄（日期、通路、分類、名次、標題）
            sub = sub.sort_values(["date","rank"])
            for _, r in sub.iterrows():
                results.append({
                    "date": r["date"].date().isoformat(),
                    "channel": r["channel"],
                    "list_name": r["list_name"],
                    "rank": int(r["rank"]),
                    "title": r["title"],
                    "url": r.get("url", None)
                })

    return render_template("index.html",
                           query=q,
                           channel=channel,
                           cat=cat,
                           exact="1" if exact else "0",
                           status=status,
                           results=results)

def _plot_bytes(df, title_query, days, channel=None, cat=None, exact=False):
    if df.empty:
        return None
    m = df["title"].astype(str).str.strip()
    m = (m == title_query) if exact else m.str.contains(title_query, case=False, na=False)
    if channel in ["books_com_tw","eslite"]:
        m &= (df["channel"] == channel)
    if cat in ["art_design","humanities"]:
        m &= (df["list_name"] == cat)

    cutoff = pd.Timestamp(datetime.utcnow().date() - timedelta(days=days))
    m &= (df["date"] >= cutoff)

    sub = df[m].copy()
    if sub.empty:
        return None

    # 同日取最前名次
    sub = sub.sort_values(["date","rank"]).groupby("date", as_index=False).first()

    fig = plt.figure()
    plt.plot(sub["date"], sub["rank"], marker="o")
    plt.gca().invert_yaxis()
    plt.xlabel("日期")
    plt.ylabel("名次（越上面越好）")
    plt.title(f"《{title_query}》近 {days} 天趨勢")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf

@app.route("/chart.png")
def chart():
    q = request.args.get("q", "", type=str).strip()
    if not q:
        abort(400)
    days = int(request.args.get("days", "90"))
    channel = request.args.get("channel", "all")
    cat = request.args.get("cat", "all")
    exact = request.args.get("exact", "0") == "1"

    df = load_df()
    buf = _plot_bytes(df, q, days, None if channel=="all" else channel,
                      None if cat=="all" else cat, exact=exact)
    if buf is None:
        abort(404)
    return send_file(buf, mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
