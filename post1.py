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

# Expanded RSS Feeds - Tech + Game Dev
TECH_RSS_FEEDS = [
    'https://techcrunch.com/feed',
    'https://www.wired.com/feed/rss',
    'https://arstechnica.com/feed',
    'https://venturebeat.com/feed',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.mashable.com/mashable/tech',
    'https://www.digitaltrends.com/feed'
]

GAME_DEV_RSS_FEEDS = [
    'https://blog.unity.com/feed',
    'https://80.lv/feed/',
    'https://www.gamedeveloper.com/rss',
    'https://www.gamesindustry.biz/feed',
    'https://videogamemarketing.com/feed/',
    'https://www.indiedb.com/engine/unity/feed',
    'https://www.rockpapershotgun.com/feed',
    'https://kotaku.com/rss'
]

# ================================
# TWITTER/X API FUNCTIONS
# ================================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret, image_url=None):
    """Post content to Twitter/X with optional image using the correct API versions"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Ensure content is within Twitter limits
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        # --- UPLOAD MEDIA (using v1.1) ---
        media_ids = []
        if image_url:
            print(f"📤 Uploading media from {image_url}...")
            
            # Use v1.1 API for media upload (this is allowed on Free tier)
            auth_v1 = tweepy.OAuthHandler(api_key, api_secret)
            auth_v1.set_access_token(access_token, access_token_secret)
            api_v1 = tweepy.API(auth_v1)
            
            # Download image and upload
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Save temporarily
            temp_file = "/tmp/tweet_image.jpg"
            with open(temp_file, "wb") as f:
                f.write(response.content)
            
            media = api_v1.media_upload(filename=temp_file)
            media_ids.append(media.media_id_string)
            
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
            print(f"✅ Media uploaded successfully! ID: {media.media_id_string}")
        
        # --- CREATE TWEET (using v2) ---
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Post the tweet using v2 endpoint
        if media_ids:
            response = client_v2.create_tweet(text=content, media_ids=media_ids)
        else:
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
# CONTENT GENERATION FUNCTIONS
# ================================

def fetch_tech_news_from_rss():
    """Fetch current tech news from RSS feeds - RANDOM SELECTION"""
    try:
        print("📰 Fetching latest tech news...")
        articles = fetch_news_from_feeds(TECH_RSS_FEEDS, "tech")
        
        random.shuffle(articles)
        print(f"🎲 Randomly selected from {len(articles)} tech articles")
        return articles
        
    except Exception as e:
        print(f"❌ Tech RSS fetch error: {e}")
        return []

def fetch_game_dev_news_from_rss():
    """Fetch current game development news from RSS feeds - RANDOM SELECTION"""
    try:
        print("🎮 Fetching latest game dev news...")
        articles = fetch_news_from_feeds(GAME_DEV_RSS_FEEDS, "game dev")
        
        random.shuffle(articles)
        print(f"🎲 Randomly selected from {len(articles)} game dev articles")
        return articles
        
    except Exception as e:
        print(f"❌ Game dev RSS fetch error: {e}")
        return []

def fetch_news_from_feeds(feed_list, category):
    """Generic function to fetch news from RSS feeds"""
    all_articles = []
    
    for rss_url in feed_list:
        try:
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                continue
            
            for entry in feed.entries[:3]:
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_date = datetime(*entry.published_parsed[:6])
                
                # Skip if article is too old
                if article_date and (datetime.now() - article_date).days > 3:
                    continue
                
                # Extract image from entry
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

def extract_image_from_entry(entry):
    """Extract image URL from RSS entry"""
    try:
        # Check multiple possible locations for images
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if 'url' in media and media.get('type', '').startswith('image'):
                    return media['url']
        
        if hasattr(entry, 'links'):
            for link in entry.links:
                if hasattr(link, 'type') and link.type and 'image' in link.type:
                    return link.href
                elif hasattr(link, 'rel') and link.rel == 'enclosure':
                    return link.href
        
        if hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if enclosure.type and 'image' in enclosure.type:
                    return enclosure.href
        
        # Try to extract from content/summary
        content_text = ""
        if hasattr(entry, 'content'):
            for content in entry.content:
                content_text += content.value + " "
        elif hasattr(entry, 'summary'):
            content_text = entry.summary
        
        # Simple regex to find image URLs in content
        image_urls = re.findall(r'<img[^>]+src="([^">]+)"', content_text)
        if image_urls:
            return image_urls[0]
                    
        return None
    except Exception as e:
        print(f"⚠️ Error extracting image: {e}")
        return None

def get_google_trends_topics():
    """Get current trending topics"""
    try:
        print("📈 Checking Google Trends...")
        
        pytrends = TrendReq(hl='en-US', tz=360)
        trending_searches = pytrends.trending_searches(pn='united_states')
        
        trends = trending_searches[0].tolist()[:10]
        print(f"✅ Found trending topics: {trends}")
        return trends
        
    except Exception as e:
        print(f"❌ Google Trends error: {e}")
        return ['AI technology', 'gaming trends', 'tech innovation']

def generate_hashtags(topic, content_type):
    """Generate relevant hashtags using AI"""
    prompt = f"""
    Generate 3-4 highly relevant, popular hashtags for a {content_type} post about: {topic}
    
    Requirements:
    - Mix popular and niche hashtags
    - Include trending hashtags when relevant
    - Focus on {content_type} space (tech, gaming, indie dev, etc.)
    - Keep them short and effective
    - Return ONLY the hashtags as: #First #Second #Third
    
    Examples for tech: #AI #Tech #Innovation #FutureTech
    Examples for gaming: #GameDev #IndieDev #Gaming #Unity
    Examples for trends: #Trending #TechNews #Future
    
    Make them feel current and relevant.
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
                print(f"🏷️ AI-generated hashtags: {hashtags}")
                return hashtags
    except Exception as e:
        print(f"❌ Hashtag generation error: {e}")
    
    # Fallback hashtags
    if content_type == 'tech':
        return "#Tech #AI #Innovation #Future"
    elif content_type == 'game dev':
        return "#GameDev #IndieDev #Gaming #DevLife"
    else:
        return "#Trending #Tech #Insights"

def generate_tech_analysis_post(articles):
    """Generate sophisticated tech analysis post"""
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
    Create a SHORT, engaging Twitter post about tech trends. MAX 150 characters for main content.

    Topic: {main_topic}

    Writing style:
    - Sound like a smart, witty tech enthusiast
    - Add subtle humor and personality
    - Use 1-2 relevant emojis naturally
    - Be insightful but conversational
    - Sound human and authentic
    - Keep it strategic but fun

    Structure:
    - Start with an interesting observation
    - Add strategic insight with personality
    - End with engaging question/thought

    Examples:
    "AI is getting so smart, soon it'll be giving US performance reviews 😅 But seriously, this changes everything about how we work. Wild times ahead! 🤖"
    "Another day, another 'revolutionary' tech launch 🚀 This one actually has some interesting strategic implications though... Your take?"

    Return ONLY the post text (without hashtags).
    """
    
    post_text = generate_ai_content(prompt, selected_articles, 'tech', main_topic)
    return post_text, image_url

def generate_game_dev_post(articles):
    """Generate sophisticated game development post"""
    if not articles:
        return create_fallback_post('game dev'), None
    
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
    Create a SHORT, engaging Twitter post about game development. MAX 150 characters for main content.

    Topic: {main_topic}

    Writing style:
    - Sound like a passionate game developer/enthusiast
    - Add gaming humor and personality
    - Use 1-2 gaming-related emojis
    - Be insightful but conversational
    - Sound human and authentic
    - Mix strategic thinking with dev humor

    Structure:
    - Start with an interesting observation
    - Add industry insight with personality
    - End with engaging question/thought

    Examples:
    "Another 'game-changing' engine update? 🎮 Let's see if it actually helps indie devs or just adds more complexity 😂 Thoughts?"
    "Player expectations are evolving faster than my ability to fix bugs 🐛 But this shift towards community-driven games is fascinating!"

    Return ONLY the post text (without hashtags).
    """
    
    post_text = generate_ai_content(prompt, selected_articles, 'game dev', main_topic)
    return post_text, image_url

def generate_trending_topic_post(trends):
    """Generate post about trending topics"""
    if not trends:
        return create_fallback_post('trending'), None
    
    main_topic = trends[0]
    
    prompt = f"""
    Create a SHORT, engaging Twitter post about trending topics. MAX 150 characters for main content.

    Topic: {main_topic}

    Writing style:
    - Sound like a curious, witty observer
    - Add subtle humor about trends
    - Use 1-2 relevant emojis
    - Be insightful but conversational
    - Sound human and authentic
    - Mix trend analysis with personality

    Structure:
    - Start with an interesting observation about the trend
    - Add strategic insight with personality
    - End with engaging question/thought

    Examples:
    "Everyone's talking about this trend... and I can see why! 🤔 There's some real strategic gold here if you look closely. What's your read?"
    "Another day, another viral trend taking over my timeline 😅 But this one actually has some interesting implications. Your thoughts?"

    Return ONLY the post text (without hashtags).
    """
    
    post_text = generate_ai_content(prompt, trends, 'trending', main_topic)
    return post_text, None

def generate_trend_based_opinion_poll(trends):
    """Generate opinion poll post based on trending topics"""
    if not trends:
        return create_opinion_fallback()
    
    # Select a trending topic for the poll
    poll_topic = random.choice(trends[:5])
    
    prompt = f"""
    Create a SHORT, engaging Twitter opinion poll. MAX 180 characters TOTAL.

    Topic: {poll_topic}

    Writing style:
    - Sound like a curious, engaging community member
    - Add personality and subtle humor
    - Use 1-2 relevant emojis
    - Make it conversational and fun
    - Keep options clear but interesting

    Format:
    [Engaging question with personality - max 100 chars]
    A: [Fun option 1 - max 25 chars]
    B: [Fun option 2 - max 25 chars]
    [Brief engaging call to vote]

    Examples:
    "Strategic dilemma time! 🧐 For this trend, which approach wins?
    A: Go all in, YOLO style 🚀
    B: Wait and see, play it safe 🛡️
    Vote below! 👇"

    Return the complete post text (without additional hashtags).
    """
    
    try:
        print(f"🗳️ Generating opinion poll about trending topic: {poll_topic}")
        
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
                post_text = remove_ai_indicators(post_text)
                
                # Ensure it's short enough
                if len(post_text) > 180:
                    lines = post_text.split('\n')
                    if len(lines) >= 3:
                        lines[0] = lines[0][:90] + "..." if len(lines[0]) > 90 else lines[0]
                        post_text = '\n'.join(lines[:4])
                
                print(f"✅ Opinion poll created ({len(post_text)} chars)")
                return post_text
        else:
            print(f"❌ Poll generation error: {response.text}")
            
    except Exception as e:
        print(f"❌ Opinion poll generation error: {e}")
    
    return create_opinion_fallback(poll_topic)

def generate_ai_content(prompt, content, content_type, main_topic):
    """Generate content using AI and add AI-powered hashtags"""
    try:
        print(f"🎭 Generating {content_type} post...")
        
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
                
                # Add AI-generated hashtags for all post types
                hashtags = generate_hashtags(main_topic, content_type)
                post_text += f" {hashtags}"
                
                post_text = remove_ai_indicators(post_text)
                
                # Final length check and truncation if needed
                if len(post_text) > 280:
                    post_text = post_text[:277] + "..."
                
                print(f"✅ {content_type.title()} post created ({len(post_text)} chars)")
                return post_text
        else:
            print(f"❌ AI generation error: {response.text}")
            
    except Exception as e:
        print(f"❌ {content_type} generation error: {e}")
    
    return create_fallback_post(content_type)

def remove_ai_indicators(text):
    """Remove any phrases that sound AI-generated"""
    ai_phrases = [
        "as an AI", "according to AI", "AI-generated", "language model",
        "based on the provided", "in this content", "the writer",
        "this analysis", "the author", "in this piece", "according to the"
    ]
    
    for phrase in ai_phrases:
        text = text.replace(phrase, "")
        text = text.replace(phrase.title(), "")
    
    return ' '.join(text.split())

def create_fallback_post(content_type):
    """Create sophisticated fallback posts"""
    emojis = ["🚀", "🤔", "💡", "🎯", "🔥", "👀", "💭", "⚡"]
    
    if content_type == 'tech':
        fallbacks = [
            f"Tech moves fast but patterns emerge {random.choice(emojis)} This shift changes everything for builders. Wild times ahead!",
            f"Another 'revolutionary' launch {random.choice(emojis)} But this one actually has legs. Strategic implications are huge!"
        ]
    elif content_type == 'game dev':
        fallbacks = [
            f"Game dev never slows down {random.choice(emojis)} This evolution in player expectations is fascinating! Community over graphics?",
            f"Indie dev life: fixing bugs while trends shift {random.choice(emojis)} But this change actually makes sense long-term!"
        ]
    else:
        fallbacks = [
            f"Trends come and go but patterns remain {random.choice(emojis)} This one's actually worth paying attention to!",
            f"Another day, another viral moment {random.choice(emojis)} But the strategic angle here is genuinely interesting!"
        ]
    
    post_text = random.choice(fallbacks)
    hashtags = generate_hashtags("industry trends", content_type)
    post_text += f" {hashtags}"
    
    return post_text

def create_opinion_fallback(topic=None):
    """Create fallback opinion poll"""
    if not topic:
        topic = "industry strategy"
    
    emojis = ["🤔", "🧐", "💭", "🎯"]
    fallback_polls = [
        f"Strategic dilemma time! {random.choice(emojis)} For {topic}, which approach wins?\nA: Go big or go home 🚀\nB: Slow and steady wins 🐢\nWhat's your move?",
        f"Hot take needed! {random.choice(emojis)} On {topic}, which strategy?\nA: Innovate like crazy 💡\nB: Perfect what exists ⚡\nCast your vote! 👇"
    ]
    
    post_text = random.choice(fallback_polls)
    return post_text

# ================================
# POST TYPE SELECTOR
# ================================

def select_post_type():
    """Randomly select post type with weighted probability"""
    post_types = [
        ('tech', 0.3),        # 30% tech posts
        ('game_dev', 0.3),    # 30% game dev posts  
        ('trending', 0.2),    # 20% trending topics
        ('opinion_poll', 0.2) # 20% opinion polls
    ]
    
    choices, weights = zip(*post_types)
    return random.choices(choices, weights=weights)[0]

# ================================
# MAIN EXECUTION
# ================================

def main():
    print("🐦 Strategic Content Analyst - Twitter Edition")
    print("=" * 50)
    print("📰 Multi-Source Intelligence • AI-Powered Posts")
    print("🎮 Human Personality • Smart & Witty")
    print("=" * 50)
    
    # Validate configuration
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API secrets")
        return
        
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY secret")
        return
    
    print(f"✅ Twitter API configured")
    print(f"✅ Gemini API configured")
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
        image_url = None
    
    print(f"📝 Post: {post_text}")
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
        print("🤖 AI-powered personality")
        print("😄 Human-like & engaging")
    else:
        print("\n❌ Deployment failed.")

if __name__ == "__main__":
    main()