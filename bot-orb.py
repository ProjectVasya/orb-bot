import requests
import time
from datetime import datetime
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ===== НАСТРОЙКИ =====
TOKEN = os.getenv("TOKEN_ORB")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "BTCUSDT"
TIMEFRAME_15M = "15"
TIMEFRAME_1M = "1"
CHECK_TIME = "16:45"
# =====================

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("❌ Ошибка: TOKEN или CHAT_ID не заданы")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_bybit_klines(symbol, interval, limit=2):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if data['retCode'] != 0:
            return None
        return data['result']['list']
    except:
        return None

def get_current_price(symbol):
    url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if data['retCode'] != 0:
            return None
        return float(data['result']['list'][0]['lastPrice'])
    except:
        return None

def wait_until_16_45():
    while True:
        now = datetime.now().strftime("%H:%M")
        if now == CHECK_TIME:
            break
        time.sleep(30)

def get_last_15m_candle():
    data = get_bybit_klines(SYMBOL, TIMEFRAME_15M, limit=2)
    if not data or len(data) < 2:
        return None, None
    candle = data[-2]
    high = float(candle[2])
    low = float(candle[3])
    return high, low

def monitor_breakout(high, low):
    first_touch = None
    send_telegram(f"📊 ORB активен. HIGH: {high}, LOW: {low}")

    while True:
        price = get_current_price(SYMBOL)
        if price is None:
            time.sleep(10)
            continue

        now = datetime.now().strftime("%H:%M")
        if now > "17:45":
            send_telegram("⏰ Время вышло. Сегодня сигналов нет.")
            break

        if first_touch is None:
            if price >= high:
                first_touch = "HIGH"
                send_telegram(f"🟡 Первое касание ВЕРХНЕГО уровня: {price}")
            elif price <= low:
                first_touch = "LOW"
                send_telegram(f"🟡 Первое касание НИЖНЕГО уровня: {price}")
            time.sleep(10)
            continue

        if first_touch == "HIGH" and price >= high:
            send_telegram(f"📈 СИГНАЛ: LONG\n🪙 {SYMBOL}\n📊 Уровень: {high}\n⏰ Время: {datetime.now().strftime('%H:%M')}")
            break

        if first_touch == "LOW" and price <= low:
            send_telegram(f"📉 СИГНАЛ: SHORT\n🪙 {SYMBOL}\n📊 Уровень: {low}\n⏰ Время: {datetime.now().strftime('%H:%M')}")
            break

        time.sleep(10)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_webserver():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

if __name__ == "__main__":
    Thread(target=run_webserver, daemon=True).start()
    send_telegram("✅ ORB Бот запущен! Жду 16:45 по МСК...")
    print("🤖 Бот запущен. Жду 16:45...")
    while True:
        wait_until_16_45()
        high, low = get_last_15m_candle()
        if high is None or low is None:
            send_telegram("❌ Не удалось получить свечу. Попробую позже.")
            time.sleep(60)
            continue
        monitor_breakout(high, low)
        print("⏳ Ожидание следующего дня...")
        time.sleep(60)