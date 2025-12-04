# gaming_news_post_twitter.py
import os
import requests
import feedparser
from datetime import datetime
from dotenv import load_dotenv
import re
from io import BytesIO
import json
import tweepy
import random

load_dotenv()

# Twitter API credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI = os.getenv("GEMINI_API_KEY")

# Updated RSS feeds focused on gaming news
GAMING_RSS_FEEDS = [
    "https://www.ign.com/feeds/news",
    "https://www.gamespot.com/feeds/news",
    "https://www.polygon.com/rss/index.xml",
    "https://feeds.feedburner.com/Kotaku",
    "https://www.pcgamer.com/rss/",
    "https://www.eurogamer.net/feed",
    "https://www.gameinformer.com/news.xml",
    "https://www.rockpapershotgun.com/feed",
    "https://www.destructoid.com/feed/",
    "https://www.vg247.com/feed"
]

# Gaming hashtag mapping
GAMING_HASHTAGS = {
    'playstation': ['#PlayStation', '#PS5', '#PS4', '#PlayStation5', '#Sony', '#Exclusive'],
    'xbox': ['#Xbox', '#XboxSeriesX', '#XboxSeriesS', '#Microsoft', '#GamePass'],
    'nintendo': ['#Nintendo', '#Switch', '#NintendoSwitch', '#Zelda', '#Mario'],
    'pc': ['#PCGaming', #Steam', '#PC', '#EpicGames', '#GOG'],
    'mobile': ['#MobileGaming', '#iOS', '#Android', '#AppStore', '#PlayStore'],
    'esports': ['#Esports', '#Gaming', '#Competitive', '#Tournament', '#ProGamer'],
    'vr': ['#VR', '#VirtualReality', '#Oculus', '#MetaQuest', '#VRGaming'],
    'indie': ['#IndieGame', '#IndieDev', '#GameDev', '#IndieGaming'],
    'release': ['#NewRelease', '#GameLaunch', '#ComingSoon', '#ReleaseDate'],
    'update': ['#Update', '#Patch', '#GameUpdate', '#BugFix'],
    'trailer': ['#Trailer', '#Gameplay', '#Reveal', '#Announcement'],
    'general': ['#GamingNews', '#VideoGames', '#Gamer', '#GamingCommunity', '#WhatsNew']
}

def post_to_twitter(content, image_urls=None):
    """Post content to Twitter/X with optional images"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Twitter character limit
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        media_ids = []
        
        # Upload images if available (Twitter supports up to 4 images)
        if image_urls and len(image_urls) > 0:
            print(f"📤 Uploading {min(len(image_urls), 4)} images for tweet...")
            
            # Twitter API v1.1 for media upload
            auth_v1 = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
            auth_v1.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
            api_v1 = tweepy.API(auth_v1)
            
            for img_url in image_urls[:4]:  # Max 4 images per tweet
                try:
                    # Clean URL
                    clean_url = img_url.split('?')[0].split('&#')[0]
                    
                    # Download image
                    response = requests.get(clean_url, timeout=15, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    response.raise_for_status()
                    
                    # Save temporarily
                    temp_file = "/tmp/tweet_image.jpg"
                    with open(temp_file, "wb") as f:
                        f.write(response.content)
                    
                    # Check file size
                    file_size = os.path.getsize(temp_file)
                    if file_size > 5 * 1024 * 1024:  # 5MB limit
                        print(f"⚠️ Image too large ({file_size} bytes), skipping...")
                        continue
                    
                    # Upload media
                    media = api_v1.media_upload(filename=temp_file)
                    media_ids.append(media.media_id_string)
                    print(f"✅ Image uploaded: {media.media_id_string}")
                    
                    # Clean up
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        
                except Exception as e:
                    print(f"⚠️ Failed to upload image {img_url}: {e}")
        
        # Twitter API v2 for posting
        client_v2 = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        
        # Post tweet
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

def extract_gaming_keywords(text):
    """Extract gaming-related keywords for hashtags"""
    gaming_terms = {
        'playstation': ['playstation', 'ps5', 'ps4', 'sony'],
        'xbox': ['xbox', 'microsoft', 'gamepass'],
        'nintendo': ['nintendo', 'switch', 'zelda', 'mario'],
        'pc': ['pc', 'steam', 'epic', 'gog', 'computer'],
        'vr': ['vr', 'virtual', 'oculus', 'quest'],
        'esports': ['esports', 'tournament', 'competitive'],
        'indie': ['indie', 'indiegame', 'gamejam'],
        'release': ['release', 'launch', 'available'],
        'update': ['update', 'patch', 'fix', 'bug'],
        'trailer': ['trailer', 'gameplay', 'reveal']
    }
    
    detected_keywords = []
    text_lower = text.lower()
    
    for category, terms in gaming_terms.items():
        if any(term in text_lower for term in terms):
            detected_keywords.append(category)
    
    # Always include general gaming hashtags
    if not detected_keywords:
        detected_keywords.append('general')
    
    return detected_keywords[:3]  # Max 3 categories

def get_gaming_hashtags(keywords):
    """Get relevant hashtags for gaming topics"""
    hashtags = []
    
    for keyword in keywords:
        if keyword in GAMING_HASHTAGS:
            hashtags.extend(GAMING_HASHTAGS[keyword][:2])  # Take top 2 from each category
    
    # Ensure we have a good mix without duplicates
    unique_hashtags = list(set(hashtags))
    
    # Add some general gaming hashtags
    general_hashtags = ['#GamingNews', '#VideoGames', '#Gamer']
    for hashtag in general_hashtags:
        if hashtag not in unique_hashtags and len(unique_hashtags) < 5:  # Twitter limit
            unique_hashtags.append(hashtag)
    
    return ' '.join(unique_hashtags[:5])

def get_gaming_news():
    """Fetch gaming news from multiple RSS feeds and return combined entries"""
    all_entries = []
    
    for rss_url in GAMING_RSS_FEEDS:
        try:
            print(f"🎮 Fetching gaming news from: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            if feed.entries:
                for entry in feed.entries:
                    # Filter out non-gaming content
                    title = getattr(entry, 'title', '').lower()
                    summary = getattr(entry, 'summary', '').lower()
                    description = getattr(entry, 'description', '').lower()
                    
                    gaming_keywords = ['game', 'gaming', 'playstation', 'xbox', 'nintendo', 'pc', 'steam', 
                                     'release', 'trailer', 'update', 'patch', 'review', 'esports', 'console',
                                     'switch', 'ps5', 'xbox series', 'vr', 'virtual reality']
                    
                    if not any(keyword in title + summary + description for keyword in gaming_keywords):
                        continue
                    
                    entry.source = rss_url.split('//')[1].split('/')[0]
                    all_entries.append(entry)
                print(f"✅ Found {len(feed.entries)} entries from {rss_url}")
            else:
                print(f"⚠️ No entries found in: {rss_url}")
                
        except Exception as e:
            print(f"❌ Error parsing RSS feed {rss_url}: {e}")
    
    all_entries.sort(key=lambda x: getattr(x, 'published_parsed', (0, 0, 0, 0, 0, 0, 0, 0, 0)), reverse=True)
    
    return all_entries[:10]

def clean_twitter_text(text):
    """Clean text for Twitter posting"""
    # Remove markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'[`~]', '', text)
    
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def is_recent_entry(entry, hours_threshold=48):
    """Check if the entry was published within the last specified hours"""
    try:
        if hasattr(entry, 'published_parsed'):
            published_time = datetime(*entry.published_parsed[:6])
            time_diff = datetime.utcnow() - published_time
            return time_diff.total_seconds() <= (hours_threshold * 3600)
    except:
        pass
    return False

def extract_images_from_entry(entry):
    """Extract all images from RSS entry"""
    images = []
    
    # Check media content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if hasattr(media, 'url') and hasattr(media, 'type') and media.get('type', '').startswith('image/'):
                images.append(media.url)
            elif isinstance(media, dict) and 'url' in media and media.get('type', '').startswith('image/'):
                images.append(media['url'])
    
    # Check enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if hasattr(enc, 'href') and hasattr(enc, 'type') and enc.get('type', '').startswith('image/'):
                images.append(enc.href)
            elif isinstance(enc, dict) and 'href' in enc and enc.get('type', '').startswith('image/'):
                images.append(enc['href'])
    
    # Parse HTML content for images
    if hasattr(entry, 'summary'):
        try:
            matches = re.findall(r'<img[^>]+src="([^">]+)"', entry.summary)
            images.extend(matches)
        except:
            pass
    
    if hasattr(entry, 'description'):
        try:
            matches = re.findall(r'<img[^>]+src="([^">]+)"', entry.description)
            images.extend(matches)
        except:
            pass
    
    # Remove duplicates and invalid URLs
    unique_images = []
    for img in images:
        if img and isinstance(img, str) and img.startswith(('http://', 'https://')) and img not in unique_images:
            unique_images.append(img)
    
    return unique_images

def generate_gaming_cta():
    """Generate gaming-specific call to action"""
    ctas = [
        "What do you think? 👇",
        "Your thoughts? 💭",
        "Excited for this? 🎮",
        "Which game are you waiting for? ⏳",
        "Share your opinion! 💬",
        "Agree or disagree? 🤔"
    ]
    return random.choice(ctas)

def post_gaming_news():
    print("🎮 Fetching latest gaming news for Twitter...")
    
    # Validate Twitter credentials
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        return
    
    if not GEMINI:
        print("❌ Missing GEMINI_API_KEY")
        return
    
    print("✅ Twitter API configured")
    print("✅ Gemini API configured")
    
    try:
        entries = get_gaming_news()
        
        recent_entries = [entry for entry in entries if is_recent_entry(entry)]
        
        if not recent_entries:
            print("❌ No recent gaming news entries found.")
            fallback_post = (
                "🎮 Gaming News Update\n\n"
                "No major gaming news right now! What game are you currently playing? "
                "Share your favorite gaming moment! 👇\n\n"
                "#Gaming #VideoGames #Gamer #GamingCommunity"
            )
            post_to_twitter(fallback_post)
            return
        
        # Select one main entry for the tweet
        main_entry = recent_entries[0]
        title = getattr(main_entry, 'title', 'No Title').strip()
        summary = getattr(main_entry, 'summary', '')
        description = getattr(main_entry, 'description', summary)
        link = getattr(main_entry, 'link', '#').strip()
        
        # Extract images for this entry
        image_urls = extract_images_from_entry(main_entry)[:1]  # Just first image for Twitter
        
        # Extract gaming keywords for hashtags
        content_for_keywords = title + " " + description[:200]
        detected_keywords = extract_gaming_keywords(content_for_keywords)
        gaming_hashtags = get_gaming_hashtags(detected_keywords)
        
        # Generate CTA
        gaming_cta = generate_gaming_cta()
        
        # Create prompt for Gemini (English for Twitter)
        prompt = (
            "Create an engaging Twitter post about this gaming news. Rules:\n"
            "1. Write in conversational English\n"
            "2. Keep it under 200 characters (before hashtags)\n"
            "3. Include 1-2 relevant emojis\n"
            "4. End with this CTA: '" + gaming_cta + "'\n"
            "5. No markdown formatting\n"
            "6. Make it exciting and shareable\n\n"
            "News Title: " + title + "\n"
            "News Details: " + description[:300] + "\n\n"
            "Example format:\n"
            "'Breaking: New Zelda game announced! 🎮✨ Looks amazing! "
            "What do you think? 👇 #Gaming #Nintendo #Zelda'\n\n"
            "Now create the tweet:"
        )
        
        try:
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent",
                params={"key": GEMINI},
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and data["candidates"]:
                    ai_content = data["candidates"][0]["content"]["parts"][0]["text"]
                    cleaned_content = clean_twitter_text(ai_content)
                    
                    # Add hashtags
                    final_post = f"{cleaned_content} {gaming_hashtags}"
                    
                    # Post to Twitter
                    print(f"\n📝 Generated Tweet: {final_post}")
                    print(f"📏 Character count: {len(final_post)}")
                    print(f"🏷️ Hashtags: {gaming_hashtags}")
                    print(f"🖼️ Images: {len(image_urls)}")
                    
                    success = post_to_twitter(final_post, image_urls)
                    
                    if success:
                        print("\n✅ Successfully posted gaming news to Twitter!")
                    else:
                        print("\n❌ Failed to post to Twitter.")
                        
                    return
                else:
                    print(f"❌ No valid candidates in Gemini response")
                    raise Exception("No valid candidates")
            else:
                print(f"❌ Gemini API error: {response.status_code}")
                raise Exception(f"API error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Gemini API exception: {e}")
            raise Exception("Gemini failed")
            
    except Exception as e:
        print(f"❌ Error in post_gaming_news: {e}")
        # Fallback tweet
        fallback_tweets = [
            "🎮 New gaming updates dropping this week! What are you playing right now? Share below! 👇 #Gaming #VideoGames",
            "🔥 Hot gaming news incoming! Stay tuned for updates on your favorite titles. #Gamer #GamingNews",
            "🚀 Exciting developments in the gaming world! Which upcoming release has you most hyped? 💥 #GamingCommunity"
        ]
        fallback_post = random.choice(fallback_tweets)
        post_to_twitter(fallback_post)

def main():
    print("=" * 50)
    print("🎮 GAMING NEWS - TWITTER EDITION")
    print("=" * 50)
    print("📰 Latest gaming news from top sources")
    print("🐦 Optimized for Twitter/X")
    print("🏷️ Gaming-specific hashtags")
    print("🎮 Conversational & engaging")
    print("🤖 Powered by Gemini 2.5 Flash")
    print("=" * 50)
    
    post_gaming_news()

if __name__ == '__main__':
    main()