import os
import requests
import random
import time
import feedparser
from datetime import datetime
import re
import tweepy

# ================================
# CONFIGURATION
# ================================

# Get from GitHub Secrets
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Web3 Security RSS Feeds
WEB3_SECURITY_RSS_FEEDS = [
    'https://blog.trailofbits.com/feed/',
    'https://medium.com/feed/immunefi',
    'https://rekt.news/feed/',
    'https://halborn.com/blog/feed/',
    'https://slowmist.medium.com/feed',
    'https://consensys.io/blog/feed/',
    'https://blog.openzeppelin.com/feed/',
    'https://chainsecurity.com/news/feed/',
    'https://quantstamp.com/blog/feed/'
]

# ================================
# SIMPLE FILTERING FUNCTIONS
# ================================

def should_filter_article(article):
    """Simple filtering - only filter obvious spam/promotions"""
    title = article.get('title', '').lower()
    
    # Very basic spam indicators only
    spam_indicators = [
        'buy now', 'limited time', 'discount', 'coupon code',
        'token sale', 'airdrop', 'whitelist', 'presale', 'ico sale',
        'investment opportunity', 'earn money', 'make money'
    ]
    
    # Only filter if title contains obvious spam phrases
    for indicator in spam_indicators:
        if indicator in title:
            return True
    
    return False

# ================================
# TWITTER/X API FUNCTIONS
# ================================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret, image_url=None):
    """Post content to Twitter/X with optional image"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Ensure content is within Twitter limits
        if len(content) > 280:
            content = content[:277] + "..."
        
        # Upload media if image exists
        media_ids = []
        if image_url:
            # Clean up image URL
            clean_image_url = image_url.split('?')[0].split('&#')[0]
            
            # Use v1.1 API for media upload
            auth_v1 = tweepy.OAuthHandler(api_key, api_secret)
            auth_v1.set_access_token(access_token, access_token_secret)
            api_v1 = tweepy.API(auth_v1)
            
            # Download image and upload
            try:
                response = requests.get(clean_image_url, timeout=30)
                response.raise_for_status()
                
                # Save temporarily
                temp_file = "/tmp/tweet_image.jpg"
                with open(temp_file, "wb") as f:
                    f.write(response.content)
                
                # Check file size
                file_size = os.path.getsize(temp_file)
                if file_size <= 5 * 1024 * 1024:  # 5MB limit
                    media = api_v1.media_upload(filename=temp_file)
                    media_ids.append(media.media_id_string)
                
                # Clean up
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            except Exception:
                # Continue without image
                pass
        
        # Create tweet using v2
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Post the tweet
        if media_ids:
            response = client_v2.create_tweet(text=content, media_ids=media_ids)
        else:
            response = client_v2.create_tweet(text=content)
        
        if response and response.data:
            tweet_id = response.data['id']
            print(f"🎉 Successfully tweeted! Tweet ID: {tweet_id}")
            return True
        else:
            return False
            
    except Exception:
        return False

# ================================
# CONTENT GENERATION FUNCTIONS
# ================================

def fetch_web3_security_news():
    """Fetch current web3 security news from RSS feeds"""
    try:
        print("📰 Fetching Web3 security news...")
        articles = []
        
        for rss_url in WEB3_SECURITY_RSS_FEEDS:
            try:
                feed = feedparser.parse(rss_url)
                
                if not feed.entries:
                    continue
                
                for entry in feed.entries[:5]:
                    article_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        article_date = datetime(*entry.published_parsed[:6])
                    
                    # Skip if article is too old (2 days max)
                    if article_date and (datetime.now() - article_date).days > 2:
                        continue
                    
                    # Extract image from entry
                    image_url = None
                    if hasattr(entry, 'media_content') and entry.media_content:
                        for media in entry.media_content:
                            if 'url' in media and media.get('type', '').startswith('image'):
                                image_url = media['url']
                                break
                    
                    article = {
                        'title': entry.title,
                        'link': entry.link,
                        'summary': entry.summary if hasattr(entry, 'summary') else '',
                        'published': article_date,
                        'image_url': image_url
                    }
                    
                    # Only add if not obvious spam
                    if not should_filter_article(article):
                        articles.append(article)
                
                time.sleep(0.5)
                
            except Exception:
                continue
        
        print(f"✅ Found {len(articles)} security articles")
        return articles
        
    except Exception:
        return []

def generate_hashtags(topic):
    """Generate hashtags using AI"""
    prompt = f"""
    Generate 4-5 relevant hashtags for a Web3 security post about: {topic}
    
    Requirements:
    - Focus on Web3/blockchain security
    - Mix popular and technical hashtags
    - Return ONLY hashtags as: #First #Second #Third #Fourth
    
    Example output for smart contract security: #SmartContracts #Web3Security #Audit #Blockchain
    """
    
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                hashtags = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                hashtags = hashtags.replace('```', '').strip()
                return hashtags
    except Exception:
        pass
    
    return "#Web3Security #Blockchain #Security #Crypto"

def generate_post_content(article):
    """Generate Twitter post content from article"""
    topic = article['title']
    
    prompt = f"""
    Create a Twitter post about this Web3 security topic: {topic}
    
    Requirements:
    - Keep it concise (under 220 characters for hashtags)
    - Focus on the security aspect
    - Make it informative and valuable
    - Don't include hashtags in the main text
    - Keep it natural and professional
    
    Just write the post text, no explanations.
    """
    
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                post_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                post_text = post_text.replace('```', '').strip()
                
                # Clean up
                post_text = ' '.join(post_text.split())
                
                # Add AI-generated hashtags
                hashtags = generate_hashtags(topic)
                full_post = f"{post_text} {hashtags}"
                
                # Ensure length
                if len(full_post) > 280:
                    full_post = full_post[:277] + "..."
                
                return full_post
    except Exception:
        pass
    
    # If AI fails, create simple post
    title_summary = topic[:150]
    hashtags = "#Web3Security #Blockchain #Security"
    return f"{title_summary}... {hashtags}"

# ================================
# MAIN EXECUTION
# ================================

def main():
    print("🔐 Web3 Security Content Creator")
    print("=" * 50)
    
    # Validate configuration
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        return
    
    if not GEMINI_API_KEY:
        return
    
    # Fetch security articles
    articles = fetch_web3_security_news()
    
    # If no articles found, just exit quietly
    if not articles:
        return
    
    # Shuffle and pick one article
    random.shuffle(articles)
    article = articles[0]
    
    # Generate post content
    post_text = generate_post_content(article)
    
    # Get image if available
    image_url = article.get('image_url')
    
    # Post to Twitter
    success = post_to_twitter(
        post_text, 
        TWITTER_API_KEY, 
        TWITTER_API_SECRET, 
        TWITTER_ACCESS_TOKEN, 
        TWITTER_ACCESS_TOKEN_SECRET,
        image_url
    )
    
    if success:
        print("✅ Posted successfully")
    else:
        print("⚠️ Failed to post")

if __name__ == "__main__":
    main()