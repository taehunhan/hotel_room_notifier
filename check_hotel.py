from playwright.sync_api import sync_playwright
import os
import requests
import time

URL = "https://www.edgewater.co.nz/book-edgewater-hotel-accommodation"
CHECKIN = "13/12/2025"   # DD/MM/YYYY
CHECKOUT = "14/12/2025"  # DD/MM/YYYY

def check_availability():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        # iBex 예약 iframe 안으로 들어가기
        frame = page.frame_locator("iframe[src*='ibex.net.nz']")

        # 날짜 입력
        frame.locator("input#checkInDate").fill(CHECKIN)
        frame.locator("input#checkOutDate").fill(CHECKOUT)

        # 검색 버튼 클릭
        frame.locator("button#checkAvailability").click()

        # 로딩 대기
        frame.locator("body").wait_for(timeout=10000)

        # 결과 HTML 가져오기
        content = frame.locator("body").inner_text()

        browser.close()

        print(content)

        # 예약 가능 여부 판정
        if "Sold Out" in content or "Fully Booked" in content:
            return False, "Sold Out"
        return True, "Available"

def send_telegram(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})

def debug_iframe():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)

        # iframe 나타날 때까지 기다림
        iframe_element = page.wait_for_selector("iframe[src*='ibex.net.nz']", timeout=60000)
        frame = iframe_element.content_frame()

        # iframe 안 HTML 덤프
        html = frame.content()
        print(html[:5000])  # 앞부분만 출력

        browser.close()

if __name__ == "__main__":
    # available, msg = check_availability()
    # if available:
    #     send_telegram(f"✅ Room available for {CHECKIN} → {CHECKOUT}!\n{URL}")
    # else:
    #     print(f"❌ Not available: {msg}")
    debug_iframe()