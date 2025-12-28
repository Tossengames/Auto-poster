import os
import random
import re
import textwrap
from io import BytesIO
import feedparser
import tweepy

# Auto-install Pillow if missing
import subprocess
import sys
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

import google.generativeai as genai

# =============================
# CONFIG
# =============================
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/AskReddit/.rss",
    "https://www.reddit.com/r/relationships/.rss",
    "https://www.reddit.com/r/antiwork/.rss",
    "https://www.reddit.com/r/selfimprovement/.rss",
    "https://www.reddit.com/r/technology/.rss"
]

posted_links = set()

# =============================
# INIT AI
# =============================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# =============================
# HELPERS
# =============================

def contains_political_content(text):
    POLITICAL_KEYWORDS = ['trump','biden','president','election','government','policy','tax','war','political','democrat','republican','vote']
    return any(k in text.lower() for k in POLITICAL_KEYWORDS) if text else False

def extract_hashtags_from_text(text, max_tags=3):
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    common = sorted(set(words), key=lambda w: -words.count(w))
    tags = []
    for w in common:
        tag = "#" + w.capitalize()
        if tag not in tags:
            tags.append(tag)
        if len(tags) == max_tags:
            break
    return " ".join(tags)

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
# AI POST GENERATION
# =============================

def generate_engaging_post():
    entries = parse_reddit_rss()
    if not entries:
        print("No valid RSS entries found.")
        return None, None, None
    
    entry = random.choice(entries)
    posted_links.add(entry['link'])
    
    hashtags = extract_hashtags_from_text(entry['title'] + " " + entry['summary'])
    
    prompt = (
        f"Create ONE standalone, easy-to-read tweet about this online discussion:\n\n"
        f"Title: {entry['title']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"Requirements:\n"
        f"- Funny/observational about modern life, work, relationships or internet behavior\n"
        f"- Use line breaks and emojis for readability\n"
        f"- Include text only (exclude hashtags)\n"
        f"- Must make sense by itself\n"
        f"- Max 250 characters\n"
    )
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'\*\*|\*|__|_', '', text).strip()
        return text, hashtags, entry['link']
    except Exception as e:
        print(f"AI generation failed: {e}")
        return None, None, None

# =============================
# IMAGE CREATION
# =============================

def create_text_image(text, width=1080, height=1080):
    bg_color = tuple(random.randint(100, 255) for _ in range(3))
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except:
        font = ImageFont.load_default()

    margin = 40
    max_width = width - 2*margin
    lines = textwrap.wrap(text, width=30)
    y_text = margin
    for line in lines:
        w, h = draw.textsize(line, font=font)
        draw.text(((width - w)/2, y_text), line, font=font, fill="black")
        y_text += h + 10

    output = BytesIO()
    img.save(output, format="JPEG")
    output.seek(0)
    return output

# =============================
# TWITTER POST
# =============================

def post_to_twitter_image(text_image, hashtags, api_key, api_secret, access_token, access_token_secret):
    try:
        auth_v1 = tweepy.OAuthHandler(api_key, api_secret)
        auth_v1.set_access_token(access_token, access_token_secret)
        api_v1 = tweepy.API(auth_v1)
        
        media = api_v1.media_upload(filename="tweet.jpg", file=text_image)
        print("✅ Media uploaded, ID:", media.media_id_string)

        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        response = client_v2.create_tweet(
            text=hashtags,
            media_ids=[media.media_id_string]
        )
        if response and response.data:
            print(f"🎉 Tweet posted! ID: {response.data['id']}")
            return True
        return False
    except tweepy.TweepyException as e:
        print("🐦 Twitter API Error:", e.response.text if hasattr(e, 'response') else e)
        return False
    except Exception as e:
        print("🐦 Twitter post error:", e)
        return False

# =============================
# MAIN
# =============================

def main():
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        return
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI API_KEY")
        return

    text, hashtags, _ = generate_engaging_post()
    if not text:
        print("⚠️ AI failed to generate tweet. Skipping post.")
        return

    print(f"Generated text:\n{text}\n")
    print(f"Hashtags:\n{hashtags}\n")

    text_image = create_text_image(text)
    success = post_to_twitter_image(text_image, hashtags, TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)

    print("✅ Posted!" if success else "❌ Failed to post.")

if __name__ == "__main__":
    main()