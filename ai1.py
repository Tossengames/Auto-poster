import os
import requests
import random
import time
import feedparser
from datetime import datetime, timedelta
import re
import tweepy

# ================================
# CONFIGURATION FROM ENVIRONMENT
# ================================
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# RSS Feeds for AI/ML content
AI_RSS_FEEDS = [
    'https://ai.googleblog.com/feeds/posts/default',
    'https://openai.com/blog/rss/',
    'https://deepmind.google/blog/feed.xml',
    'https://huggingface.co/blog/feed.xml',
    'https://blog.tensorflow.org/feeds/posts/default',
    'https://pytorch.org/blog/feed/',
    'https://www.fast.ai/rss.xml',
    'https://distill.pub/rss.xml'
]

# Keywords that indicate promotional content
PROMOTIONAL_TERMS = [
    'sponsored', 'advertisement', 'advertorial', 'partner post',
    'limited time', 'buy now', 'shop now', 'discount', 'coupon',
    'special offer', 'exclusive deal', 'sign up', 'subscribe',
    'free trial', 'contact sales', 'request demo', 'pricing'
]

# ================================
# SIMPLIFIED FILTERING FUNCTIONS
# ================================
def should_filter_article(article):
    """Check if article should be filtered out"""
    combined_text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    
    # Filter out promotional content
    if any(term in combined_text for term in PROMOTIONAL_TERMS):
        return True
    
    # Filter out old articles (older than 14 days)
    pub_date = article.get('published')
    if pub_date:
        age_days = (datetime.now() - pub_date).days
        if age_days > 14:
            return True
    
    return False

def filter_articles(articles):
    """Filter articles using list comprehension"""
    filtered = []
    for article in articles:
        if not should_filter_article(article):
            filtered.append(article)
    return filtered

# ================================
# CONTENT FETCHING
# ================================
def fetch_articles():
    """Fetch and filter articles from all RSS feeds"""
    all_articles = []
    
    for feed_url in AI_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                continue
                
            for entry in feed.entries[:5]:  # Limit entries per feed
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                article = {
                    'title': entry.title if hasattr(entry, 'title') else 'No title',
                    'link': entry.link if hasattr(entry, 'link') else '#',
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'published': pub_date,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else 'Unknown',
                    'image_url': extract_image(entry)
                }
                all_articles.append(article)
                
            time.sleep(0.5)  # Be polite to servers
            
        except Exception as e:
            continue
    
    return all_articles

def extract_image(entry):
    """Extract image URL from feed entry"""
    try:
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if media.get('type', '').startswith('image'):
                    return media['url']
        
        if hasattr(entry, 'links'):
            for link in entry.links:
                if getattr(link, 'type', '').startswith('image'):
                    return link.href
        
        # Try to extract from content
        content = ""
        if hasattr(entry, 'content'):
            if isinstance(entry.content, list):
                content = ' '.join([c.value for c in entry.content if hasattr(c, 'value')])
            elif hasattr(entry.content, 'value'):
                content = entry.content.value
                
        elif hasattr(entry, 'summary'):
            content = entry.summary
            
        img_matches = re.findall(r'<img[^>]+src="([^">]+)"', content)
        if img_matches:
            return img_matches[0]
            
    except Exception:
        pass
    return None

# ================================
# CONTENT GENERATION WITH GEMINI
# ================================
def generate_tweet_content(article):
    """Generate tweet content using Gemini API"""
    print(f"\n[DEBUG] Generating tweet for: {article['title'][:60]}...")
    
    try:
        # Clean and prepare the summary
        summary = article['summary']
        if len(summary) > 300:
            summary = summary[:300] + "..."
        
        # Clean HTML tags from summary
        summary = re.sub(r'<[^>]+>', '', summary)
        
        prompt = f"""
        Create a tweet about this AI topic: "{article['title']}"
        
        Key points: {summary}
        
        Requirements:
        - Write in a professional tone
        - Include key insight or takeaway
        - End with 3-4 relevant hashtags (like #AI, #MachineLearning, etc.)
        - Maximum 280 characters total
        - DO NOT include URLs or links
        - Focus on the technical/value aspect
        """
        
        print(f"[DEBUG] Calling Gemini API...")
        
        # Try Gemini 1.5 Flash instead - more reliable endpoint
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            },
            timeout=30
        )
        
        print(f"[DEBUG] Gemini API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[DEBUG] Response received successfully")
            
            if data.get("candidates") and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"[DEBUG] Generated text: {text[:100]}...")
                return text[:280]
            else:
                print(f"[DEBUG] No candidates in response")
                print(f"[DEBUG] Full response: {data}")
                return None
        elif response.status_code == 400:
            print(f"[DEBUG] Bad request - likely invalid API key or quota")
            print(f"[DEBUG] Response: {response.text[:200]}")
            return None
        elif response.status_code == 429:
            print(f"[DEBUG] Rate limited - quota exceeded")
            return None
        else:
            print(f"[DEBUG] Gemini API error: {response.status_code}")
            return None
        
    except requests.exceptions.Timeout:
        print(f"[DEBUG] Gemini API timeout")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[DEBUG] Gemini API connection error")
        return None
    except Exception as e:
        print(f"[DEBUG] Gemini API error: {type(e).__name__}: {str(e)[:100]}")
        return None

# ================================
# TWITTER POSTING
# ================================
def post_to_twitter(content):
    """Post content to Twitter using Tweepy"""
    try:
        print(f"\n[DEBUG] Posting to Twitter...")
        
        # Authenticate
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        
        # Use API v1.1 for compatibility
        api = tweepy.API(auth, wait_on_rate_limit=True)
        
        # Verify credentials
        user = api.verify_credentials()
        print(f"[DEBUG] Twitter auth successful: @{user.screen_name}")
        
        # Post tweet
        tweet = api.update_status(content)
        print(f"[DEBUG] Tweet posted: ID {tweet.id}")
        
        return True
        
    except tweepy.TweepyException as e:
        print(f"[DEBUG] Twitter API error: {e}")
        return False
    except Exception as e:
        print(f"[DEBUG] Posting error: {type(e).__name__}: {str(e)[:100]}")
        return False

# ================================
# MAIN EXECUTION FLOW
# ================================
def main():
    print("🤖 AI Content Bot Starting...")
    print("=" * 50)
    
    # Validate credentials
    required_vars = [
        TWITTER_API_KEY, TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET,
        GEMINI_API_KEY
    ]
    
    missing_vars = []
    var_names = ['TWITTER_API_KEY', 'TWITTER_API_SECRET', 'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_TOKEN_SECRET', 'GEMINI_API_KEY']
    
    for name, value in zip(var_names, required_vars):
        if not value:
            missing_vars.append(name)
    
    if missing_vars:
        print(f"❌ Missing: {', '.join(missing_vars)}")
        return
    
    print("✅ All environment variables are set")
    
    # Fetch and filter articles
    print("\n📡 Fetching articles...")
    articles = fetch_articles()
    
    if not articles:
        print("⏭️ No articles found. Skipping post.")
        return
    
    print(f"📊 Found {len(articles)} articles")
    
    filtered_articles = filter_articles(articles)
    
    if not filtered_articles:
        print("⏭️ No articles passed filtering. Skipping post.")
        return
    
    print(f"✅ {len(filtered_articles)} articles after filtering")
    
    # Select random article
    selected_article = random.choice(filtered_articles)
    print(f"\n🎯 Selected: {selected_article['title'][:80]}...")
    
    # Generate tweet content
    tweet_content = generate_tweet_content(selected_article)
    
    if not tweet_content:
        print("\n❌ Failed to generate tweet content. Skipping post.")
        print("   This is usually due to:")
        print("   1. Invalid Gemini API key in GitHub Secrets")
        print("   2. API quota exceeded")
        print("   3. Network issue in GitHub Actions")
        return
    
    print(f"\n📝 Generated tweet ({len(tweet_content)} chars):")
    print("-" * 50)
    print(tweet_content)
    print("-" * 50)
    
    # Post to Twitter
    success = post_to_twitter(tweet_content)
    
    if success:
        print("\n🎉 Success!")
    else:
        print("\n❌ Failed to post")

# ================================
# ENTRY POINT
# ================================
if __name__ == "__main__":
    main()