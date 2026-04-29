import os
import re
import time
import hashlib
from supabase import create_client

SUPABASE_URL = os.getenv("https://bvvzbtxeqpzqdwwjabws.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2dnpidHhlcXB6cWR3d2phYndzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjg2NjIsImV4cCI6MjA5Mjk0NDY2Mn0.ZsORzusxgxiLq59rE6n4EcPG13j1VGaTK7Mz0nRZJ6A")

if not SUPABASE_URL:
    raise ValueError("Missing SUPABASE_URL Railway variable")

if not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_KEY Railway variable")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BULLISH_WORDS = [
    "bullish", "send", "sending", "breakout", "long", "buy",
    "buying", "accumulation", "moon", "pump", "strong", "gem",
    "ready", "run", "reversal"
]

BEARISH_WORDS = [
    "dump", "short", "sell", "exit", "rug", "scam",
    "weak", "dead", "risk", "avoid"
]


def make_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def extract_tickers(text):
    matches = re.findall(r"\$[A-Z]{2,10}", text)
    return list(set([m.replace("$", "") for m in matches]))


def detect_sentiment(text):
    text_lower = text.lower()

    bullish = sum(1 for word in BULLISH_WORDS if word in text_lower)
    bearish = sum(1 for word in BEARISH_WORDS if word in text_lower)

    if bullish > bearish:
        return "bullish"

    if bearish > bullish:
        return "bearish"

    return "neutral"


def build_signals(tweets):
    signals = []

    for tweet in tweets:
        tickers = extract_tickers(tweet["text"])
        sentiment = detect_sentiment(tweet["text"])

        for ticker in tickers:
            if sentiment == "bullish":
                signal_type = "Narrative Build"
                confidence = "Medium"
                score = 65
                reason = "Positive attention is building around this coin."
            elif sentiment == "bearish":
                signal_type = "Bearish Attention"
                confidence = "Medium"
                score = 45
                reason = "Negative sentiment is stronger than positive sentiment."
            else:
                signal_type = "Neutral Mention"
                confidence = "Low"
                score = 25
                reason = "Coin was mentioned, but sentiment is unclear."

            signal_key = make_hash(ticker + "|" + signal_type + "|" + reason)

            signals.append({
                "signal_key": signal_key,
                "ticker": ticker,
                "signal_type": signal_type,
                "confidence": confidence,
                "score": score,
                "reason": reason,
                "mentions": 1,
                "unique_kols": 1,
                "attention_score": score,
                "price_change": 0
            })

    return signals


def save_signals(signals):
    inserted = 0
    updated = 0

    for signal in signals:
        existing = supabase.table("signals").select("id").eq(
            "signal_key", signal["signal_key"]
        ).execute()

        if existing.data:
            supabase.table("signals").update(signal).eq(
                "signal_key", signal["signal_key"]
            ).execute()
            updated += 1
        else:
            supabase.table("signals").insert(signal).execute()
            inserted += 1

    print(f"Signals inserted: {inserted}")
    print(f"Signals updated: {updated}")


def run_cycle():
    tweets = fetch_tweets()
    signals = build_signals(tweets)

    save_signals(signals)

    print(f"🚀 LIVE cycle completed | signals: {len(signals)}")


if __name__ == "__main__":
    while True:
        try:
            run_cycle()
        except Exception as e:
            print("❌ ERROR:", e)

        time.sleep(60)