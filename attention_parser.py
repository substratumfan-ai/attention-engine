import re
import math
import csv
import hashlib
import os
import time
from supabase import create_client, Client

SUPABASE_URL = "https://bvvzbtxeqpzqdwwjabws.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2dnpidHhlcXB6cWR3d2phYndzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjg2NjIsImV4cCI6MjA5Mjk0NDY2Mn0.ZsORzusxgxiLq59rE6n4EcPG13j1VGaTK7Mz0nRZJ6A"

CSV_PATH = os.path.join(os.path.dirname(__file__), "tweets.csv")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BULLISH_WORDS = [
    "bullish", "send", "sending", "breakout", "long", "buying",
    "accumulation", "early", "moon", "ready", "run", "pump",
    "strong", "undervalued", "reversal", "gem", "send it"
]

BEARISH_WORDS = [
    "dump", "short", "sell", "exit", "overvalued", "distribution",
    "weak", "dead", "avoid", "rug", "risk", "scam"
]


def fetch_tweets():
    tweets = []

    with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            tweets.append({
                "user": row["user"],
                "followers": int(row["followers"]),
                "text": row["text"],
                "likes": int(row["likes"]),
                "retweets": int(row["retweets"]),
                "timestamp": row["timestamp"]
            })

    return tweets


def make_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def extract_tickers(text):
    matches = re.findall(r"\$[A-Z]{2,10}", text)
    return list(set([m.replace("$", "") for m in matches]))


def detect_sentiment(text):
    lower = text.lower()
    score = 0

    for word in BULLISH_WORDS:
        if word in lower:
            score += 1

    for word in BEARISH_WORDS:
        if word in lower:
            score -= 1

    if score > 0:
        return "bullish", score
    elif score < 0:
        return "bearish", score
    return "neutral", score


def calculate_tweet_weight(followers, likes, retweets):
    follower_score = math.log10(max(followers, 1)) * 10
    engagement_score = math.log10(max(likes + retweets, 1)) * 8
    return round(follower_score + engagement_score, 2)


def parse_tweet(tweet):
    sentiment, sentiment_score = detect_sentiment(tweet["text"])

    tweet_hash = make_hash(
        tweet["user"] + "|" + tweet["text"] + "|" + tweet["timestamp"]
    )

    return {
        "tweet_hash": tweet_hash,
        "user": tweet["user"],
        "followers": tweet["followers"],
        "text": tweet["text"],
        "coins": extract_tickers(tweet["text"]),
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "weight": calculate_tweet_weight(tweet["followers"], tweet["likes"], tweet["retweets"]),
        "engagement": {
            "likes": tweet["likes"],
            "retweets": tweet["retweets"]
        },
        "timestamp": tweet["timestamp"]
    }


def aggregate_by_coin(parsed_tweets):
    coins = {}

    for tweet in parsed_tweets:
        for coin in tweet["coins"]:
            if coin not in coins:
                coins[coin] = {
                    "ticker": coin,
                    "mentions": 0,
                    "weighted_mentions": 0,
                    "bullish": 0,
                    "bearish": 0,
                    "neutral": 0,
                    "unique_kols": set()
                }

            coins[coin]["mentions"] += 1
            coins[coin]["weighted_mentions"] += tweet["weight"]
            coins[coin]["unique_kols"].add(tweet["user"])

            if tweet["sentiment"] == "bullish":
                coins[coin]["bullish"] += 1
            elif tweet["sentiment"] == "bearish":
                coins[coin]["bearish"] += 1
            else:
                coins[coin]["neutral"] += 1

    result = []

    for coin, data in coins.items():
        result.append({
            "ticker": coin,
            "mentions": data["mentions"],
            "weighted_mentions": round(data["weighted_mentions"], 2),
            "attention_score": min(100, round(data["weighted_mentions"] / 2, 1)),
            "unique_kols": len(data["unique_kols"]),
            "bullish": data["bullish"],
            "bearish": data["bearish"],
            "neutral": data["neutral"]
        })

    return sorted(result, key=lambda x: x["attention_score"], reverse=True)


def detect_signals(coin_summary):
    signals = []

    for coin in coin_summary:
        ticker = coin["ticker"]
        mentions = coin["mentions"]
        kols = coin["unique_kols"]
        attention = coin["attention_score"]
        bullish = coin["bullish"]
        bearish = coin["bearish"]

        signal_type = None
        confidence = "Low"
        score = 0
        reason = ""

        if mentions >= 2 and kols >= 2 and attention < 80 and bullish > bearish:
            signal_type = "Early Signal"
            confidence = "High"
            score = attention + 10
            reason = "KOL activity is rising while attention has not fully peaked yet."

        elif kols >= 3:
            signal_type = "KOL Cluster"
            confidence = "High"
            score = attention + 15
            reason = "Multiple KOLs are posting about the same coin."

        elif mentions >= 3 and kols <= 1:
            signal_type = "Fake Pump Risk"
            confidence = "Medium"
            score = max(0, attention - 10)
            reason = "High mention count but low unique KOL participation."

        elif attention > 85:
            signal_type = "Exhaustion"
            confidence = "Medium"
            score = attention
            reason = "Attention is already very high, possible late-stage hype."

        elif mentions >= 1 and bullish > bearish:
            signal_type = "Narrative Build"
            confidence = "Medium"
            score = attention
            reason = "Positive attention is building around this coin."

        elif bearish > bullish:
            signal_type = "Bearish Attention"
            confidence = "Medium"
            score = attention
            reason = "Negative sentiment is stronger than positive sentiment."

        if signal_type:
            signal_key = make_hash(ticker + "|" + signal_type + "|" + reason)

            signals.append({
                "signal_key": signal_key,
                "ticker": ticker,
                "signal_type": signal_type,
                "confidence": confidence,
                "score": round(score, 2),
                "reason": reason,
                "mentions": mentions,
                "unique_kols": kols,
                "attention_score": attention,
                "price_change": 0
            })

    return sorted(signals, key=lambda x: x["score"], reverse=True)


def save_to_supabase(parsed_tweets, coin_summary):
    inserted_tweets = 0
    skipped_tweets = 0

    for tweet in parsed_tweets:
        existing = supabase.table("tweets").select("id").eq("tweet_hash", tweet["tweet_hash"]).execute()

        if existing.data:
            skipped_tweets += 1
            continue

        res = supabase.table("tweets").insert({
            "tweet_hash": tweet["tweet_hash"],
            "username": tweet["user"],
            "followers": tweet["followers"],
            "text": tweet["text"],
            "sentiment": tweet["sentiment"],
            "sentiment_score": tweet["sentiment_score"],
            "weight": tweet["weight"],
            "likes": tweet["engagement"]["likes"],
            "retweets": tweet["engagement"]["retweets"],
            "created_at": tweet["timestamp"]
        }).execute()

        inserted_tweets += 1
        tweet_id = res.data[0]["id"]

        for coin in tweet["coins"]:
            supabase.table("coin_mentions").insert({
                "tweet_id": tweet_id,
                "ticker": coin
            }).execute()

    for coin in coin_summary:
        existing_summary = supabase.table("coin_summary").select("id").eq("ticker", coin["ticker"]).execute()

        payload = {
            "ticker": coin["ticker"],
            "mentions": coin["mentions"],
            "weighted_mentions": coin["weighted_mentions"],
            "attention_score": coin["attention_score"],
            "unique_kols": coin["unique_kols"],
            "bullish": coin["bullish"],
            "bearish": coin["bearish"],
            "neutral": coin["neutral"]
        }

        if existing_summary.data:
            supabase.table("coin_summary").update(payload).eq("ticker", coin["ticker"]).execute()
        else:
            supabase.table("coin_summary").insert(payload).execute()

    print(f"Tweets inserted: {inserted_tweets}")
    print(f"Tweets skipped duplicates: {skipped_tweets}")


def save_signals(signals):
    inserted_signals = 0
    updated_signals = 0

    for signal in signals:
        existing = supabase.table("signals").select("id").eq("signal_key", signal["signal_key"]).execute()

        payload = {
            "signal_key": signal["signal_key"],
            "ticker": signal["ticker"],
            "signal_type": signal["signal_type"],
            "confidence": signal["confidence"],
            "score": signal["score"],
            "reason": signal["reason"],
            "mentions": signal["mentions"],
            "unique_kols": signal["unique_kols"],
            "attention_score": signal["attention_score"],
            "price_change": signal["price_change"]
        }

        if existing.data:
            supabase.table("signals").update(payload).eq("signal_key", signal["signal_key"]).execute()
            updated_signals += 1
        else:
            supabase.table("signals").insert(payload).execute()
            inserted_signals += 1

    print(f"Signals inserted: {inserted_signals}")
    print(f"Signals updated: {updated_signals}")


def run_cycle():
    raw_tweets = fetch_tweets()
    parsed = [parse_tweet(tweet) for tweet in raw_tweets]
    parsed = [tweet for tweet in parsed if len(tweet["coins"]) > 0]

    coin_summary = aggregate_by_coin(parsed)
    signals = detect_signals(coin_summary)

    save_to_supabase(parsed, coin_summary)
    save_signals(signals)

    print("✅ CSV tweet engine cycle completed")


if __name__ == "__main__":
    while True:
        try:
            run_cycle()
        except Exception as e:
            print("❌ ERROR:", e)

        time.sleep(60)
