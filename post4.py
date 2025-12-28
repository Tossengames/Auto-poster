import os
import google.generativeai as genai
import random
import feedparser
import re
import tweepy
from PIL import Image, ImageDraw, ImageFont
import textwrap
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
# IMAGE GENERATION FUNCTIONS
# =============================

def generate_random_color():
    """Generate a random pastel color for the background"""
    return (
        random.randint(100, 200),  # R
        random.randint(100, 200),  # G
        random.randint(100, 200)   # B
    )

def create_image_with_text(text, width=1200, height=630):
    """
    Create an image with random color background and overlay text
    Returns: Bytes of the image
    """
    # Create a new image with random color
    bg_color = generate_random_color()
    image = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)
    
    # Try to use a nice font, fall back to default
    try:
        # Try to use Arial font (common on most systems)
        font = ImageFont.truetype("arial.ttf", 48)
        small_font = ImageFont.truetype("arial.ttf", 36)
    except:
        # Fall back to default font
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Wrap text to fit within image
    margin = 60
    max_width = width - 2 * margin
    max_height = height - 2 * margin
    
    # Calculate character width (approximate)
    avg_char_width = 24  # Approximate width for font size 48
    chars_per_line = max_width // avg_char_width
    
    # Wrap the text
    wrapped_lines = []
    for line in text.split('\n'):
        if len(line.strip()) == 0:
            wrapped_lines.append('')
            continue
        
        wrapped = textwrap.wrap(line, width=chars_per_line)
        if not wrapped:  # Empty line
            wrapped_lines.append('')
        else:
            wrapped_lines.extend(wrapped)
    
    # Calculate total text height
    line_height = 70
    total_text_height = len(wrapped_lines) * line_height
    
    # Start position (centered vertically)
    y_start = (height - total_text_height) // 2
    if y_start < margin:
        y_start = margin
    
    # Draw each line
    for i, line in enumerate(wrapped_lines):
        # Calculate text width for this line
        if font == ImageFont.load_default():
            text_width = len(line) * 10  # Rough estimate for default font
        else:
            text_bbox = draw.textbbox((0, 0), line, font=font)
            text_width = text_bbox[2] - text_bbox[0]
        
        # Center the line horizontally
        x = (width - text_width) // 2
        y = y_start + i * line_height
        
        # Draw text with shadow effect for better readability
        shadow_color = (0, 0, 0)  # Black shadow
        text_color = (255, 255, 255)  # White text
        
        # Draw shadow (slightly offset)
        draw.text((x+2, y+2), line, font=font, fill=shadow_color)
        # Draw main text
        draw.text((x, y), line, font=font, fill=text_color)
    
    # Add a subtle border
    border_color = tuple(max(0, c-40) for c in bg_color)
    draw.rectangle([10, 10, width-10, height-10], outline=border_color, width=4)
    
    # Convert image to bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr.getvalue()

# =============================
# TWITTER API
# =============================

def post_to_twitter_with_image(content, image_bytes, api_key, api_secret, access_token, access_token_secret):
    """Post tweet with image"""
    try:
        # Twitter v1.1 API for media upload (needed for images)
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret,
            access_token, access_token_secret
        )
        api_v1 = tweepy.API(auth)
        
        # Upload media
        media = api_v1.media_upload(filename="tweet_image.png", file=io.BytesIO(image_bytes))
        media_id = media.media_id_string
        
        # Twitter v2 API for tweeting
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Post tweet with image
        response = client_v2.create_tweet(
            text=content,
            media_ids=[media_id]
        )
        return bool(response and response.data)
    except Exception as e:
        print(f"Twitter post error: {e}")
        return False

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret):
    """Post text-only tweet (fallback)"""
    try:
        if len(content) > 280:
            content = content[:277] + "..."
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        response = client_v2.create_tweet(text=content)
        return bool(response and response.data)
    except Exception as e:
        print(f"Twitter post error: {e}")
        return False

def get_trending_hashtags(api_key, api_secret, access_token, access_token_secret, count=3):
    """Fetch trending hashtags from Twitter (US WOEID = 23424977)"""
    try:
        # For simplicity, we'll simulate trending hashtags
        # In production, you'd use Twitter API v1.1
        sample_trends = [
            "#TrendingTopic", "#Viral", "#News",
            "#Tech", "#Life", "#Thoughts",
            "#Internet", "#Discussion", "#Community"
        ]
        random.shuffle(sample_trends)
        return sample_trends[:count]
    except Exception as e:
        print(f"Failed to fetch trending hashtags: {e}")
        return []

# =============================
# HELPERS
# =============================

def contains_political_content(text):
    POLITICAL_KEYWORDS = [
        'trump', 'biden', 'president', 'election', 'government', 'policy',
        'tax', 'war', 'political', 'democrat', 'republican', 'vote'
    ]
    return any(k in text.lower() for k in POLITICAL_KEYWORDS) if text else False

def extract_hashtags_from_text(text, max_tags=3):
    """Simple hashtag creator: grab frequent meaningful words from text."""
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
# GENERATE TWEET
# =============================

def generate_engaging_post():
    entries = parse_reddit_rss()
    if not entries:
        print("No valid RSS entries found.")
        return None, None, None  # Return tweet, hashtags, and image separately

    entry = random.choice(entries)  
    posted_links.add(entry['link'])
    
    # Build prompt for AI to generate tweet AND hashtags
    prompt = (
        f"Create ONE standalone, easy-to-read tweet about this online discussion:\n\n"
        f"Title: {entry['title']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"Requirements:\n"
        f"- Funny/observational about modern life, work, relationships or internet behavior\n"
        f"- Use line breaks and emojis for readability\n"
        f"- Include EXACTLY 3 relevant hashtags at the end\n"
        f"- Must make sense by itself\n"
        f"- Keep the main tweet content under 220 characters (leaving space for hashtags)\n"
        f"- Do NOT mention Reddit or sources\n"
        f"- Format: [Your tweet text]\n\n[3 hashtags separated by spaces]\n\n"
        f"Example:\n"
        f"😂 First thought here.\n\n"
        f"🤔 Another thought.\n\n"
        f"#Hashtag1 #Hashtag2 #Hashtag3"
    )
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'\*\*|\*|__|_', '', text).strip()
        
        # Split the response to separate tweet from hashtags
        lines = text.split('\n')
        tweet_lines = []
        hashtag_line = ""
        
        for line in lines:
            if line.startswith('#') or '#' in line:
                # Extract hashtags
                hashtags_found = re.findall(r'#\w+', line)
                if hashtags_found:
                    # Take only first 3 hashtags
                    hashtag_line = ' '.join(hashtags_found[:3])
                    break
            elif line.strip():  # Non-empty, non-hashtag line
                tweet_lines.append(line.strip())
        
        # If no hashtags found in response, create some
        if not hashtag_line:
            tweet_text = ' '.join(tweet_lines)
            hashtag_line = extract_hashtags_from_text(tweet_text, max_tags=3)
        
        # Create the final tweet (tweet text + hashtags)
        tweet_text_only = '\n\n'.join(tweet_lines)
        final_tweet = f"{tweet_text_only}\n\n{hashtag_line}"
        
        # Truncate if necessary
        if len(final_tweet) > 280:
            final_tweet = final_tweet[:277] + "..."
        
        # Create image with JUST the tweet text (no hashtags)
        image_text = tweet_text_only  # Image contains only the tweet text, no hashtags
        image_bytes = create_image_with_text(image_text)
        
        return final_tweet, hashtag_line, image_bytes
    
    except Exception as e:
        print(f"AI generation failed: {e}")
        return None, None, None

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
    
    # Generate tweet, hashtags, and image
    post_text, hashtags, image_bytes = generate_engaging_post()
    
    if not post_text or not image_bytes:
        print("❌ AI failed to generate content. Skipping post.")
        return
    
    print(f"\nGenerated Hashtags: {hashtags}")
    print(f"\nTweet:\n{post_text}\n")
    
    # Post with image
    success = post_to_twitter_with_image(
        post_text,
        image_bytes,
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    )
    
    # Fallback to text-only if image post fails
    if not success:
        print("⚠️ Image post failed, trying text-only...")
        success = post_to_twitter(
            post_text,
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET
        )
    
    print("✅ Posted with image!" if success else "❌ Failed to post.")

if __name__ == "__main__":
    main()