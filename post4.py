import os
import random
import feedparser
import re
import tweepy
from datetime import datetime
import google.generativeai as genai  # Keep using your current package

# ===================== CONFIG =====================
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Reddit-like RSS feeds (humor/life/work/internet behavior)
RSS_FEEDS = [
    "https://www.reddit.com/r/funny/.rss",
    "https://www.reddit.com/r/Unexpected/.rss",
    "https://www.reddit.com/r/antiwork/.rss",
    "https://www.reddit.com/r/mildlyinteresting/.rss",
]

# ===================== FUNCTIONS =====================

def parse_rss_feeds():
    """Parse all RSS feeds and return entries"""
    all_entries = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                # Skip old articles (older than 7 days)
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_date = datetime(*entry.published_parsed[:6])
                    if article_date and (datetime.now() - article_date).days > 7:
                        continue
                all_entries.append({
                    'title': entry.title,
                    'summary': entry.get('summary', ''),
                    'link': entry.link
                })
        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")
    return all_entries

def generate_text_post():
    """Generate a standalone text tweet"""
    entries = parse_rss_feeds()
    if not entries:
        # Fallback prompt
        prompt = "Create a funny, observational, standalone tweet about life, work, relationships, or internet behavior. Keep it under 280 characters."
    else:
        entry = random.choice(entries)
        prompt = (
            f"Create a funny, standalone, conversational Twitter post based on this content:\n\n"
            f"Title: {entry['title']}\nSummary: {entry['summary']}\n\n"
            f"- Keep it under 280 characters\n"
            f"- Observational and humorous\n"
            f"- Must be readable and standalone, no hashtags or links\n"
        )
    try:
        response = model.generate_content(prompt)
        text_content = response.text.strip()
        # Clean formatting
        text_content = re.sub(r'\*\*|\*|__|_', '', text_content)
        return text_content[:280]  # Ensure max length
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

def post_to_twitter(content):
    """Post text-only tweet"""
    try:
        print("🐦 Posting to Twitter/X...")
        if len(content) > 280:
            content = content[:277] + "..."
        
        client_v2 = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        response = client_v2.create_tweet(text=content)
        if response and response.data:
            tweet_id = response.data['id']
            print(f"🎉 Successfully tweeted! Tweet ID: {tweet_id}")
            return True
        else:
            print("❌ Twitter post failed: No response data")
            return False
    except Exception as e:
        print(f"❌ Twitter post error: {e}")
        if hasattr(e, 'response'):
            print(e.response.text)
        return False

# ===================== MAIN =====================

def main():
    print("🐦 Reddit Content - Text-Only Twitter Edition")
    print("💬 LIFE / WORK / RELATIONSHIPS / INTERNET BEHAVIOR POSTS")
    print("🌟 OBSERVATIONAL & HUMOROUS TONE")
    print("🤖 USING GEMINI 2.5 FLASH")
    print("="*50)
    
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        return
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return
    
    text_post = generate_text_post()
    if text_post:
        print("Tweet text:\n", text_post)
        success = post_to_twitter(text_post)
        if success:
            print("✅ Successfully posted to Twitter!")
        else:
            print("❌ Failed to post.")
    else:
        print("❌ No text generated, skipping post.")

if __name__ == "__main__":
    main()