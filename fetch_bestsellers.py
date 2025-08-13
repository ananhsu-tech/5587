#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import time
import json
import random
import logging
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
CSV_PATH = os.path.join(DATA_DIR, "bestsellers.csv")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_rows_unique(rows):
    key_fields = ["date", "channel", "list_name", "rank"]
    existing = set()
    out_rows = []

    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                k = tuple(str(r[kf]) for kf in key_fields)
                existing.add(k)
                out_rows.append(r)

    for r in rows:
        k = tuple(str(r[kf]) for kf in key_fields)
        if k not in existing:
            out_rows.append(r)
            existing.add(k)

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date","channel","list_name","rank","title","author","isbn","url"
        ])
        writer.writeheader()
        writer.writerows(out_rows)

def request_html(session, url, cfg):
    headers = {"User-Agent": cfg.get("user_agent","BestsellerBot/1.0")}
    resp = session.get(url, headers=headers, timeout=cfg.get("request_timeout",15))
    resp.raise_for_status()
    return resp.text

def parse_books_com_tw_list(html, base_url, max_rank):
    # 通用解析（網站可能改版，請依實況調整）
    soup = BeautifulSoup(html, "html.parser")
    items = []
    selectors = [
        "ul#itemlist li",
        "div.mod_a li",
        "div.mod_b li",
        "li.item",
        "div.item"
    ]
    nodes = []
    for sel in selectors:
        nodes = soup.select(sel)
        if len(nodes) >= 10:
            break

    rank = 0
    for node in nodes:
        a = node.select_one("a[title]") or node.select_one("a[href]")
        title = (a.get("title") or a.get_text(strip=True)) if a else None
        href = a.get("href") if a else None
        if href:
            href = urljoin(base_url, href)
        author = None
        for sel in ["p.author", "div.author", "li.author", "span.author", "p>a[rel='goAuthor']"]:
            x = node.select_one(sel)
            if x:
                author = x.get_text(" ", strip=True)
                break
        if title:
            rank += 1
            items.append({"rank": rank, "title": title, "author": author, "isbn": None, "url": href})
        if rank >= max_rank:
            break
    return items

def parse_eslite_list(html, base_url, max_rank):
    # 通用解析（誠品常改版，請依實況調整）
    soup = BeautifulSoup(html, "html.parser")
    items = []
    selectors = [
        "div.product-item", "li.product-item", "li.ProductCard", "div.ProductCard",
        "ul.product-list li", "div.product-list li"
    ]
    nodes = []
    for sel in selectors:
        nodes = soup.select(sel)
        if len(nodes) >= 10:
            break

    rank = 0
    for node in nodes:
        a = node.select_one("a[href]")
        title = None
        if a:
            title = a.get("title") or a.get_text(" ", strip=True)
        href = a.get("href") if a else None
        if href and not href.startswith("http"):
            href = urljoin(base_url, href)

        author = None
        for sel in ["div.author", "p.author", "span.author"]:
            x = node.select_one(sel)
            if x:
                author = x.get_text(" ", strip=True)
                break

        if title:
            rank += 1
            items.append({"rank": rank, "title": title, "author": author, "isbn": None, "url": href})
        if rank >= max_rank:
            break
    return items

def main():
    cfg = load_config()
    rows_to_add = []
    today = date.today().isoformat()
    max_rank = int(cfg.get("max_rank", 20))
    delay_min = float(cfg.get("delay_seconds_min", 2.0))
    delay_max = float(cfg.get("delay_seconds_max", 4.0))

    session = requests.Session()

    for channel_key, ch in cfg.get("channels", {}).items():
        if not ch.get("enabled", True):
            continue
        lists = ch.get("lists", {})
        for list_name, url in lists.items():
            try:
                logging.info(f"Fetching {channel_key}:{list_name} -> {url}")
                html = request_html(session, url, cfg)
                if channel_key == "books_com_tw":
                    parsed = parse_books_com_tw_list(html, url, max_rank)
                elif channel_key == "eslite":
                    parsed = parse_eslite_list(html, url, max_rank)
                else:
                    parsed = []

                for item in parsed:
                    rows_to_add.append({
                        "date": today,
                        "channel": channel_key,
                        "list_name": list_name,
                        "rank": item["rank"],
                        "title": item["title"],
                        "author": item.get("author"),
                        "isbn": item.get("isbn"),
                        "url": item.get("url"),
                    })

                time.sleep(random.uniform(delay_min, delay_max))
            except Exception as e:
                logging.error(f"Error fetching {channel_key}:{list_name} -> {e}")

    if rows_to_add:
        save_rows_unique(rows_to_add)
        logging.info(f"Saved {len(rows_to_add)} rows into {CSV_PATH}")
        print("=== 今日上榜書單 ===")
        for r in rows_to_add:
            print(f"{r['channel']} | {r['list_name']} | {r['rank']:>2} | {r['title']}")
    else:
        logging.info("No rows parsed. Check selectors/URLs.")

if __name__ == "__main__":
    main()
