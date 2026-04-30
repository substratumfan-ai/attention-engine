import os
import re
import time
import hashlib
import requests
from supabase import create_client

# =============================
# CONFIG / FALLBACKS
# =============================

SUPABASE_URL = os.getenv("https://bvvzbtxeqpzqdwwjabws.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2dnpidHhlcXB6cWR3d2phYndzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjg2NjIsImV4cCI6MjA5Mjk0NDY2Mn0.ZsORzusxgxiLq59rE6n4EcPG13j1VGaTK7Mz0nRZJ6A")
TWITTER_API_KEY = os.getenv("new1_810cb3d65f14407b8108a542758105db")

FALLBACK_SUPABASE_URL = "https://bvvzbtxeqpzqdwwjabws.supabase.co"
FALLBACK_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2dnpidHhlcXB6cWR3d2phYndzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjg2NjIsImV4cCI6MjA5Mjk0NDY2Mn0.ZsORzusxgxiLq59rE6n4EcPG13j1VGaTK7Mz0nRZJ6A"
FALLBACK_TWITTER_API_KEY = "new1_810cb3d65f14407b8108a542758105db"

if not SUPABASE_URL:
    print("⚠️ Railway SUPABASE_URL missing, using fallback")
    SUPABASE_URL = FALLBACK_SUPABASE_URL

if not SUPABASE_KEY:
    print("⚠️ Railway SUPABASE_KEY missing, using fallback")
    SUPABASE_KEY = FALLBACK_SUPABASE_KEY

if not TWITTER_API_KEY:
    print("⚠️ Railway TWITTER_API_KEY missing, using fallback")
    TWITTER_API_KEY = FALLBACK_TWITTER_API_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TWITTER_SEARCH_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"

TOKENS = ["BTC", "ETH", "SOL", "RAVE", "SEEK", "BONK"]
SEARCH_LIMIT = 20
LOOP_SECONDS = 60

BULLISH_WORDS = [
    "bullish", "buy", "bought", "buying", "long", "send", "sending",
    "breakout", "pump", "moon", "strong", "accumulation", "ready",
    "run", "reversal", "undervalued", "gem", "entry", "bounce"
]

BEARISH_WORDS = [
    "bearish", "dump", "short", "sell", "selling", "exit", "rug",
    "scam", "weak", "dead", "risk", "avoid", "distribution",
    "overvalued", "breakdown"
]


# =============================
# HELPERS
# =============================

def make_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_int(value, default=0):
    try:
        return int(value or default)
    except Exception:
        return default


def extract_text(tweet):
    return tweet.get("text") or tweet.get("fullText") or tweet.get("content") or ""


def extract_author(tweet):
    author = tweet.get("author") or {}

    username = (
        author.get("userName")
        or author.get("username")
        or author.get("screen_name")
        or "unknown"
    )

    followers = (
        author.get("followers")
        or author.get("followersCount")
        or author.get("followers_count")
        or 0
    )

    return username, safe_int(followers)


def detect_sentiment(text):
    lower = text.lower()

    bullish_score = sum(1 for word in BULLISH_WORDS if word in lower)
    bearish_score = sum(1 for word in BEARISH_WORDS if word in lower)

    if bullish_score > bearish_score:
        return "bullish", bullish_score - bearish_score

    if bearish_score > bullish_score:
        return "bearish", bearish_score - bullish_score

    return "neutral", 0


def calculate_weight(followers, likes, retweets, replies):
    follower_score = min(followers / 10000, 40)
    engagement_score = min((likes + retweets * 2 + replies) / 10, 40)
    return round(follower_score + engagement_score, 2)


# =============================
# TWITTER FETCH
# =============================

def fetch_tweets(token):
    headers = {
        "X-API-Key": TWITTER_API_KEY
    }

    query = f'("${token}" OR "{token}") lang:en -is:retweet'

    params = {
        "query": query,
        "limit": SEARCH_LIMIT
    }

    try:
        response = requests.get(
            TWITTER_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=30
        )

        data = response.json()

        print(f"Twitter status for {token}: {response.status_code}")

        if response.status_code != 200:
            print("Twitter error:", data)
            return []

        tweets = data.get("tweets", [])

        print(f"Fetched {len(tweets)} tweets for {token}")

        return tweets

    except Exception as e:
        print(f"❌ Error fetching {token}:", e)
        return []


# =============================
# SIGNAL ENGINE
# =============================

def analyze_token(token, tweets):
    if not tweets:
        return None

    mentions = 0
    bullish = 0
    bearish = 0
    neutral = 0
    total_weight = 0
    unique_kols = set()

    for tweet in tweets:
        text = extract_text(tweet)
        text_lower = text.lower()

        if token.lower() not in text_lower and f"${token.lower()}" not in text_lower:
            continue

        username, followers = extract_author(tweet)

        likes = safe_int(tweet.get("likeCount"))
        retweets = safe_int(tweet.get("retweetCount"))
        replies = safe_int(tweet.get("replyCount"))

        sentiment, sentiment_score = detect_sentiment(text)
        weight = calculate_weight(followers, likes, retweets, replies)

        mentions += 1
        total_weight += weight
        unique_kols.add(username)

        if sentiment == "bullish":
            bullish += 1
        elif sentiment == "bearish":
            bearish += 1
        else:
            neutral += 1

        print(f"TWEET [{token}]: {text[:160]}")

    if mentions == 0:
        return None

    unique_kol_count = len(unique_kols)

    attention_score = min(
        100,
        round((mentions * 8) + (unique_kol_count * 12) + total_weight, 2)
    )

    if attention_score >= 75 and bullish > bearish:
        signal_type = "Early Signal"
        confidence = "High"
        reason = "Strong attention growth with bullish sentiment and multiple mentions."
    elif bullish > bearish:
        signal_type = "Narrative Build"
        confidence = "Medium"
        reason = "Positive attention is building around this token."
    elif bearish > bullish:
        signal_type = "Bearish Attention"
        confidence = "Medium"
        reason = "Negative sentiment is stronger than positive sentiment."
    else:
        signal_type = "Attention Mention"
        confidence = "Low"
        reason = "Token is receiving attention, but sentiment is not clear yet."

    signal_key = make_hash(f"{token}|{signal_type}|{reason}")

    return {
        "signal_key": signal_key,
        "ticker": token,
        "signal_type": signal_type,
        "confidence": confidence,
        "score": attention_score,
        "reason": reason,
        "mentions": mentions,
        "unique_kols": unique_kol_count,
        "attention_score": attention_score,
        "price_change": 0
    }


# =============================
# SUPABASE SAVE
# =============================

def save_signal(signal):
    existing = supabase.table("signals").select("id").eq(
        "signal_key", signal["signal_key"]
    ).execute()

    if existing.data:
        supabase.table("signals").update(signal).eq(
            "signal_key", signal["signal_key"]
        ).execute()
        print(f"Signals updated: 1 | {signal['ticker']}")
    else:
        supabase.table("signals").insert(signal).execute()
        print(f"Signals inserted: 1 | {signal['ticker']}")


# =============================
# MAIN LOOP
# =============================

def run_cycle():
    total_signals = 0

    for token in TOKENS:
        tweets = fetch_tweets(token)
        signal = analyze_token(token, tweets)

        if signal:
            save_signal(signal)
            total_signals += 1
        else:
            print(f"No signal for {token}")

    print(f"🚀 LIVE cycle completed | signals: {total_signals}")


if __name__ == "__main__":
    while True:
        try:
            run_cycle()
        except Exception as e:
            print("❌ ERROR:", e)

        time.sleep(LOOP_SECONDS)