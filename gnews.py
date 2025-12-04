import os
import requests
import feedparser
from datetime import datetime, timezone
from dotenv import load_dotenv
import re
import json
import tweepy

load_dotenv()

# Twitter API credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gaming RSS feeds
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

# Gaming hashtags - FIXED: removed extra closing brace
GAMING_HASHTAGS = {
    'playstation': ['#PlayStation', '#PS5', '#PS4', '#PlayStation5', '#Sony', '#Exclusive'],
    'xbox': ['#Xbox', '#XboxSeriesX', '#XboxSeriesS', '#Microsoft', '#GamePass'],
    'nintendo': ['#Nintendo', '#Switch', '#NintendoSwitch', '#Zelda', '#Mario'],
    'pc': ['#PCGaming', '#Steam', '#PC', '#EpicGames', '#GOG'],
    'mobile': ['#MobileGaming', '#iOS', '#Android', '#AppStore', '#PlayStore'],
    'esports': ['#Esports', '#Gaming', '#Competitive', '#Tournament', '#ProGamer'],
    'vr': ['#VR', '#VirtualReality', '#Oculus', '#MetaQuest', '#VRGaming'],
    'indie': ['#IndieGame', '#IndieDev', '#GameDev', '#IndieGaming'],
    'release': ['#NewRelease', '#GameLaunch', '#ComingSoon', '#ReleaseDate'],
    'update': ['#Update', '#Patch', '#GameUpdate', '#BugFix'],
    'trailer': ['#Trailer', '#Gameplay', '#Reveal', '#Announcement'],
    'general': ['#GamingNews', '#VideoGames', '#Gamer', '#GamingCommunity', '#WhatsNew']
}

def post_to_twitter(content, image_url=None):
    """Post content to Twitter"""
    try:
        print("🐦 Posting to Twitter...")
        
        # Twitter character limit
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        # Initialize Twitter API
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        
        media_ids = []
        
        # Upload image if available
        if image_url:
            try:
                auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
                auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
                api = tweepy.API(auth)
                
                # Download image
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    with open('/tmp/temp_image.jpg', 'wb') as f:
                        f.write(response.content)
                    
                    # Upload to Twitter
                    media = api.media_upload('/tmp/temp_image.jpg')
                    media_ids.append(media.media_id_string)
                    print(f"✅ Image uploaded: {image_url}")
            except Exception as e:
                print(f"⚠️ Failed to upload image: {e}")
        
        # Post tweet
        if media_ids:
            response = client.create_tweet(text=content, media_ids=media_ids)
        else:
            response = client.create_tweet(text=content)
        
        if response and response.data:
            print(f"✅ Tweet posted successfully! ID: {response.data['id']}")
            return True
        else:
            print("❌ Tweet failed")
            return False
            
    except Exception as e:
        print(f"❌ Twitter error: {e}")
        return False

def get_gaming_news():
    """Fetch gaming news"""
    all_entries = []
    
    for rss_url in GAMING_RSS_FEEDS:
        try:
            print(f"📰 Fetching from: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            if feed.entries:
                for entry in feed.entries:
                    # Skip if too old
                    if not hasattr(entry, 'published_parsed'):
                        continue
                    
                    entry.source = rss_url.split('//')[1].split('/')[0]
                    all_entries.append(entry)
                    
        except Exception as e:
            print(f"❌ Error: {rss_url}: {e}")
    
    # Sort by date, newest first
    all_entries.sort(key=lambda x: getattr(x, 'published_parsed', datetime(1970, 1, 1).timetuple()), reverse=True)
    return all_entries[:5]

def is_recent(entry, hours=48):
    """Check if entry is recent"""
    try:
        if hasattr(entry, 'published_parsed'):
            published = datetime(*entry.published_parsed[:6])
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            diff = now - published
            return diff.total_seconds() <= hours * 3600
    except:
        return False
    return False

def extract_image(entry):
    """Extract first image from entry"""
    # Check media content
    if hasattr(entry, 'media_content'):
        for media in entry.media_content[:3]:
            if hasattr(media, 'url'):
                return media.url
            elif isinstance(media, dict) and 'url' in media:
                return media['url']
    
    # Check enclosures
    if hasattr(entry, 'enclosures'):
        for enc in entry.enclosures[:3]:
            if hasattr(enc, 'href'):
                return enc.href
            elif isinstance(enc, dict) and 'href' in enc:
                return enc['href']
    
    # Check summary for images
    if hasattr(entry, 'summary'):
        matches = re.findall(r'<img[^>]+src="([^">]+)"', entry.summary)
        if matches:
            return matches[0]
    
    return None

def get_gaming_hashtags(title, description):
    """Get relevant hashtags"""
    text = (title + " " + description).lower()
    hashtags = []
    
    # Check categories
    if any(word in text for word in ['playstation', 'ps5', 'ps4', 'sony']):
        hashtags.extend(['#PlayStation', '#PS5'])
    elif any(word in text for word in ['xbox', 'microsoft', 'gamepass']):
        hashtags.extend(['#Xbox', '#GamePass'])
    elif any(word in text for word in ['nintendo', 'switch', 'zelda', 'mario']):
        hashtags.extend(['#Nintendo', '#Switch'])
    elif any(word in text for word in ['pc', 'steam', 'epic', 'computer']):
        hashtags.extend(['#PCGaming', '#Steam'])
    elif any(word in text for word in ['vr', 'virtual', 'oculus']):
        hashtags.extend(['#VR', '#VRGaming'])
    else:
        hashtags.extend(['#GamingNews', '#VideoGames'])
    
    # Add general gaming tags
    hashtags.append('#Gamer')
    
    return ' '.join(hashtags[:4])

def generate_tweet_with_gemini(title, description):
    """Generate tweet text using Gemini"""
    try:
        prompt = f"""Create an engaging gaming news tweet about: "{title}"

Description: {description[:200]}

Requirements:
1. Keep it under 200 characters
2. Add 1-2 relevant emojis
3. Make it exciting and shareable
4. End with a question to engage followers
5. No hashtags (they'll be added separately)

Example format: "Breaking: New game announcement! 🎮 Looks amazing! What do you think? 👇"

Now create the tweet:"""
        
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    
    except Exception as e:
        print(f"❌ Gemini error: {e}")
    
    # Fallback tweet
    return f"🎮 {title[:100]}... What's your take on this? 👇"

def main():
    print("=" * 50)
    print("🎮 GAMING NEWS BOT")
    print("=" * 50)
    
    # Validate API keys
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API keys")
        return
    
    if not GEMINI_API_KEY:
        print("❌ Missing Gemini API key")
        return
    
    print("✅ API keys loaded")
    
    # Get news
    entries = get_gaming_news()
    recent_entries = [e for e in entries if is_recent(e)]
    
    if not recent_entries:
        print("❌ No recent news found")
        # Fallback tweet
        fallback = "🎮 No major gaming news today! What game are you currently playing? Share below! 👇 #Gaming #Gamer"
        post_to_twitter(fallback)
        return
    
    # Take first recent entry
    entry = recent_entries[0]
    title = getattr(entry, 'title', 'Gaming News Update')
    description = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
    
    # Extract image
    image_url = extract_image(entry)
    
    # Generate tweet text
    tweet_text = generate_tweet_with_gemini(title, description)
    
    # Add hashtags
    hashtags = get_gaming_hashtags(title, description)
    final_tweet = f"{tweet_text} {hashtags}"
    
    # Ensure within limit
    if len(final_tweet) > 280:
        final_tweet = final_tweet[:277] + "..."
    
    print(f"\n📝 Tweet: {final_tweet}")
    print(f"📏 Length: {len(final_tweet)} chars")
    print(f"🖼️ Image: {'Yes' if image_url else 'No'}")
    
    # Post to Twitter
    success = post_to_twitter(final_tweet, image_url)
    
    if success:
        print("\n✅ Bot completed successfully!")
    else:
        print("\n❌ Bot failed")

if __name__ == '__main__':
    main()