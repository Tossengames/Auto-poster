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
# REDDIT RSS FEEDS - LIFE / WORK / RELATIONSHIPS / INTERNET BEHAVIOR NICHE
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
# ================================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret, image_url=None):
    """Post content to Twitter/X (text-only, image_url ignored)"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Ensure content is within Twitter limits
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        # Use v2 client
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        response = client_v2.create_tweet(text=content)
        
        if response and response.data:
            tweet_id = response.data['id']
            print(f"🎉 Successfully tweeted! Tweet ID: {tweet_id}")
            return True
        else:
            print("❌ Twitter post failed: No response data")
            return False
            
    except tweepy.TweepyException as e:
        print(f"❌ Twitter API error: {e}")
        return False
    except Exception as e:
        print(f"💥 Twitter post error: {e}")
        return False

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
# PARSE REDDIT RSS
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
                    'images': []  # No images for Reddit RSS
                })
        except Exception as e:
            print(f"Error parsing Reddit feed {feed_url}: {e}")
    return all_entries

# ================================
# GENERATE ENGAGING POST
# ================================

def generate_engaging_post():
    """Generate a single standalone, humorous or observational post using Reddit RSS"""
    entries = parse_reddit_rss()
    
    if not entries:
        return generate_fallback_post()
    
    entry = random.choice(entries)
    posted_links.add(entry['link'])
    
    # Purely text-based, no images
    image_url = None
    
    # AI prompt for a single, standalone tweet
    prompt = (
        f"Write a single, standalone, witty, conversational tweet reacting to this online discussion:\n\n"
        f"Title: {entry['title']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"Requirements:\n"
        f"- Observational, humorous, or relatable\n"
        f"- Standalone: must make sense by itself\n"
        f"- Topic: life, work, relationships, internet behavior\n"
        f"- Use emojis sparingly\n"
        f"- Maximum 200 characters\n"
        f"- Do not include hashtags\n"
        f"- No references to sources or Reddit\n"
    )
    
    try:
        response = model.generate_content(prompt)
        text_content = response.text.strip()
        text_content = re.sub(r'\*\*|\*|__|_', '', text_content)
        return text_content, image_url
    
    except Exception as e:
        print(f"AI content generation error: {e}")
        return generate_fallback_post()

def generate_fallback_post():
    """Fallback single text-only Reddit-style humorous post"""
    fallbacks = [
        "Everyone wants to wake up at 5am but nobody wants to sleep early. 😴💭 What habit confuses you the most?",
        "We all ghost people online and then wonder why we feel lonely. 👀💬 Has this happened to you?",
        "People love productivity hacks but skip the actual work. 🤷‍♂️📈 Which one do you actually follow?"
    ]
    return random.choice(fallbacks), None

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