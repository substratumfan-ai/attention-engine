import os
import time
import re
from supabase import create_client

# =============================
# 🔐 ENV VARIABLES (Railway)
# =============================
SUPABASE_URL = os.getenv("https://bvvzbtxeqpzqdwwjabws.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2dnpidHhlcXB6cWR3d2phYndzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjg2NjIsImV4cCI6MjA5Mjk0NDY2Mn0.ZsORzusxgxiLq59rE6n4EcPG13j1VGaTK7Mz0nRZJ6A")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================
# 🧠 KEYWORDS
# =============================
BULLISH_WORDS = [
    "bullish", "send", "breakout", "long", "buy",
    "accumulation", "moon", "pump", "strong", "gem"
]

BEARISH_WORDS = [
    "dump", "short", "sell", "exit", "rug",
    "scam", "weak", "dead"
]

# =============================
# 🧲 MOCK LIVE FEED (replace later with real API)
# =============================
def fetch_tweets():
    return [
        {
            "user": "CryptoAlpha",
            "followers": 120000,
            "text": "$SOL breakout looks strong. Sending soon 🚀",
            "likes": 120,
            "retweets": 30
        },
        {
            "user": "DeFiKing",
            "followers": 80000,
            "text": "$ETH looks weak, possible dump",
            "likes": 80,
            "retweets": 10
        }
    ]

# =============================
# 🪙 PARSE COINS
# =============================
def extract_coins(text):
    return re.findall(r"\$[A-Z]+", text)

# =============================
# 🧠 SENTIMENT
# =============================
def detect_sentiment(text):
    text_lower = text.lower()

    if any(word in text_lower for word in BULLISH_WORDS):
        return "bullish"
    if any(word in text_lower for word in BEARISH_WORDS):
        return "bearish"
    
    return "neutral"

# =============================
# 📊 PROCESS
# =============================
def process_tweets(raw_tweets):
    processed = []

    for tweet in raw_tweets:
        coins = extract_coins(tweet["text"])
        sentiment = detect_sentiment(tweet["text"])

        if not coins:
            continue

        processed.append({
            "user": tweet["user"],
            "followers": tweet["followers"],
            "coins": coins,
            "sentiment": sentiment,
            "engagement": tweet["likes"] + tweet["retweets"],
            "text": tweet["text"]
        })

    return processed

# =============================
# 💾 SAVE TO SUPABASE
# =============================
def save_to_supabase(data):
    if not data:
        return

    supabase.table("signals").insert(data).execute()

# =============================
# 🔁 MAIN LOOP
# =============================
def run_cycle():
    raw = fetch_tweets()
    processed = process_tweets(raw)

    save_to_supabase(processed)

    print(f"🚀 LIVE cycle completed | signals: {len(processed)}")

# =============================
# ▶️ RUN
# =============================
if __name__ == "__main__":
    while True:
        try:
            run_cycle()
        except Exception as e:
            print("❌ ERROR:", e)

        time.sleep(60)