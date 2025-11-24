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

# Curated RSS Feeds - Only quality sources
TECH_RSS_FEEDS = [
    'https://techcrunch.com/feed',
    'https://www.wired.com/feed/rss',
    'https://arstechnica.com/feed',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.mashable.com/mashable/tech'
]

GAME_DEV_RSS_FEEDS = [
    'https://blog.unity.com/feed',
    'https://80.lv/feed/',
    'https://www.gamedeveloper.com/rss',
    'https://www.gamesindustry.biz/feed',
    'https://www.rockpapershotgun.com/feed'
]

# Promotional keywords to filter out
PROMOTIONAL_KEYWORDS = [
    'discount', 'sale', 'coupon', 'promo', 'deal', 'offer', 'limited time',
    'buy now', 'shop', 'store', 'price drop', 'save', 'percent off',
    'exclusive offer', 'special offer', 'flash sale', 'black friday',
    'cyber monday', 'sponsored', 'advertisement', 'affiliate', 'partner',
    'promotion', 'bundle', 'free trial', 'subscribe', 'sign up', 'get started'
]

# Post styles for variety - updated for friendly tone
POST_STYLES = [
    "friendly_enthusiast",
    "curious_friend", 
    "helpful_techie",
    "excited_gamer",
    "thoughtful_buddy",
    "creative_mind"
]

# ================================
# SEASONAL & TIME AWARENESS FUNCTIONS
# ================================

def get_season():
    """Get current season based on date"""
    today = datetime.now()
    month = today.month
    
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "fall"

def get_seasonal_hashtags():
    """Get seasonal hashtags"""
    season = get_season()
    seasonal_hashtags = {
        "winter": ["#WinterTech", "#GameDevWinter", "#HolidayGaming", "#WinterInnovation"],
        "spring": ["#SpringTech", "#GameDevSpring", "#SpringGaming", "#SpringInnovation"],
        "summer": ["#SummerTech", "#SummerGameDev", "#SummerGaming", "#SunmerInnovation"],
        "fall": ["#FallTech", "#AutumnGameDev", "#FallGaming", "#FallInnovation"]
    }
    return random.sample(seasonal_hashtags.get(season, []), 2)

def get_day_specific_hashtags():
    """Get hashtags specific to the day of week"""
    today = datetime.now()
    day_name = today.strftime("%A").lower()
    
    day_hashtags = {
        "monday": ["#MondayMotivation", "#GameDevMonday", "#TechMonday", "#NewWeek"],
        "tuesday": ["#TechTuesday", "#GameDevTuesday", "#IndieDevTuesday", "#TuesdayTips"],
        "wednesday": ["#WednesdayWisdom", "#GameDevWednesday", "#MidweekTech", "#WIPWednesday"],
        "thursday": ["#ThrowbackThursday", "#TechThursday", "#GameDevThursday", "#TBT"],
        "friday": ["#FridayFeeling", "#GameDevFriday", "#TechFriday", "#FridayFun"],
        "saturday": ["#ScreenshotSaturday", "#GameDevSaturday", "#WeekendTech", "#IndieSaturday"],
        "sunday": ["#SundayFunday", "#GameDevSunday", "#WeekendGaming", "#SundayTech"]
    }
    return random.sample(day_hashtags.get(day_name, []), 2)

def is_special_occasion():
    """Check if today is a special occasion"""
    today = datetime.now()
    month_day = (today.month, today.day)
    
    special_occasions = {
        (12, 24): "christmas_eve",
        (12, 25): "christmas",
        (12, 31): "new_years_eve",
        (1, 1): "new_year",
        (10, 31): "halloween",
        (2, 14): "valentines",
        (7, 4): "independence_day",
        (11, 24): "thanksgiving"  # Approximate
    }
    
    return special_occasions.get(month_day)

def get_occasion_hashtags(occasion):
    """Get hashtags for special occasions"""
    occasion_hashtags = {
        "christmas_eve": ["#ChristmasEve", "#HolidayTech", "#GameDevHoliday", "#SeasonsGreetings"],
        "christmas": ["#MerryChristmas", "#ChristmasGaming", "#HolidayTech", "#ChristmasDay"],
        "new_years_eve": ["#NewYearsEve", "#YearInReview", "#GameDev2024", "#NYE"],
        "new_year": ["#HappyNewYear", "#NewYearNewGames", "#Tech2024", "#NewBeginnings"],
        "halloween": ["#Halloween", "#SpookyGames", "#HalloweenTech", "#TrickOrTreat"],
        "valentines": ["#ValentinesDay", "#GameDevLove", "#TechLove", "#Valentines"],
        "independence_day": ["#IndependenceDay", "#July4th", "#PatrioticGames", "#SummerTech"],
        "thanksgiving": ["#Thanksgiving", "#GratefulGaming", "#ThankfulTech", "#TurkeyDay"]
    }
    return random.sample(occasion_hashtags.get(occasion, []), 2)

def get_occasion_mood(occasion):
    """Get mood/feeling for special occasions"""
    occasion_moods = {
        "christmas_eve": "festive and magical",
        "christmas": "joyful and celebratory",
        "new_years_eve": "reflective and excited",
        "new_year": "hopeful and fresh",
        "halloween": "spooky and fun",
        "valentines": "loving and appreciative",
        "independence_day": "patriotic and celebratory",
        "thanksgiving": "grateful and warm"
    }
    return occasion_moods.get(occasion, "thoughtful")

# ================================
# CONTENT FILTERING FUNCTIONS
# ================================

def is_promotional_content(article):
    """Check if article contains promotional content"""
    title = article.get('title', '').lower()
    summary = article.get('summary', '').lower()
    
    # Check for promotional keywords
    for keyword in PROMOTIONAL_KEYWORDS:
        if keyword in title or keyword in summary:
            print(f"🚫 Filtered out promotional content: {keyword}")
            return True
    
    # Check for sponsored indicators
    if 'sponsored' in title or 'sponsored' in summary:
        print(f"🚫 Filtered out sponsored content")
        return True
    
    # Check for sales/discount language
    if any(word in title for word in ['% off', '$', '€', '£']):
        print(f"🚫 Filtered out price/discount content")
        return True
    
    return False

def is_quality_content(article):
    """Check if article is genuine tech/game dev content"""
    title = article.get('title', '').lower()
    
    # Positive indicators of quality content
    quality_indicators = [
        'analysis', 'review', 'guide', 'tutorial', 'news', 'update',
        'release', 'development', 'design', 'programming', 'engine',
        'studio', 'developer', 'industry', 'trend', 'future', 'ai',
        'technology', 'innovation', 'research', 'study', 'report',
        'interview', 'behind the scenes', 'post-mortem', 'case study'
    ]
    
    # Count quality indicators
    quality_score = sum(1 for indicator in quality_indicators if indicator in title)
    return quality_score > 0

def filter_articles(articles):
    """Filter out promotional and low-quality articles"""
    filtered_articles = []
    
    for article in articles:
        if not is_promotional_content(article) and is_quality_content(article):
            filtered_articles.append(article)
        else:
            print(f"🚫 Filtered out: {article['title'][:60]}...")
    
    print(f"✅ Filtered {len(articles)} -> {len(filtered_articles)} quality articles")
    return filtered_articles

# ================================
# TWITTER/X API FUNCTIONS
# ================================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret, image_url=None):
    """Post content to Twitter/X with optional image using the correct API versions"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Remove any Markdown formatting
        content = remove_markdown_formatting(content)
        
        # Ensure content is within Twitter limits
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        # --- UPLOAD MEDIA (using v1.1) ---
        media_ids = []
        if image_url:
            print(f"📤 Uploading media from {image_url}...")
            
            # Clean up image URL
            clean_image_url = image_url.split('?')[0].split('&#')[0]
            
            # Use v1.1 API for media upload (this is allowed on Free tier)
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
                if file_size > 5 * 1024 * 1024:  # 5MB limit
                    print(f"⚠️ Image too large ({file_size} bytes), skipping...")
                else:
                    media = api_v1.media_upload(filename=temp_file)
                    media_ids.append(media.media_id_string)
                    print(f"✅ Media uploaded successfully! ID: {media.media_id_string}")
                
                # Clean up
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            except Exception as e:
                print(f"⚠️ Failed to download/upload image: {e}")
                # Continue without image
        
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
    """Fetch current tech news from RSS feeds - WITH FILTERING"""
    try:
        print("📰 Fetching latest tech news...")
        articles = fetch_news_from_feeds(TECH_RSS_FEEDS, "tech")
        
        # Filter out promotional content
        filtered_articles = filter_articles(articles)
        
        random.shuffle(filtered_articles)
        print(f"🎲 Randomly selected from {len(filtered_articles)} quality tech articles")
        return filtered_articles
        
    except Exception as e:
        print(f"❌ Tech RSS fetch error: {e}")
        return []

def fetch_game_dev_news_from_rss():
    """Fetch current game development news from RSS feeds - WITH FILTERING"""
    try:
        print("🎮 Fetching latest game dev news...")
        articles = fetch_news_from_feeds(GAME_DEV_RSS_FEEDS, "game dev")
        
        # Filter out promotional content
        filtered_articles = filter_articles(articles)
        
        random.shuffle(filtered_articles)
        print(f"🎲 Randomly selected from {len(filtered_articles)} quality game dev articles")
        return filtered_articles
        
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
            
            for entry in feed.entries[:5]:  # Get more entries to filter from
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
        return ['gaming industry', 'tech innovation', 'software development', 'creative tools']

def generate_hashtags(topic, content_type):
    """Generate relevant hashtags using AI with seasonal/day awareness"""
    # Get special occasion first
    occasion = is_special_occasion()
    
    prompt = f"""
    Generate 3-4 highly relevant, popular hashtags for a {content_type} post about: {topic}
    
    Current season: {get_season()}
    Today is: {datetime.now().strftime('%A')}
    {f"Special occasion: {occasion}" if occasion else ""}
    
    Requirements:
    - Mix popular and niche hashtags
    - Include seasonal relevance when appropriate
    - Consider day of week (e.g., #ScreenshotSaturday for Saturday)
    - Focus on {content_type} space (tech, gaming, indie dev, etc.)
    - Keep them short and effective
    - Return ONLY the hashtags as: #First #Second #Third
    
    Examples for Saturday game dev: #ScreenshotSaturday #GameDev #IndieDev #Gaming
    Examples for winter tech: #WinterTech #AI #Innovation #Tech
    Examples for Friday: #FridayFeeling #GameDevFriday #Tech
    
    Make them feel current and relevant to genuine content.
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
    
    # Fallback: Combine AI hashtags with seasonal/day ones
    base_hashtags = "#Tech #GameDev #IndieDev"
    seasonal_hashtags = " ".join(get_seasonal_hashtags())
    day_hashtags = " ".join(get_day_specific_hashtags())
    
    if occasion:
        occasion_hashtags = " ".join(get_occasion_hashtags(occasion))
        return f"{base_hashtags} {seasonal_hashtags} {day_hashtags} {occasion_hashtags}"
    else:
        return f"{base_hashtags} {seasonal_hashtags} {day_hashtags}"

def generate_contextual_cta(post_text, topic):
    """Generate a relevant CTA based on the post content"""
    prompt = f"""
    Based on this Twitter post about "{topic}":
    
    "{post_text}"
    
    Create ONE engaging, conversational call-to-action that:
    - Directly relates to the post content
    - Encourages comments and discussion
    - Sounds natural and friendly
    - Is specific to the topic (e.g., if it's about GTA, ask what people are excited about)
    - Uses casual, conversational language
    - Is under 40 characters
    
    Return ONLY the CTA text (no quotes, no explanation).
    
    Examples:
    - "What feature are you most excited about?"
    - "Your favorite moment from this game?"
    - "What would you improve here?"
    - "Seen any cool alternatives?"
    - "Your take on this trend?"
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
                cta = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                cta = cta.replace('"', '').replace("'", "").strip()
                print(f"💬 AI-generated CTA: {cta}")
                return cta
    except Exception as e:
        print(f"❌ CTA generation error: {e}")
    
    # Fallback CTAs
    fallback_ctas = [
        "What do you think? 👀",
        "Your take on this? 💭",
        "Would love to hear your thoughts! 🗣️",
        "What's your experience with this? 🤔"
    ]
    return random.choice(fallback_ctas)

def quality_check_post(post_text, topic, content_type):
    """AI quality check to ensure posts make sense and are appropriate"""
    prompt = f"""
    Analyze this Twitter post about {topic} (content type: {content_type}):
    
    "{post_text}"
    
    Evaluate it on these criteria:
    1. Does it make logical sense?
    2. Is it factually reasonable (not making false claims)?
    3. Is the tone friendly and conversational?
    4. Is it free of markdown formatting and proper for Twitter?
    5. Is it engaging and likely to start conversations?
    
    Respond with ONLY "APPROVED" if it passes all criteria, or "REJECTED" if it fails any.
    If rejected, provide a brief reason after "REJECTED: ".
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
                result = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"🔍 Quality check result: {result}")
                return "APPROVED" in result.upper(), result
    except Exception as e:
        print(f"❌ Quality check error: {e}")
    
    # If quality check fails, default to approved to avoid blocking all posts
    return True, "Auto-approved due to check error"

def remove_markdown_formatting(text):
    """Remove Markdown formatting from text"""
    # Remove bold/italic markers
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    # Remove other Markdown symbols
    text = re.sub(r'#{1,6}\s?', '', text)  # headers
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # links
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text)  # code
    text = re.sub(r'~{2}(.*?)~{2}', r'\1', text)  # strikethrough
    return text.strip()

def get_post_style_prompt(style, topic, content_type):
    """Get different writing styles for variety with seasonal awareness - UPDATED FOR FRIENDLY TONE"""
    occasion = is_special_occasion()
    season = get_season()
    day_name = datetime.now().strftime("%A")
    
    base_prompts = {
        "friendly_enthusiast": f"""
        Create a warm, enthusiastic tweet about {topic}. Sound like an excited friend sharing cool news!
        Use natural, conversational language with emojis. Be genuinely excited about this {content_type} development.
        Keep it under 180 characters. Make it feel like you're chatting with friends.
        DO NOT start with greetings like "Hey friends" or "Hello everyone" - jump straight into the content.
        """,
        
        "curious_friend": f"""
        Write a curious, friendly tweet about {topic}. Sound like you're genuinely interested and want to learn together.
        Ask open questions that invite discussion. Use warm, approachable language.
        Keep it under 180 characters. Be authentically curious and friendly.
        DO NOT start with greetings like "Hey friends" or "Hello everyone" - jump straight into the content.
        """,
        
        "helpful_techie": f"""
        Share a helpful insight about {topic}. Sound like a friendly expert who wants to help others understand.
        Break it down in simple terms. Be encouraging and supportive of others in the {content_type} community.
        Keep it under 180 characters. Be helpful without being condescending.
        DO NOT start with greetings like "Hey friends" or "Hello everyone" - jump straight into the content.
        """,
        
        "excited_gamer": f"""
        Write an excited, passionate tweet about {topic}. Show genuine gaming enthusiasm!
        Sound like you just found something awesome and can't wait to share it with your gaming friends.
        Keep it under 180 characters. Be energetic and positive.
        DO NOT start with greetings like "Hey friends" or "Hello everyone" - jump straight into the content.
        """,
        
        "thoughtful_buddy": f"""
        Share a thoughtful observation about {topic}. Sound like a friend having a deep conversation over coffee.
        Be reflective but warm. Show you care about the {content_type} community and its direction.
        Keep it under 180 characters. Be insightful but approachable.
        DO NOT start with greetings like "Hey friends" or "Hello everyone" - jump straight into the content.
        """,
        
        "creative_mind": f"""
        Share a creative perspective on {topic}. Sound inspired and imaginative!
        Talk about possibilities and creative potential in the {content_type} space.
        Keep it under 180 characters. Be visionary but grounded.
        DO NOT start with greetings like "Hey friends" or "Hello everyone" - jump straight into the content.
        """
    }
    
    base_prompt = base_prompts.get(style, base_prompts["friendly_enthusiast"])
    
    # Add seasonal/occasion context
    if occasion:
        mood = get_occasion_mood(occasion)
        if occasion == "christmas":
            base_prompt += f"\n\nIt's Christmas! Add some holiday cheer and warmth to make it feel {mood} and festive."
        elif occasion == "new_year":
            base_prompt += f"\n\nIt's New Year's Day! Add some hopeful, fresh energy looking forward to the year ahead."
        else:
            base_prompt += f"\n\nIt's a special occasion! Add some {mood} vibes to match the day."
    
    # Add seasonal context
    season_context = {
        "winter": "Add some cozy winter vibes - perfect for indoor dev work and gaming sessions with hot cocoa! ☕",
        "spring": "Add some fresh spring energy - new beginnings and exciting growth in the air! 🌸",
        "summer": "Add some sunny summer vibes - great for gaming marathons and outdoor coding! ☀️",
        "fall": "Add some cozy fall atmosphere - perfect for creative work with a warm drink! 🍂"
    }
    base_prompt += f"\n\n{season_context.get(season, '')}"
    
    # Add day-specific context for weekends
    if day_name.lower() in ['saturday', 'sunday']:
        base_prompt += f"\n\nIt's the weekend! Perfect time for gaming adventures and creative projects with friends."
    
    return base_prompt

def add_conversation_starter(post_text, topic):
    """Add a relevant AI-generated CTA to encourage comments and discussion"""
    # Remove any existing punctuation at the end
    post_text = post_text.rstrip('.,!?')
    
    # Generate contextual CTA
    cta = generate_contextual_cta(post_text, topic)
    
    # Ensure we don't exceed character limit
    new_text = f"{post_text} {cta}"
    
    if len(new_text) > 280:
        # If too long, truncate the main text slightly to fit the CTA
        available_space = 280 - len(cta) - 5  # 5 for space and buffer
        truncated_text = post_text[:available_space].rstrip('.,!?') + "..."
        new_text = f"{truncated_text} {cta}"
    
    return new_text

def generate_tech_analysis_post(articles):
    """Generate friendly tech analysis post - ONLY QUALITY CONTENT"""
    if not articles:
        return create_fallback_post('tech'), None
    
    # RANDOM SELECTION: Pick from filtered quality articles
    selected_articles = random.sample(articles, min(2, len(articles)))
    main_topic = selected_articles[0]['title']
    
    # Try to find an article with an image
    image_url = None
    for article in selected_articles:
        if article.get('image_url'):
            image_url = article['image_url']
            break
    
    # Choose random style for variety
    style = random.choice(POST_STYLES)
    print(f"🎨 Using post style: {style}")
    
    prompt = f"""
    {get_post_style_prompt(style, main_topic, 'tech')}

    Topic context: {main_topic}

    IMPORTANT FRIENDLY TONE GUIDELINES:
    - Sound like you're talking to friends, not making a formal announcement
    - Use natural, conversational language with personality
    - Include appropriate emojis to show emotion and tone
    - Be genuinely excited or curious about the topic
    - Avoid corporate speak or overly technical jargon
    - Make it feel like a real conversation starter
    - Keep it warm, approachable, and engaging
    - DO NOT use any markdown formatting (no *, _, ~, etc.)
    - DO NOT start with greetings like "Hey friends" or "Hello everyone"

    Return ONLY the post text (without hashtags).
    """
    
    post_text = generate_ai_content(prompt, selected_articles, 'tech', main_topic)
    
    # Add conversation starter
    post_text = add_conversation_starter(post_text, main_topic)
    
    return post_text, image_url

def generate_game_dev_post(articles):
    """Generate friendly game development post - ONLY QUALITY CONTENT"""
    if not articles:
        return create_fallback_post('game dev'), None
    
    # RANDOM SELECTION: Pick from filtered quality articles
    selected_articles = random.sample(articles, min(2, len(articles)))
    main_topic = selected_articles[0]['title']
    
    # Try to find an article with an image
    image_url = None
    for article in selected_articles:
        if article.get('image_url'):
            image_url = article['image_url']
            break
    
    # Choose random style for variety
    style = random.choice(POST_STYLES)
    print(f"🎨 Using post style: {style}")
    
    # Special handling for ScreenshotSaturday
    day_name = datetime.now().strftime("%A").lower()
    screenshot_saturday_note = ""
    if day_name == "saturday":
        screenshot_saturday_note = "Since it's Saturday, make it perfect for #ScreenshotSaturday - encourage sharing progress and celebrating each other's work!"

    prompt = f"""
    {get_post_style_prompt(style, main_topic, 'game development')}

    Topic context: {main_topic}
    {screenshot_saturday_note}

    IMPORTANT FRIENDLY TONE GUIDELINES:
    - Sound like a fellow gamer/developer excited to share with friends
    - Use gaming community language that feels natural and inclusive
    - Show genuine passion for game development and gaming culture
    - Be encouraging and supportive of other developers
    - Make it feel like you're chatting in a game dev Discord server
    - Include gaming-related emojis where appropriate
    - DO NOT use any markdown formatting (no *, _, ~, etc.)
    - DO NOT start with greetings like "Hey friends" or "Hello everyone"

    Return ONLY the post text (without hashtags).
    """
    
    post_text = generate_ai_content(prompt, selected_articles, 'game dev', main_topic)
    
    # Add conversation starter
    post_text = add_conversation_starter(post_text, main_topic)
    
    return post_text, image_url

def generate_trending_topic_post(trends):
    """Generate friendly post about trending topics"""
    if not trends:
        return create_fallback_post('trending'), None
    
    # Skip AI-focused trends that create repetitive posts
    filtered_trends = [t for t in trends if not any(ai_word in t.lower() for ai_word in 
                      ['ai predict', 'ai knows', 'ai getting', 'ai will', 'ai can'])]
    
    if not filtered_trends:
        filtered_trends = trends  # Fall back to original if all filtered
    
    main_topic = random.choice(filtered_trends[:5])  # More random selection
    
    # Choose random style for variety
    style = random.choice(POST_STYLES)
    print(f"🎨 Using post style: {style}")
    
    prompt = f"""
    {get_post_style_prompt(style, main_topic, 'tech/gaming trends')}

    Topic context: {main_topic}

    IMPORTANT FRIENDLY TONE GUIDELINES:
    - Sound curious and engaged, not like you're just reporting trends
    - Ask questions that show genuine interest in what others think
    - Use casual, conversational language that invites discussion
    - Be the friend who spots cool trends and wants to talk about them
    - Avoid sounding like a trend-chasing bot or marketer
    - DO NOT use any markdown formatting (no *, _, ~, etc.)
    - DO NOT start with greetings like "Hey friends" or "Hello everyone"

    Return ONLY the post text (without hashtags).
    """
    
    post_text = generate_ai_content(prompt, trends, 'trending', main_topic)
    
    # Add conversation starter
    post_text = add_conversation_starter(post_text, main_topic)
    
    return post_text, None

def generate_trend_based_opinion_poll(trends):
    """Generate opinion poll post based on trending topics - FRIENDLY VERSION"""
    if not trends:
        return create_opinion_fallback()
    
    # Select a trending topic for the poll (avoid AI prediction topics)
    filtered_trends = [t for t in trends if not any(ai_word in t.lower() for ai_word in 
                      ['ai predict', 'ai knows', 'ai getting', 'ai will'])]
    
    if not filtered_trends:
        filtered_trends = trends
    
    poll_topic = random.choice(filtered_trends[:5])
    
    # Special handling for Saturday
    day_name = datetime.now().strftime("%A").lower()
    if day_name == "saturday":
        poll_types = [
            f"#ScreenshotSaturday question! For {poll_topic}, what's your weekend focus? 🎮\nA: Visual polish & screenshots\nB: Core gameplay mechanics\nC: Level design & environments\nD: Character art & animation\n\nShare your progress below! 👇",
            f"Happy #ScreenshotSaturday! When working on {poll_topic}, you're probably focusing on:\nA: Beautiful visuals & art 🎨\nB: Smooth gameplay & controls 🕹️\nC: Engaging story & characters 📖\nD: Performance & optimization ⚡\n\nWhat's your Saturday vibe? Let me know! 💫"
        ]
    else:
        poll_types = [
            f"Quick game dev question! For {poll_topic}, what's your approach? 🎮\nA: Focus on innovation & new ideas\nB: Polish existing ideas to perfection\nC: Community-driven development\nD: Solo creative vision\n\nWhat's your style? Tell me below! 👇",
            f"Strategy question about {poll_topic}: 💡\nA: Build fast & iterate quickly\nB: Plan thoroughly first\nC: User feedback driven\nD: Vision-led development\n\nYour preferred approach? Would love to know! 💭",
            f"Indie dev crew! With {poll_topic}, what's your priority? ⚡\nA: Unique mechanics that stand out\nB: Killer visual style & art\nC: Compelling story/narrative\nD: Rock-solid performance\n\nWhat comes first for you? Share your thoughts! 🚀"
        ]
    
    post_text = random.choice(poll_types)
    hashtags = generate_hashtags(poll_topic, 'poll')
    post_text += f" {hashtags}"
    
    print(f"✅ Friendly opinion poll created ({len(post_text)} chars)")
    return post_text

def generate_ai_content(prompt, content, content_type, main_topic, max_retries=2):
    """Generate content using AI with quality checks and retries"""
    for attempt in range(max_retries + 1):
        try:
            print(f"🎭 Generating {content_type} post (attempt {attempt + 1})...")
            
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
                    
                    # Remove any Markdown formatting
                    post_text = remove_markdown_formatting(post_text)
                    
                    # Add AI-generated hashtags for all post types
                    hashtags = generate_hashtags(main_topic, content_type)
                    post_text += f" {hashtags}"
                    
                    post_text = remove_ai_indicators(post_text)
                    
                    # Quality check the post
                    is_approved, reason = quality_check_post(post_text, main_topic, content_type)
                    
                    if is_approved:
                        # Final length check and truncation if needed
                        if len(post_text) > 280:
                            post_text = post_text[:277] + "..."
                        
                        print(f"✅ {content_type.title()} post created ({len(post_text)} chars)")
                        return post_text
                    else:
                        print(f"❌ Post rejected: {reason}")
                        if attempt < max_retries:
                            print("🔄 Retrying with different approach...")
                            continue
                        else:
                            print("❌ Max retries reached, using fallback")
                            return create_fallback_post(content_type)
            else:
                print(f"❌ AI generation error: {response.text}")
                
        except Exception as e:
            print(f"❌ {content_type} generation error: {e}")
            if attempt < max_retries:
                print("🔄 Retrying...")
                continue
    
    return create_fallback_post(content_type)

def remove_ai_indicators(text):
    """Remove any phrases that sound AI-generated"""
    ai_phrases = [
        "as an AI", "according to AI", "AI-generated", "language model",
        "based on the provided", "in this content", "the writer",
        "this analysis", "the author", "in this piece", "according to the",
        "as a large language model", "I am designed to", "my purpose is to"
    ]
    
    for phrase in ai_phrases:
        text = text.replace(phrase, "")
        text = text.replace(phrase.title(), "")
    
    return ' '.join(text.split())

def create_fallback_post(content_type):
    """Create friendly fallback posts with seasonal awareness - NO GREETINGS"""
    emojis = ["🚀", "🤔", "💡", "🎯", "🔥", "👀", "💭", "⚡", "🌟", "✨", "🎮", "💻"]
    
    # Check for special occasions
    occasion = is_special_occasion()
    day_name = datetime.now().strftime("%A").lower()
    
    if occasion == "christmas":
        if content_type == 'tech':
            fallbacks = [
                f"🎄 Christmas coding sessions just hit different! Perfect time for some cozy dev work with holiday vibes 🎁 What tech projects are you tinkering with?",
                f"🎁 The best tech innovations feel like pure magic during the holidays! Wishing everyone inspiration and great ideas this season 🎅"
            ]
        else:
            fallbacks = [
                f"🎄 Holiday gaming sessions are the best! Perfect day for some cozy gaming or creative dev work 🎮 What's on your playlist today?",
                f"🎁 There's something magical about games that bring people together during the holidays! Wishing everyone warm gaming sessions ❄️"
            ]
    elif day_name == "saturday":
        if content_type == 'game dev':
            fallbacks = [
                f"#ScreenshotSaturday progress! Working on some exciting game mechanics today 🎮 Love seeing everyone's creative projects - what are you building this weekend?",
                f"Saturday game dev sessions are the best! Polishing up some level design and loving the community energy 🎨 What creative projects are you excited about?"
            ]
        else:
            fallbacks = [
                f"Weekend coding sessions just hit different ☕ Perfect time for experimental projects and learning new tech - what are you building today?",
                f"Saturday tech experiments are my favorite! Trying out some new frameworks and loving the creative energy 🚀 What's on your weekend dev list?"
            ]
    else:
        if content_type == 'tech':
            fallbacks = [
                f"Noticed something interesting in the tech space today {random.choice(emojis)} The way we're approaching development is really evolving - anyone else seeing this shift?",
                f"The future of tech development looks wild {random.choice(emojis)} Some of these new approaches could really change how we build things together"
            ]
        elif content_type == 'game dev':
            fallbacks = [
                f"Game dev thought of the day {random.choice(emojis)} The balance between innovation and polish is tougher than ever - where do you lean with your projects?",
                f"Watching player expectations evolve is fascinating {random.choice(emojis)} It's amazing what matters to gamers now vs a few years ago - anyone else tracking this?"
            ]
        else:
            fallbacks = [
                f"Interesting patterns in what's trending lately {random.choice(emojis)} Says a lot about where things might be heading together",
                f"Noticed some shifts in the industry conversation that feel pretty significant {random.choice(emojis)} Some themes keep coming up that could really shape where we're headed"
            ]
    
    post_text = random.choice(fallbacks)
    hashtags = generate_hashtags("industry trends", content_type)
    post_text += f" {hashtags}"
    
    # Add contextual CTA
    post_text = add_conversation_starter(post_text, "industry trends")
    
    # Ensure we don't exceed character limit
    if len(post_text) > 280:
        post_text = post_text[:277] + "..."
    
    return post_text

def create_opinion_fallback(topic=None):
    """Create fallback opinion poll"""
    if not topic:
        topic = "industry strategy"
    
    day_name = datetime.now().strftime("%A").lower()
    
    if day_name == "saturday":
        poll_types = [
            f"#ScreenshotSaturday poll! What's your weekend focus? 🎮\nA: Visual polish & screenshots\nB: Gameplay mechanics\nC: Level design\nD: Bug fixing\n\nShare your progress below! 👇 {generate_hashtags('ScreenshotSaturday', 'poll')}",
            f"Saturday game dev question! Working on:\nA: Art & visuals 🖌️\nB: Code & systems 💻\nC: Design & levels 📐\nD: Sound & music 🎵\n\nWhat's your focus today? 💫 {generate_hashtags('GameDev', 'poll')}"
        ]
    else:
        poll_types = [
            f"Game dev priority right now? 🎮\nA: Innovation & new ideas\nB: Polish & refinement\nC: Community building\nD: Business sustainability\n\nWhat's your current focus? 👇 {generate_hashtags('GameDev', 'poll')}",
            f"Tech development approach? 💻\nA: Move fast & break things\nB: Build slow & solid\nC: User-driven iteration\nD: Vision-led creation\n\nYour preferred style? ⬇️ {generate_hashtags('Tech', 'poll')}"
        ]
    
    post_text = random.choice(poll_types)
    
    # Ensure we don't exceed character limit
    if len(post_text) > 280:
        post_text = post_text[:277] + "..."
    
    return post_text

# ================================
# POST TYPE SELECTOR - UPDATED FOR MORE TECH/GAME DEV
# ================================

def select_post_type():
    """Randomly select post type with weighted probability - more tech/game dev"""
    post_types = [
        ('tech', 0.30),       # 30% tech posts
        ('game_dev', 0.30),   # 30% game dev posts  
        ('trending', 0.25),   # 25% trending topics
        ('opinion_poll', 0.15) # 15% opinion polls
    ]
    
    choices, weights = zip(*post_types)
    return random.choices(choices, weights=weights)[0]

# ================================
# MAIN EXECUTION
# ================================

def main():
    print("🐦 Friendly Content Creator - Twitter Edition")
    print("=" * 50)
    print("🌟 BRIGHT & FRIENDLY TONE • CONVERSATIONAL STYLE")
    print("🎮 #ScreenshotSaturday • COMMUNITY FOCUS")
    print("🤖 USING GEMINI 2.0 FLASH")
    print("=" * 50)
    
    # Show current context
    occasion = is_special_occasion()
    season = get_season()
    day_name = datetime.now().strftime("%A")
    
    print(f"📅 Today: {day_name}")
    print(f"🌤️  Season: {season.title()}")
    if occasion:
        print(f"🎉 Special Occasion: {occasion.replace('_', ' ').title()}")
    print("")
    
    # Validate configuration
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API secrets")
        return
        
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY secret")
        return
    
    print(f"✅ Twitter API configured")
    print(f"✅ Gemini 2.0 Flash configured")
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
    
    print(f"📝 Final Post: {post_text}")
    print(f"📏 Character count: {len(post_text)}")
    print(f"🖼️ Image available: {'Yes' if image_url else 'No'}")
    
    # Post to Twitter
    print("\n🚀 Sharing with friends...")
    success = post_to_twitter(
        post_text, 
        TWITTER_API_KEY, 
        TWITTER_API_SECRET, 
        TWITTER_ACCESS_TOKEN, 
        TWITTER_ACCESS_TOKEN_SECRET,
        image_url
    )
    
    if success:
        print("\n✅ Successfully shared with the community!")
        print(f"🎯 Post type: {post_type.replace('_', ' ').title()}")
        print(f"🖼️ Image included: {'Yes' if image_url else 'No'}")
        print(f"📅 Seasonal context: {season.title()}")
        if occasion:
            print(f"🎉 Holiday vibes: {occasion.replace('_', ' ').title()}")
        if day_name.lower() == 'saturday':
            print("🖼️ #ScreenshotSaturday ready!")
        print("💬 Contextual CTA: Included!")
    else:
        print("\n❌ Failed to share.")

if __name__ == "__main__":
    main()