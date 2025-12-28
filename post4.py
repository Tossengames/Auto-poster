import os
import google.generativeai as genai
import random
import feedparser
import re
import tweepy
import requests

# Configuration
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Reddit RSS feeds for niche
REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/AskReddit/.rss",
    "https://www.reddit.com/r/relationships/.rss",
    "https://www.reddit.com/r/antiwork/.rss",
    "https://www.reddit.com/r/selfimprovement/.rss",
    "https://www.reddit.com/r/technology/.rss"
]

posted_links = set()

# =============================
# TWITTER API
# =============================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret):
    """Post text-only tweet"""
    try:
        if len(content) > 280:
            content = content[:277] + "..."
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        response = client_v2.create_tweet(text=content)
        return bool(response and response.data)
    except Exception as e:
        print(f"Twitter post error: {e}")
        return False

def get_trending_hashtags_for_text(text, count=3):
    """Fetch trending hashtags and select ones relevant to the tweet text"""
    try:
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        # Get US trends (WOEID 23424977)
        bearer_token = client._bearer_token
        url = "https://api.twitter.com/1.1/trends/place.json?id=23424977"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        resp = requests.get(url, headers=headers).json()
        trends = resp[0]["trends"]
        hashtags = [t["name"] for t in trends if t["name"].startswith("#")]

        # Filter hashtags to be relevant to words in the text
        words = set(re.findall(r'\b[a-zA-Z]{3,}\b', text.lower()))
        relevant = [h for h in hashtags if any(w in h.lower() for w in words)]
        random.shuffle(relevant)
        return relevant[:count] if relevant else hashtags[:count]
    except Exception as e:
        print(f"Failed to fetch trending hashtags: {e}")
        return []

# =============================
# HELPERS
# =============================

def contains_political_content(text):
    POLITICAL_KEYWORDS = [
        'trump','biden','president','election','government','policy',
        'tax','war','political','democrat','republican','vote'
    ]
    return any(k in text.lower() for k in POLITICAL_KEYWORDS) if text else False

# =============================
# PARSE REDDIT RSS
# =============================

def parse_reddit_rss():
    entries = []
    for url in REDDIT_RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.link in posted_links:
                    continue
                if contains_political_content(entry.title) or contains_political_content(entry.get('summary','')):
                    continue
                entries.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary','')
                })
        except Exception as e:
            print(f"RSS error {url}: {e}")
    return entries

# =============================
# GENERATE TWEET
# =============================

def generate_engaging_post():
    entries = parse_reddit_rss()
    if not entries:
        print("No valid RSS entries found.")
        return None

    entry = random.choice(entries)
    posted_links.add(entry['link'])
    
    prompt = (
        f"Create ONE standalone, easy-to-read tweet about this online discussion:\n\n"
        f"Title: {entry['title']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"Requirements:\n"
        f"- Funny/observational about modern life, work, relationships or internet behavior\n"
        f"- Use line breaks and emojis for readability\n"
        f"- Must make sense by itself\n"
        f"- Max 250 characters\n"
        f"- Do NOT mention Reddit or sources"
    )
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'\*\*|\*|__|_', '', text).strip()
        hashtags = get_trending_hashtags_for_text(text, count=3)
        final_tweet = f"{text}\n\n{' '.join(hashtags)}" if hashtags else text
        if len(final_tweet) > 280:
            final_tweet = final_tweet[:277] + "..."
        return final_tweet
    except Exception as e:
        print(f"AI generation failed: {e}")
        return None

# =============================
# MAIN
# =============================

def main():
    print("🐦 Reddit Content - Twitter Edition")
    
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        return
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return
    
    post_text = generate_engaging_post()
    if not post_text:
        print("❌ AI failed to generate a tweet or no trending hashtags found. Skipping post.")
        return
    
    print(f"Tweet:\n{post_text}\n")
    
    success = post_to_twitter(
        post_text,
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    )
    
    print("✅ Posted!" if success else "❌ Failed to post.")

if __name__ == "__main__":
    main()