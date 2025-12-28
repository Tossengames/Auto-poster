import os
import random
import feedparser
import re
import tweepy
from PIL import Image, ImageDraw, ImageFont
import textwrap
import io
from google import genai  # Updated import for Gemini API

# =============================
# CONFIGURATION
# =============================
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# =============================
# RSS FEEDS
# =============================
REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/AskReddit/.rss",
    "https://www.reddit.com/r/relationships/.rss",
    "https://www.reddit.com/r/antiwork/.rss",
    "https://www.reddit.com/r/selfimprovement/.rss",
    "https://www.reddit.com/r/technology/.rss"
]

posted_links = set()

# =============================
# IMAGE GENERATION FUNCTIONS
# =============================

def generate_random_color():
    return (
        random.randint(100, 200),
        random.randint(100, 200),
        random.randint(100, 200)
    )

def create_image_with_text(text, width=1200, height=630):
    try:
        bg_color = generate_random_color()
        image = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()

        margin = 60
        max_width = width - 2 * margin
        avg_char_width = 24
        chars_per_line = max_width // avg_char_width

        wrapped_lines = []
        for line in text.split('\n'):
            if not line.strip():
                wrapped_lines.append('')
                continue
            wrapped = textwrap.wrap(line, width=chars_per_line)
            if wrapped:
                wrapped_lines.extend(wrapped)
            else:
                wrapped_lines.append('')

        while wrapped_lines and not wrapped_lines[0].strip():
            wrapped_lines.pop(0)
        while wrapped_lines and not wrapped_lines[-1].strip():
            wrapped_lines.pop()

        if not wrapped_lines:
            return None

        line_height = 70
        total_text_height = len(wrapped_lines) * line_height
        y_start = (height - total_text_height) // 2
        if y_start < margin:
            y_start = margin

        for i, line in enumerate(wrapped_lines):
            if hasattr(font, 'getbbox'):
                text_bbox = font.getbbox(line)
                text_width = text_bbox[2] - text_bbox[0]
            elif hasattr(font, 'getsize'):
                text_width = font.getsize(line)[0]
            else:
                text_width = len(line) * 24

            x = (width - text_width) // 2
            y = y_start + i * line_height

            draw.text((x+2, y+2), line, font=font, fill=(0, 0, 0))
            draw.text((x, y), line, font=font, fill=(255, 255, 255))

        border_color = tuple(max(0, c-40) for c in bg_color)
        draw.rectangle([10, 10, width-10, height-10], outline=border_color, width=4)

        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG', optimize=True)
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    except Exception as e:
        print(f"Image creation error: {e}")
        return None

# =============================
# TWITTER API FUNCTIONS
# =============================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret):
    try:
        if len(content) > 280:
            content = content[:277] + "..."
        client_twitter = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        response = client_twitter.create_tweet(text=content)
        if response and response.data:
            print(f"Tweet posted successfully! Tweet ID: {response.data['id']}")
            return True
        else:
            print("Tweet post returned no data")
            return False
    except tweepy.TweepyException as e:
        print(f"Twitter API error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error posting to Twitter: {e}")
        return False

# =============================
# HELPER FUNCTIONS
# =============================

def contains_political_content(text):
    if not text:
        return False
    POLITICAL_KEYWORDS = [
        'trump', 'biden', 'president', 'election', 'government', 'policy',
        'tax', 'war', 'political', 'democrat', 'republican', 'vote',
        'congress', 'senate', 'white house', 'campaign', 'poll'
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in POLITICAL_KEYWORDS)

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'[#*_~`]', '', text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'.*?|.*?', '', text)
    return text.strip()

# =============================
# RSS PARSING
# =============================

def parse_reddit_rss():
    entries = []
    for url in REDDIT_RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                continue
            for entry in feed.entries:
                try:
                    if entry.link in posted_links:
                        continue
                    title = clean_text(entry.title)
                    summary = clean_text(entry.get('summary', ''))
                    if contains_political_content(title) or contains_political_content(summary):
                        continue
                    if len(title) < 10:
                        continue
                    entries.append({
                        'title': title,
                        'link': entry.link,
                        'summary': summary[:500]
                    })
                except:
                    continue
        except:
            continue
    return entries

# =============================
# CONTENT GENERATION
# =============================

def generate_engaging_post():
    entries = parse_reddit_rss()
    if not entries:
        print("❌ No valid RSS entries found.")
        return None, None, None

    entry = random.choice(entries)
    posted_links.add(entry['link'])

    prompt = f"""
    Create ONE engaging tweet based on this Reddit discussion:

    TITLE: {entry['title']}

    CONTEXT: {entry['summary']}

    REQUIREMENTS:
    1. Make it funny, observational, or insightful about modern life, work, relationships, or internet culture
    2. Use 1-2 relevant emojis
    3. Include EXACTLY 3 relevant hashtags at the end
    4. Make it stand alone - don't reference Reddit
    5. Use line breaks for readability (1-3 lines max)
    6. Total length: Under 250 characters including hashtags
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        generated_text = response.text.strip()
        cleaned_text = clean_text(generated_text)
        lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]

        if not lines:
            print("❌ AI generated empty content")
            return None, None, None

        tweet_lines = []
        hashtag_line = ""
        for line in lines:
            if line.startswith('#') and len(line.split()) <= 5:
                hashtag_line = line
            else:
                tweet_lines.append(line)

        if not hashtag_line:
            all_text = ' '.join(tweet_lines)
            hashtags = re.findall(r'#\w+', all_text)
            if not hashtags:
                print("❌ No hashtags found in AI response")
                return None, None, None
            hashtag_line = ' '.join(hashtags[:3])

        hashtags = re.findall(r'#\w+', hashtag_line)
        if len(hashtags) < 3:
            print(f"❌ Only {len(hashtags)} hashtags found, need exactly 3")
            return None, None, None

        hashtag_line = ' '.join(hashtags[:3])
        tweet_text_only = '\n\n'.join(tweet_lines)
        final_tweet = f"{tweet_text_only}\n\n{hashtag_line}"
        if len(final_tweet) > 280:
            final_tweet = final_tweet[:277] + "..."
        image_text = tweet_text_only
        image_bytes = create_image_with_text(image_text)
        if not image_bytes:
            print("❌ Failed to create image")
            return None, None, None

        return final_tweet, hashtag_line, image_bytes

    except Exception as e:
        print(f"❌ AI generation failed: {e}")
        return None, None, None

# =============================
# MAIN FUNCTION
# =============================

def main():
    print("🚀 Reddit to Twitter Bot")
    print("="*50)
    missing_vars = []
    if not TWITTER_API_KEY: missing_vars.append("TWITTER_API_KEY")
    if not TWITTER_API_SECRET: missing_vars.append("TWITTER_API_SECRET")
    if not TWITTER_ACCESS_TOKEN: missing_vars.append("TWITTER_ACCESS_TOKEN")
    if not TWITTER_ACCESS_TOKEN_SECRET: missing_vars.append("TWITTER_ACCESS_TOKEN_SECRET")
    if not GEMINI_API_KEY: missing_vars.append("GEMINI_API_KEY")
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return
    print("✓ All environment variables found")

    post_text, hashtags, image_bytes = generate_engaging_post()
    if not post_text:
        print("❌ Failed to generate content. Skipping post.")
        return

    print(f"\nGenerated Hashtags: {hashtags}")
    print(f"\nTweet:\n{post_text}\n")
    print("\n" + "="*50)
    print("POSTING TO TWITTER")
    print("="*50)

    success = post_to_twitter(
        post_text,
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    )

    if success:
        print("✅ Successfully posted to Twitter!")
    else:
        print("❌ Failed to post to Twitter.")

    print("\n" + "="*50)
    print("PROCESS COMPLETE")
    print("="*50)

# =============================
# ENTRY POINT
# =============================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")