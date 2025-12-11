import os
import requests
import random
import time
import json
import feedparser
from datetime import datetime
import tweepy
import re

# =====================================
# CONFIG
# =====================================

TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- WEB3 / CRYPTO FEEDS ONLY ---
WEB3_RSS_FEEDS = [
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "https://blockworks.co/feed",
    "https://cryptobriefing.com/feed/",
    "https://thedefiant.io/feed",
    "https://www.securityweek.com/feed/",
    "https://krebsonsecurity.com/feed/",
    "https://portswigger.net/daily-swig/feed"
]

# Avoid low-quality promo/pump/airdrop spam
WEB3_PROMO_FILTER = [
    "airdrop", "giveaway", "free tokens", "pump", "low cap", 
    "moonshot", "signal group", "presale", "whitelist", 
    "casino", "betting", "bonus", "deposit", "gambling",
    "sponsored", "partnership", "launchpad", "meme coin"
]

QUALITY_KEYWORDS = [
    "blockchain", "ethereum", "bitcoin", "crypto",
    "layer 2", "security", "hack", "exploit", "breach",
    "zk", "rollup", "protocol", "governance",
    "wallet", "defi", "bridge", "sec", "regulation",
]

# =====================================
# HELPERS
# =====================================

def is_promo(article):
    text = (article.get("title","") + " " + article.get("summary","")).lower()
    return any(k in text for k in WEB3_PROMO_FILTER)

def is_quality(article):
    title = article.get("title","").lower()
    return any(k in title for k in QUALITY_KEYWORDS)

def extract_image(entry):
    try:
        if hasattr(entry, "media_content"):
            for m in entry.media_content:
                if "url" in m:
                    return m["url"]
        if hasattr(entry, "links"):
            for link in entry.links:
                if hasattr(link, "type") and "image" in link.type:
                    return link.href
        # regex
        if hasattr(entry, "summary"):
            imgs = re.findall(r'<img[^>]+src="([^">]+)"', entry.summary)
            if imgs:
                return imgs[0]
        return None
    except:
        return None

def fetch_web3_news():
    print("📡 Fetching Web3 RSS...")
    articles = []

    for feed_url in WEB3_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:6]:
                date = None
                if hasattr(entry, "published_parsed"):
                    date = datetime(*entry.published_parsed[:6])
                if date and (datetime.now() - date).days > 2:
                    continue

                articles.append({
                    "title": entry.title,
                    "summary": entry.summary if hasattr(entry, "summary") else "",
                    "link": entry.link,
                    "source": feed.feed.title if hasattr(feed.feed, "title") else "Unknown",
                    "image_url": extract_image(entry)
                })
        except:
            continue

    # Filter
    filtered = [
        a for a in articles 
        if not is_promo(a) and is_quality(a)
    ]

    print(f"✅ {len(filtered)} quality web3 articles found.")
    random.shuffle(filtered)
    return filtered

# =====================================
# AI GENERATION
# =====================================

def ai_generate(prompt: str):
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents":[{"parts":[{"text": prompt}]}]},
            timeout=40
        )
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except:
        return "Web3 keeps evolving fast — big shifts happening across the ecosystem."

def generate_web3_post(article):
    title = article["title"]

    prompt = f"""
Write a short, smart Twitter post about this Web3 topic:

Title: {title}

Style:
- Smart, clean Web3 + crypto insight
- Human tone, not hype
- 1–2 emojis max
- Max 150 characters
- No hashtags
- No promotions
- Add a small insight or question

Return ONLY the tweet text.
"""

    text = ai_generate(prompt)
    return text[:150]

# =====================================
# TWITTER POST
# =====================================

def twitter_post(text, img_url=None):
    try:
        # Upload media v1.1
        media_ids = []
        if img_url:
            try:
                auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
                auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
                api = tweepy.API(auth)

                img_data = requests.get(img_url, timeout=10).content
                temp = "/tmp/web3.jpg"
                with open(temp, "wb") as f:
                    f.write(img_data)

                media = api.media_upload(temp)
                media_ids.append(media.media_id_string)
            except:
                pass

        # Create tweet v2
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )

        if media_ids:
            client.create_tweet(text=text, media_ids=media_ids)
        else:
            client.create_tweet(text=text)

        print("✅ Tweet posted")
    except Exception as e:
        print(f"❌ Twitter error: {e}")

# =====================================
# MAIN
# =====================================

def run_web3_bot():
    articles = fetch_web3_news()
    if not articles:
        print("❌ No content")
        return

    article = articles[0]
    post = generate_web3_post(article)
    twitter_post(post, article.get("image_url"))

if __name__ == "__main__":
    run_web3_bot()