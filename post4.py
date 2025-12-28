import os
import google.generativeai as genai
import random
import feedparser
import re
import tweepy
from PIL import Image, ImageDraw, ImageFont
import io

# Configuration
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Reddit RSS feeds for niche
REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/AskReddit/.rss",
    "https://www.reddit.com/r/relationships/.rss",
    "https://www.reddit.com/r/antiwork/.rss",
    "https://www.reddit.com/r/selfimprovement/.rss",
    "https://www.reddit.com/r/technology/.rss"
]

posted_links = set()

# =============================
# TWITTER API
# =============================

def post_image_to_twitter(image_bytes, caption, api_key, api_secret, access_token, access_token_secret):
    """Post tweet with image and caption"""
    try:
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        # Upload media
        media = client_v2.upload_media(filename="tweet.png", file=image_bytes)
        response = client_v2.create_tweet(text=caption, media_ids=[media.media_id])
        return bool(response and response.data)
    except Exception as e:
        print(f"Twitter post error: {e}")
        return False

# =============================
# HELPERS
# =============================

def contains_political_content(text):
    POLITICAL_KEYWORDS = [
        'trump','biden','president','election','government','policy',
        'tax','war','political','democrat','republican','vote'
    ]
    return any(k in text.lower() for k in POLITICAL_KEYWORDS) if text else False

# =============================
# PARSE REDDIT RSS
# =============================

def parse_reddit_rss():
    entries = []
    for url in REDDIT_RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.link in posted_links:
                    continue
                if contains_political_content(entry.title) or contains_political_content(entry.get('summary','')):
                    continue
                entries.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary','')
                })
        except Exception as e:
            print(f"RSS error {url}: {e}")
    return entries

# =============================
# CREATE IMAGE
# =============================

def create_text_image(text, width=800, height=600):
    # Random background color
    bg_color = tuple(random.randint(100, 255) for _ in range(3))
    image = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)

    # Use default PIL font
    font = ImageFont.load_default()

    # Wrap text
    lines = []
    max_chars_per_line = 40
    for paragraph in text.split('\n'):
        paragraph = paragraph.strip()
        while len(paragraph) > 0:
            lines.append(paragraph[:max_chars_per_line])
            paragraph = paragraph[max_chars_per_line:]
    
    # Draw text
    y_text = 20
    for line in lines:
        draw.text((20, y_text), line, fill=(0,0,0), font=font)
        y_text += font.getsize(line)[1] + 5
    
    # Save to bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# =============================
# GENERATE TWEET
# =============================

def generate_engaging_post():
    entries = parse_reddit_rss()
    if not entries:
        print("No valid RSS entries found.")
        return None, None

    entry = random.choice(entries)
    posted_links.add(entry['link'])
    
    prompt = (
        f"Create ONE standalone, funny/observational tweet about this online discussion:\n\n"
        f"Title: {entry['title']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"Requirements:\n"
        f"- Funny/observational about modern life, work, relationships or internet behavior\n"
        f"- Include 3 hashtags at the end of the tweet\n"
        f"- Use line breaks and emojis for readability\n"
        f"- Must make sense standalone\n"
        f"- Max 250 characters\n"
        f"- Do NOT mention Reddit or sources"
    )
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'\*\*|\*|__|_', '', text).strip()
        
        # Extract hashtags from AI-generated text (assume last line has them)
        lines = text.split("\n")
        hashtags = lines[-1] if lines[-1].startswith("#") else ""
        tweet_text = "\n".join(lines[:-1]) if hashtags else text
        
        return tweet_text, hashtags
    except Exception as e:
        print(f"AI generation failed: {e}")
        return None, None

# =============================
# MAIN
# =============================

def main():
    print("🐦 Reddit Content - Twitter Edition")
    
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        return
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return
    
    post_text, hashtags = generate_engaging_post()
    if not post_text:
        print("❌ AI failed to generate a tweet. Skipping post.")
        return
    
    print(f"Generated Tweet Text:\n{post_text}")
    print(f"Hashtags for Caption:\n{hashtags}\n")
    
    # Create image with text only (no hashtags)
    img_bytes = create_text_image(post_text)
    
    # Post image with hashtags as caption
    success = post_image_to_twitter(
        img_bytes,
        caption=hashtags,
        api_key=TWITTER_API_KEY,
        api_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    
    print("✅ Posted!" if success else "❌ Failed to post.")

if __name__ == "__main__":
    main()