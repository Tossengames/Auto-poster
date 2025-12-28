import os
import google.generativeai as genai
import requests
import random
import feedparser
from datetime import datetime
import re
import time
import tweepy

# Configuration
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# ================================
# NEW: REDDIT RSS FEEDS - LIFE / WORK / RELATIONSHIP / INTERNET BEHAVIOR NICHE
# ================================
REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/AskReddit/.rss",
    "https://www.reddit.com/r/relationships/.rss",
    "https://www.reddit.com/r/antiwork/.rss",
    "https://www.reddit.com/r/selfimprovement/.rss",
    "https://www.reddit.com/r/technology/.rss"
]

# Cache to avoid duplicate posts
posted_links = set()

# ================================
# TWITTER/X API FUNCTIONS
# (UNCHANGED)
# ================================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret, image_url=None):
    # ... [keep your existing function exactly as-is] ...
    pass

# ================================
# CONTENT FUNCTIONS
# ================================

def contains_political_content(text):
    """Check if text contains political keywords"""
    POLITICAL_KEYWORDS = [
        'trump', 'biden', 'president', 'election', 'government', 'policy', 
        'tariff', 'tax', 'war', 'conflict', 'political', 'democrat', 'republican',
        'congress', 'senate', 'white house', 'administration', 'vote', 'campaign'
    ]
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in POLITICAL_KEYWORDS)

# ================================
# NEW: PARSE REDDIT RSS
# ================================

def parse_reddit_rss():
    """Parse Reddit RSS feeds and return non-political entries"""
    all_entries = []
    for feed_url in REDDIT_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if entry.link in posted_links:
                    continue
                if contains_political_content(entry.title) or contains_political_content(entry.get('summary', '')):
                    continue
                all_entries.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary', ''),
                    'published': datetime.now(),  # Reddit RSS doesn't have standard published date
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else feed_url.split('//')[-1].split('/')[0],
                    'images': []  # Reddit posts via RSS usually do not include images
                })
        except Exception as e:
            print(f"Error parsing Reddit feed {feed_url}: {e}")
    return all_entries

# ================================
# MODIFY GENERATE ENGAGING POST TO USE REDDIT RSS
# ================================

def generate_engaging_post():
    """Generate an engaging post using Reddit RSS"""
    entries = parse_reddit_rss()
    
    if not entries:
        # fallback to simple default text if no Reddit entries
        return generate_fallback_post()
    
    entry = random.choice(entries)
    posted_links.add(entry['link'])
    
    # No images for Reddit RSS by default
    image_url = None
    
    # Generate AI prompt
    prompt = (
        f"Write 3 short, witty, conversational tweets reacting to this online discussion:\n\n"
        f"Title: {entry['title']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"Requirements:\n"
        f"- Observational, humorous, or relatable\n"
        f"- Topics: life, work, relationships, internet behavior\n"
        f"- No hashtags\n"
        f"- Short, under 200 characters each\n"
        f"- Use emojis sparingly\n"
        f"- Sound like a human noticing online behavior\n"
    )
    
    try:
        response = model.generate_content(prompt)
        text_content = response.text.strip()
        text_content = re.sub(r'\*\*|\*|__|_', '', text_content)
        
        # Return the generated text and image (None)
        return text_content, image_url
    except Exception as e:
        print(f"AI content generation error: {e}")
        return generate_fallback_post()

def generate_fallback_post():
    """Fallback Reddit-style humorous post"""
    fallbacks = [
        {
            'text': "Everyone wants to wake up at 5am but nobody wants to sleep early. 😴💭 What habit confuses you the most? 👇",
            'image': None
        },
        {
            'text': "We all ghost people online and then wonder why we feel lonely. 👀💬 Has this happened to you? 👇",
            'image': None
        },
        {
            'text': "People love productivity hacks but skip the actual work. 🤷‍♂️📈 Which one do you follow? 👇",
            'image': None
        }
    ]
    fallback = random.choice(fallbacks)
    return fallback['text'], fallback['image']

# ================================
# MAIN EXECUTION
# ================================

def main():
    print("🐦 Reddit Content - Twitter Edition")
    print("=" * 50)
    print("💬 LIFE / WORK / RELATIONSHIPS / INTERNET BEHAVIOR POSTS")
    print("🌟 OBSERVATIONAL & HUMOROUS TONE")
    print("🤖 USING GEMINI 2.5 FLASH")
    print("=" * 50)
    
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        return
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return
    
    post_text, image_url = generate_engaging_post()
    
    print(f"📝 Post: {post_text}")
    print(f"📏 Character count: {len(post_text)}")
    print(f"🖼️ Image: {'Yes' if image_url else 'No'}")
    
    print("\n🚀 Posting to Twitter...")
    success = post_to_twitter(
        post_text, 
        TWITTER_API_KEY, 
        TWITTER_API_SECRET, 
        TWITTER_ACCESS_TOKEN, 
        TWITTER_ACCESS_TOKEN_SECRET,
        image_url
    )
    
    if success:
        print("\n✅ Successfully posted to Twitter!")
    else:
        print("\n❌ Failed to post to Twitter.")

if __name__ == "__main__":
    main()