import os
import random
import feedparser
import requests
import textwrap
import re
import tweepy
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

# =====================
# CONFIGURATION
# =====================
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Reddit RSS feeds (life, work, relationships, internet behavior)
RSS_FEEDS = [
    "https://www.reddit.com/r/funny/.rss",
    "https://www.reddit.com/r/AskReddit/.rss",
    "https://www.reddit.com/r/tifu/.rss",
    "https://www.reddit.com/r/relationships/.rss",
    "https://www.reddit.com/r/mildlyinfuriating/.rss",
]

# Maximum hashtags
MAX_HASHTAGS = 3

# =====================
# TWITTER FUNCTIONS
# =====================
def post_to_twitter(text, image, hashtags):
    """Post image with caption including hashtags"""
    try:
        auth_v1 = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth_v1.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        api_v1 = tweepy.API(auth_v1)
        
        # Save image temporarily
        temp_file = "/tmp/tweet_image.jpg"
        image.save(temp_file, format="JPEG")

        # Upload media
        media = api_v1.media_upload(temp_file)
        caption = " ".join(hashtags)
        client_v2 = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        client_v2.create_tweet(text=caption, media_ids=[media.media_id_string])
        print("✅ Tweet posted successfully!")
        return True
    except Exception as e:
        print(f"❌ Twitter post error: {e}")
        return False

# =====================
# RSS FUNCTIONS
# =====================
def parse_rss_feeds():
    """Get all recent entries from Reddit RSS feeds"""
    entries = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                entries.append({
                    "title": entry.title,
                    "summary": entry.get("summary", ""),
                    "link": entry.link
                })
        except Exception as e:
            print(f"Error parsing RSS {feed_url}: {e}")
    return entries

# =====================
# AI CONTENT FUNCTIONS
# =====================
def generate_tweet_text(entry):
    """Generate standalone tweet text from RSS entry"""
    prompt = (
        f"Write a funny, observational, relatable tweet based on this content.\n\n"
        f"Content: {entry['title']}\n"
        f"Details: {entry.get('summary','')}\n\n"
        f"Requirements:\n"
        "- Must be standalone (self-explanatory)\n"
        "- Include 1-2 emojis\n"
        "- Short and readable\n"
        "- Observational, humorous tone\n"
        "- No hashtags in the text\n"
    )
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"\*\*|\*|__|_", "", text)
        if not text or len(text) < 20:
            return None
        return text
    except Exception as e:
        print(f"AI generation failed: {e}")
        return None

# =====================
# IMAGE FUNCTIONS
# =====================
def create_text_image(text, width=800, padding=40):
    """Create image with random background color and tweet text"""
    bg_color = tuple(random.randint(100,255) for _ in range(3))
    img = Image.new("RGB", (width, 1), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Font
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    # Wrap text
    lines = []
    for line in text.split("\n"):
        lines.extend(textwrap.wrap(line, width=30))

    # Calculate total height
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=font)
        line_heights.append(bbox[3]-bbox[1])
    total_height = sum(line_heights) + padding*2 + (len(lines)-1)*10

    # Resize image
    img = img.resize((width, total_height))
    draw = ImageDraw.Draw(img)

    # Draw text centered
    y = padding
    for line, lh in zip(lines, line_heights):
        bbox = draw.textbbox((0,0), line, font=font)
        w = bbox[2]-bbox[0]
        x = (width - w)//2
        draw.text((x, y), line, font=font, fill=(0,0,0))
        y += lh + 10

    return img

# =====================
# HASHTAG FUNCTIONS
# =====================
def get_random_hashtags():
    """Pick some fun generic trending hashtags (or placeholders)"""
    sample_hashtags = [
        "#Life", "#Work", "#Relationships", "#InternetLife",
        "#Humor", "#Funny", "#Observations", "#DailyLife",
        "#Relatable", "#ModernLife"
    ]
    return random.sample(sample_hashtags, k=MAX_HASHTAGS)

# =====================
# MAIN
# =====================
def main():
    print("🐦 Reddit Content - Twitter Edition")
    print("💬 LIFE / WORK / RELATIONSHIPS / INTERNET BEHAVIOR POSTS")
    print("🌟 OBSERVATIONAL & HUMOROUS TONE")
    print("🤖 USING GEMINI 2.5 FLASH")
    print("="*50)

    entries = parse_rss_feeds()
    if not entries:
        print("❌ No RSS entries found.")
        return

    entry = random.choice(entries)
    text = generate_tweet_text(entry)
    if not text:
        print("❌ AI failed to generate a valid tweet. Skipping.")
        return

    print("Generated text:\n", text)
    hashtags = get_random_hashtags()
    print("\nHashtags:\n", " ".join(hashtags))

    # Create image with text
    image = create_text_image(text)

    # Post to Twitter
    success = post_to_twitter(text, image, hashtags)
    if not success:
        print("❌ Failed to post.")

if __name__ == "__main__":
    main()