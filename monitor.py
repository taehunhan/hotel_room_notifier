#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Room availability monitor for Agoda, Booking.com, and hotel official sites.
- Loads URLs from sites.json.
- Uses Playwright to render pages (dynamic JS).
- Parses page content to detect availability.
- Sends Telegram notifications on status change.
DISCLAIMER:
- Always review each site's Terms of Service and robots.txt. Automated scraping may be disallowed.
- Use reasonable intervals and avoid heavy traffic.
"""
import os
import json
import time
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import requests

STATE_FILE = os.environ.get("STATE_FILE", "state.json")
SITES_FILE = os.environ.get("SITES_FILE", "sites.json")
USER_AGENT = os.environ.get("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADLESS = os.environ.get("HEADLESS", "1") == "1"
WAIT_SEC = float(os.environ.get("WAIT_SEC", "20"))
NAV_TIMEOUT = int(float(os.environ.get("NAV_TIMEOUT", "45000")))
KO_PATTERNS_AVAILABLE = [
    # Patterns indicating rooms available (Korean/English)
    r"객실\s*선택", r"객실\s*남음", r"예약\s*가능", r"지금\s*예약",
    r"Select\s*room", r"Available", r"Book now", r"Rooms? available",
]
KO_PATTERNS_SOLDOUT = [
    r"매진", r"매진되었습니다", r"객실이\s*없습니다", r"품절", r"객실\s*없음",
    r"Sold\s*out", r"No rooms available", r"Fully booked"
]

def load_state() -> Dict[str, str]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state: Dict[str, str]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_telegram(msg: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("[WARN] Telegram not configured; skipping notification.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=30)
    try:
        resp.raise_for_status()
        print("[INFO] Telegram message sent.")
    except Exception as e:
        print("[ERROR] Telegram send failed:", e, resp.text[:2000])

def classify_content(text: str) -> str:
    # Basic heuristic: soldout beats available if both appear
    t = " ".join(text.split())
    available = any(re.search(p, t, flags=re.I) for p in KO_PATTERNS_AVAILABLE)
    soldout = any(re.search(p, t, flags=re.I) for p in KO_PATTERNS_SOLDOUT)
    if available and not soldout:
        return "available"
    if soldout and not available:
        return "soldout"
    # Fallback: presence of prices often implies availability
    price_like = re.search(r"(₩|KRW|NZD|\$)\s?\d{2,}", t)
    if price_like and not soldout:
        return "available"
    return "unknown"

def check_with_playwright(url: str) -> Tuple[str, str]:
    """
    Returns (status, evidence) where status in {"available","soldout","unknown"}.
    Evidence is a short snippet for logging.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ])
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="ko-KR",
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()
        page.set_default_timeout(NAV_TIMEOUT)
        try:
            page.goto(url, wait_until="domcontentloaded")
            # Give SPA time to load results, scroll a bit
            page.wait_for_timeout(int(WAIT_SEC * 1000))
            page.evaluate("""() => window.scrollTo(0, document.body.scrollHeight * 0.5)""")
            page.wait_for_timeout(2000)
            # Try to dismiss cookie banners / popups (best-effort)
            for sel in ["button:has-text('동의')", "button:has-text('확인')", "[data-testid='cookie-accept']"]:
                try:
                    page.locator(sel).first.click(timeout=1000)
                except Exception:
                    pass
            html = page.content()
            text = page.inner_text("body")
        except PlaywrightTimeoutError:
            browser.close()
            return "unknown", "timeout"
        except Exception as e:
            browser.close()
            return "unknown", f"error: {e}"
        finally:
            try:
                browser.close()
            except Exception:
                pass

    status = classify_content(text)
    evidence = ""

    # Try to extract first visible price chunk as evidence
    m = re.search(r"(₩|KRW|NZD|\$)\s?[\d,]{2,}", text)
    if m:
        evidence = f"price_hint={m.group(0)}"

    # Also detect Agoda/Booking specific hints
    if "agoda.com" in url:
        if "Agoda" not in evidence:
            evidence = (evidence + " ").strip() + "[Agoda]"
    if "booking.com" in url:
        evidence = (evidence + " ").strip() + "[Booking]"

    return status, evidence.strip()

def load_sites() -> List[Dict]:
    with open(SITES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "sites.json must be a JSON array"
    return data

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def main():
    load_dotenv()
    try:
        sites = load_sites()
    except Exception as e:
        print(f"[ERROR] Failed to load {SITES_FILE}: {e}")
        return

    state = load_state()
    new_state = dict(state)

    for site in sites:
        url = site.get("url")
        name = site.get("name", url)
        if not url:
            continue
        print(f"[INFO] Checking: {name} -> {url}")
        status, evidence = check_with_playwright(url)
        key = url
        prev = state.get(key, "unknown")
        new_state[key] = status
        print(f"[INFO] {name}: status={status} (prev={prev}) {evidence} time={now_iso()}")

        if status != prev and status in ("available", "soldout"):
            msg = f"🏨 <b>{name}</b>\n상태 변화: <b>{prev} ➜ {status}</b>\n{evidence}\n\n{url}"
            send_telegram(msg)

    save_state(new_state)
    print("[DONE]")

if __name__ == "__main__":
    main()
