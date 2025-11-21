import os
import requests
import random
import time
import json
import feedparser
from datetime import datetime
import pytrends
from pytrends.request import TrendReq
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

# ... (Keep your existing RSS_FEEDS and STRATEGIC_HASHTAGS lists)

# ================================
# TWITTER/X API FUNCTIONS
# ================================

def upload_media(image_url, api):
    """Download and upload an image to Twitter."""
    try:
        print(f"📤 Uploading media from {image_url}...")
        
        # Download the image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Save temporarily
        temp_file = "/tmp/tweet_image.jpg"
        with open(temp_file, "wb") as f:
            f.write(response.content)
        
        # Upload to Twitter
        media = api.media_upload(filename=temp_file)
        
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        print(f"✅ Media uploaded successfully! ID: {media.media_id_string}")
        return media.media_id_string
        
    except Exception as e:
        print(f"❌ Media upload failed: {e}")
        return None

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret, image_url=None):
    """Post content to Twitter/X with optional image"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Authenticate with Twitter API
        auth = tweepy.OAuthHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth)
        
        # Ensure content is within Twitter limits
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        media_ids = []
        if image_url:
            media_id = upload_media(image_url, api)
            if media_id:
                media_ids.append(media_id)
        
        # Post the tweet
        if media_ids:
            response = api.update_status(status=content, media_ids=media_ids)
            print("✅ Tweet with image posted successfully!")
        else:
            response = api.update_status(status=content)
            print("✅ Text-only tweet posted successfully!")
            
        if response:
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
# ENHANCED RSS PROCESSING
# ================================

def extract_image_from_entry(entry):
    """Extract image URL from RSS entry"""
    try:
        # Check multiple possible locations for images
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0]['url']
        elif hasattr(entry, 'links'):
            for link in entry.links:
                if hasattr(link, 'type') and 'image' in link.type:
                    return link.href
        elif hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if 'image' in enclosure.type:
                    return enclosure.href
        elif hasattr(entry, 'content'):
            for content in entry.content:
                # Simple regex to find image URLs in content
                import re
                image_urls = re.findall(r'<img[^>]+src="([^">]+)"', content.value)
                if image_urls:
                    return image_urls[0]
                    
        return None
    except Exception as e:
        print(f"⚠️ Error extracting image: {e}")
        return None

def fetch_news_from_feeds(feed_list, category):
    """Generic function to fetch news from RSS feeds - ENHANCED WITH IMAGE SUPPORT"""
    all_articles = []
    
    for rss_url in feed_list:
        try:
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                continue
            
            for entry in feed.entries[:3]:  # Get latest 3 entries
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_date = datetime(*entry.published_parsed[:6])
                
                # Skip if article is too old
                if article_date and (datetime.now() - article_date).days > 3:
                    continue
                
                # Extract image
                image_url = extract_image_from_entry(entry)
                
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'published': article_date,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else rss_url.split('//')[-1].split('/')[0],
                    'category': category,
                    'image_url': image_url
                }
                all_articles.append(article)
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"⚠️ Error parsing {rss_url}: {e}")
            continue
    
    print(f"✅ Found {len(all_articles)} recent {category} articles")
    return all_articles

# ================================
# ENHANCED CONTENT GENERATION
# ================================

def generate_tech_analysis_post(articles):
    """Generate sophisticated tech analysis post with image support"""
    if not articles:
        return create_fallback_post('tech'), None
    
    # RANDOM SELECTION: Pick 1-2 random articles
    selected_articles = random.sample(articles, min(2, len(articles)))
    main_topic = selected_articles[0]['title']
    
    # Try to find an article with an image
    image_url = None
    for article in selected_articles:
        if article.get('image_url'):
            image_url = article['image_url']
            break
    
    prompt = f"""
    Create a Twitter post analyzing technology trends with a sophisticated, strategic tone.
    Sound like a master strategist revealing patterns others miss.

    Recent tech developments:
    {chr(10).join([f"- {article['title']}" for article in selected_articles])}

    Writing style:
    - Sophisticated, strategic, intellectually superior
    - Connect developments to reveal larger patterns
    - Focus on strategic implications
    - Pose thought-provoking questions
    - Sound like you're revealing truths most overlook

    Structure:
    1. Start with an insightful observation
    2. Connect developments to show patterns
    3. Discuss strategic implications
    4. End with a provocative question (leave space for CTA)

    Important: 
    - DO NOT include a final CTA question - leave space for it to be added later.
    - Make it sound completely human-written. No AI phrasing.
    - Keep it under 180 characters to leave space for CTA and hashtags.
    - Be concise for Twitter format.

    Return ONLY the post text.
    """
    
    post_text = generate_ai_content(prompt, selected_articles, 'tech', main_topic)
    return post_text, image_url

# ... (Similarly modify generate_game_dev_post, generate_trending_topic_post functions)

# ================================
# ENHANCED MAIN EXECUTION
# ================================

def main():
    print("🐦 Strategic Content Analyst - Twitter Edition")
    print("=" * 50)
    print("📰 Multi-Source Intelligence • AI-Powered CTAs")
    print("🖼️ Image Support • Strategic Personality")
    print("=" * 50)
    
    # Validate configuration
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API secrets")
        return
        
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY secret")
        return
    
    print(f"✅ Twitter API Key: {'*' * 20}{TWITTER_API_KEY[-4:] if TWITTER_API_KEY else 'MISSING'}")
    print("")
    
    # Select post type
    post_type = select_post_type()
    print(f"🎯 Selected post type: {post_type.replace('_', ' ').title()}")
    
    # Gather content based on post type
    image_url = None
    if post_type == 'tech':
        articles = fetch_tech_news_from_rss()
        post_text, image_url = generate_tech_analysis_post(articles)
        
    elif post_type == 'game_dev':
        articles = fetch_game_dev_news_from_rss()
        post_text, image_url = generate_game_dev_post(articles)
        
    elif post_type == 'trending':
        trends = get_google_trends_topics()
        post_text, image_url = generate_trending_topic_post(trends)
        
    else:  # opinion_poll
        trends = get_google_trends_topics()
        post_text = generate_trend_based_opinion_poll(trends)
        # Opinion polls typically don't have images
    
    print(f"📝 Post preview: {post_text[:100]}...")
    print(f"📏 Character count: {len(post_text)}")
    print(f"🖼️ Image available: {'Yes' if image_url else 'No'}")
    
    # Post to Twitter
    print("\n🚀 Deploying strategic content...")
    success = post_to_twitter(
        post_text, 
        TWITTER_API_KEY, 
        TWITTER_API_SECRET, 
        TWITTER_ACCESS_TOKEN, 
        TWITTER_ACCESS_TOKEN_SECRET,
        image_url
    )
    
    if success:
        print("\n✅ Strategic content successfully deployed!")
        print(f"🎯 Post type: {post_type.replace('_', ' ').title()}")
        print(f"🖼️ Image included: {'Yes' if image_url else 'No'}")
        print("🤖 AI-generated CTAs and analysis")
    else:
        print("\n❌ Deployment failed.")

if __name__ == "__main__":
    main()