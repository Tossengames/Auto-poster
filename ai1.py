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
    
    # Filter out promotional content[citation:1]
    if any(term in combined_text for term in PROMOTIONAL_TERMS):
        return True
    
    # Filter out old articles (older than 7 days)
    pub_date = article.get('published')
    if pub_date and (datetime.now() - pub_date).days > 7:
        return True
    
    return False

def filter_articles(articles):
    """Filter articles using list comprehension[citation:2][citation:5][citation:8]"""
    # This is simpler and more Pythonic than using map/filter[citation:2]
    return [
        article for article in articles
        if not should_filter_article(article)
    ]

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
                    pub_date = datetime(*entry.published_parsed[:6])
                
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'published': pub_date,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else 'Unknown',
                    'image_url': extract_image(entry)
                }
                all_articles.append(article)
                
            time.sleep(0.5)  # Be polite to servers
            
        except Exception as e:
            print(f"⚠️ Error fetching {feed_url}: {e}")
            continue
    
    # Apply filtering[citation:7]
    filtered = filter_articles(all_articles)
    print(f"📰 Found {len(filtered)} articles after filtering")
    return filtered

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
            content = ' '.join([c.value for c in entry.content])
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
    try:
        prompt = f"""
        Create an engaging tweet about this AI/ML topic: "{article['title']}"
        
        Key points from article: {article['summary'][:200]}...
        
        Requirements:
        - Write in a professional but engaging tone
        - Include key insight or takeaway
        - End with 3-4 relevant hashtags (like #AI, #MachineLearning, etc.)
        - Maximum 280 characters total
        - DO NOT include URLs, links, or mentions
        - Focus on the technical/content value
        
        Format: [Tweet content] [hashtags]
        """
        
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("candidates"):
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return text[:280]  # Ensure length limit
        
    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
    
    return None

# ================================
# TWITTER POSTING
# ================================
def post_to_twitter(content):
    """Post content to Twitter using Tweepy[citation:9]"""
    try:
        # Authenticate
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)
        
        # Verify credentials[citation:9]
        api.verify_credentials()
        print("✅ Twitter authentication successful")
        
        # Post tweet
        api.update_status(content)
        print(f"✅ Tweet posted: {content[:50]}...")
        return True
        
    except tweepy.TweepyException as e:
        print(f"❌ Twitter error: {e}")
        return False
    except Exception as e:
        print(f"❌ Posting error: {e}")
        return False

# ================================
# MAIN EXECUTION FLOW
# ================================
def main():
    print("🤖 AI Content Bot Starting...")
    print("=" * 40)
    
    # Validate credentials
    required_vars = [
        TWITTER_API_KEY, TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET,
        GEMINI_API_KEY
    ]
    
    if not all(required_vars):
        print("❌ Missing environment variables")
        return
    
    # Fetch and filter articles
    articles = fetch_articles()
    
    # Skip if no articles found[citation:4]
    if not articles:
        print("⏭️ No articles found after filtering. Skipping post.")
        return
    
    # Select random article
    selected_article = random.choice(articles)
    print(f"📖 Selected article: {selected_article['title'][:60]}...")
    
    # Generate tweet content
    tweet_content = generate_tweet_content(selected_article)
    
    if not tweet_content:
        print("❌ Failed to generate tweet content")
        return
    
    print(f"📝 Generated tweet ({len(tweet_content)} chars):")
    print(f"---\n{tweet_content}\n---")
    
    # Post to Twitter
    success = post_to_twitter(tweet_content)
    
    if success:
        print("🎉 Bot execution completed successfully!")
    else:
        print("❌ Bot execution failed")

# ================================
# ENTRY POINT
# ================================
if __name__ == "__main__":
    main()