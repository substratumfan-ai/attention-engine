import os
import time
import requests
from datetime import datetime, timedelta
from supabase import create_client

# =========================
# ENV VARIABLES
# =========================

SUPABASE_URL = os.getenv("https://bvvzbtxeqpzqdwwjabws.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2dnpidHhlcXB6cWR3d2phYndzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjg2NjIsImV4cCI6MjA5Mjk0NDY2Mn0.ZsORzusxgxiLq59rE6n4EcPG13j1VGaTK7Mz0nRZJ6A")
TWITTER_API_KEY = os.getenv("new1_810cb3d65f14407b8108a542758105db")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase env variables")

if not TWITTER_API_KEY:
    print("⚠️ TWITTER_API_KEY missing — no real data")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# CONFIG
# =========================

TOKENS = ["BTC", "ETH", "SOL", "RAVE", "SEEK", "BONK"]
SEARCH_LIMIT = 20

# =========================
# FETCH REAL TWEETS
# =========================

def fetch_tweets(token):
    url = "https://api.twitterapi.io/twitter/tweet/advanced_search"

    headers = {
        "X-API-Key": TWITTER_API_KEY
    }

    query = f"${token} OR {token}"

    params = {
        "query": query,
        "limit": SEARCH_LIMIT
    }

    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()

        tweets = data.get("tweets", [])
        return tweets

    except Exception as e:
        print(f"Error fetching {token}:", e)
        return []

# =========================
# SIMPLE SIGNAL LOGIC
# =========================

def analyze_token(token, tweets):
    if not tweets:
        return None

    volume = len(tweets)

    score = min(volume * 4, 100)

    if score > 70:
        signal_type = "Early Signal"
        confidence = "High"
        reason = "Strong surge in mentions detected"
    elif score > 40:
        signal_type = "Narrative Build"
        confidence = "Medium"
        reason = "Attention is building around this token"
    else:
        signal_type = "Low Activity"
        confidence = "Low"
        reason = "Low attention levels"

    return {
        "ticker": token,
        "signal_type": signal_type,
        "confidence": confidence,
        "score": score,
        "reason": reason
    }

# =========================
# UPSERT SIGNAL
# =========================

def save_signal(signal):
    supabase.table("signals").insert(signal).execute()

# =========================
# MAIN LOOP
# =========================

def run_cycle():
    total = 0

    for token in TOKENS:
        tweets = fetch_tweets(token)
        signal = analyze_token(token, tweets)

        if signal:
            save_signal(signal)
            total += 1

    print(f"🚀 LIVE cycle completed | signals: {total}")

# =========================
# RUN LOOP
# =========================

if __name__ == "__main__":
    while True:
        run_cycle()
        time.sleep(60)