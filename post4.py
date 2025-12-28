import os
import google.genai as genai
import random
import feedparser
import re
import tweepy
from PIL import Image, ImageDraw, ImageFont
import textwrap
import io
import time

# =============================
# CONFIGURATION
# =============================
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini with new API
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Gemini configuration error: {e}")
    print("Please install: pip install google-genai")

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
    try:
        # Create a new image with random color
        bg_color = generate_random_color()
        image = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        
        # Try to use a nice font
        try:
            # Try common font paths
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "C:/Windows/Fonts/arial.ttf",  # Windows
                "arial.ttf"
            ]
            
            font = None
            for path in font_paths:
                try:
                    font = ImageFont.truetype(path, 48)
                    break
                except:
                    continue
            
            if font is None:
                font = ImageFont.load_default(size=48)
                
        except Exception as font_error:
            print(f"Font error: {font_error}")
            font = ImageFont.load_default(size=48)
        
        # Wrap text to fit within image
        margin = 60
        max_width = width - 2 * margin
        
        # Calculate character width (approximate)
        avg_char_width = 24
        chars_per_line = max_width // avg_char_width
        
        # Wrap the text
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
        
        # Remove empty lines at the beginning and end
        while wrapped_lines and not wrapped_lines[0].strip():
            wrapped_lines.pop(0)
        while wrapped_lines and not wrapped_lines[-1].strip():
            wrapped_lines.pop()
        
        if not wrapped_lines:
            wrapped_lines = ["Daily Thought"]
        
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
            if hasattr(font, 'getbbox'):
                text_bbox = font.getbbox(line)
                text_width = text_bbox[2] - text_bbox[0]
            elif hasattr(font, 'getsize'):
                text_width = font.getsize(line)[0]
            else:
                text_width = len(line) * 24  # Rough estimate
            
            # Center the line horizontally
            x = (width - text_width) // 2
            y = y_start + i * line_height
            
            # Draw text with shadow for readability
            shadow_color = (0, 0, 0, 128)
            text_color = (255, 255, 255, 255)
            
            # Draw shadow (slightly offset)
            draw.text((x+2, y+2), line, font=font, fill=(0, 0, 0))
            # Draw main text
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
        
        # Add a subtle border
        border_color = tuple(max(0, c-40) for c in bg_color)
        draw.rectangle([10, 10, width-10, height-10], outline=border_color, width=4)
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG', optimize=True)
        img_byte_arr.seek(0)
        
        return img_byte_arr.getvalue()
        
    except Exception as e:
        print(f"Image creation error: {e}")
        # Return a simple colored image as fallback
        fallback_image = Image.new('RGB', (width, height), color=(70, 130, 180))
        img_byte_arr = io.BytesIO()
        fallback_image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()

# =============================
# TWITTER API FUNCTIONS
# =============================
def post_to_twitter_with_image(content, image_bytes, api_key, api_secret, access_token, access_token_secret):
    """Post tweet with image using Twitter API v2"""
    try:
        # Initialize Twitter client
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # For media upload, we need OAuth1.1 for v1.1 API
        # But let's try v2 media upload first
        try:
            # Upload media using v2
            media_response = client.create_media(
                media_data=image_bytes,
                media_category="tweet_image"
            )
            
            if hasattr(media_response, 'media_id'):
                media_id = media_response.media_id
            elif hasattr(media_response, 'media_id_string'):
                media_id = media_response.media_id_string
            elif hasattr(media_response, 'data'):
                media_id = media_response.data.get('media_id_string')
            else:
                print("Could not extract media ID, falling back to text-only")
                return post_to_twitter(content, api_key, api_secret, access_token, access_token_secret)
            
            # Post tweet with media
            response = client.create_tweet(
                text=content,
                media_ids=[media_id]
            )
            
            return bool(response and response.data)
            
        except Exception as media_error:
            print(f"Media upload error: {media_error}")
            print("Falling back to text-only tweet")
            return post_to_twitter(content, api_key, api_secret, access_token, access_token_secret)
            
    except Exception as e:
        print(f"Twitter post with image error: {e}")
        return False

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret):
    """Post text-only tweet"""
    try:
        if len(content) > 280:
            content = content[:277] + "..."
        
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        response = client.create_tweet(text=content)
        
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
    """Check if text contains political keywords"""
    if not text:
        return False
    
    POLITICAL_KEYWORDS = [
        'trump', 'biden', 'president', 'election', 'government', 'policy',
        'tax', 'war', 'political', 'democrat', 'republican', 'vote',
        'congress', 'senate', 'white house', 'campaign', 'poll'
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in POLITICAL_KEYWORDS)

def extract_hashtags_from_text(text, max_tags=3):
    """Create hashtags from frequent meaningful words in text"""
    if not text:
        return ""
    
    # Extract words (4+ letters)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    
    # Common words to exclude
    stop_words = {'this', 'that', 'with', 'have', 'from', 'like', 'just',
                 'what', 'when', 'where', 'your', 'their', 'about', 'would',
                 'could', 'should', 'there', 'they', 'been', 'some', 'more'}
    
    # Filter and count
    word_counts = {}
    for word in words:
        if word not in stop_words:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Sort by frequency
    sorted_words = sorted(word_counts.items(), key=lambda x: (-x[1], x[0]))
    
    # Create hashtags
    tags = []
    for word, _ in sorted_words:
        tag = "#" + word.capitalize()
        if tag not in tags:
            tags.append(tag)
        if len(tags) >= max_tags:
            break
    
    return " ".join(tags) if tags else "#Thoughts #Life #Reflection"

def clean_text(text):
    """Clean text from markdown and extra spaces"""
    if not text:
        return ""
    
    # Remove markdown
    text = re.sub(r'[#*_~`]', '', text)
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    # Remove extra spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    
    # Remove specific Reddit patterns
    text = re.sub(r'\[.*?\]|\(.*?\)', '', text)
    
    return text.strip()

# =============================
# RSS PARSING
# =============================
def parse_reddit_rss():
    """Parse Reddit RSS feeds and return valid entries"""
    entries = []
    
    for url in REDDIT_RSS_FEEDS:
        try:
            print(f"Fetching from {url}...")
            feed = feedparser.parse(url)
            
            if feed.bozo:
                print(f"  RSS parse error for {url}: {feed.bozo_exception}")
                continue
            
            for entry in feed.entries:
                try:
                    # Skip if already posted
                    if entry.link in posted_links:
                        continue
                    
                    # Skip political content
                    title = clean_text(entry.title)
                    summary = clean_text(entry.get('summary', ''))
                    
                    if contains_political_content(title) or contains_political_content(summary):
                        continue
                    
                    # Skip if too short
                    if len(title) < 10:
                        continue
                    
                    entries.append({
                        'title': title,
                        'link': entry.link,
                        'summary': summary[:500]  # Limit summary length
                    })
                    
                    print(f"  Found: {title[:50]}...")
                    
                except Exception as entry_error:
                    print(f"  Error processing entry: {entry_error}")
                    continue
                    
        except Exception as feed_error:
            print(f"Error fetching {url}: {feed_error}")
            continue
    
    print(f"Total valid entries found: {len(entries)}")
    return entries

# =============================
# CONTENT GENERATION
# =============================
def generate_engaging_post():
    """Generate a tweet and image from Reddit content"""
    print("\n" + "="*50)
    print("Generating engaging post...")
    print("="*50)
    
    # Parse RSS feeds
    entries = parse_reddit_rss()
    
    if not entries:
        print("❌ No valid RSS entries found.")
        return None, None, None
    
    # Select random entry
    entry = random.choice(entries)
    posted_links.add(entry['link'])
    
    print(f"\nSelected entry:")
    print(f"Title: {entry['title'][:100]}...")
    print(f"Summary: {entry['summary'][:100]}...")
    
    # Build prompt for AI
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
    
    FORMAT:
    [Your tweet text here]
    
    [3 hashtags separated by spaces]
    
    EXAMPLE:
    Sometimes the best life advice comes from strangers online. 🤔
    Today's gem: "If it won't matter in 5 years, don't waste 5 minutes worrying about it."
    
    #Wisdom #LifeAdvice #Perspective
    """
    
    try:
        print("\nGenerating content with Gemini...")
        
        # Generate content using Gemini
        response = genai.generate_text(
            model="gemini-1.5-flash",
            prompt=prompt
        )
        
        generated_text = response.text.strip()
        print(f"Generated response:\n{generated_text}\n")
        
        # Clean the text
        cleaned_text = clean_text(generated_text)
        
        # Split into tweet and hashtags
        lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
        
        if not lines:
            raise ValueError("No content generated")
        
        # Find hashtags (should be at the end)
        tweet_lines = []
        hashtag_line = ""
        
        for line in lines:
            if line.startswith('#') and len(line.split()) <= 5:
                hashtag_line = line
            else:
                tweet_lines.append(line)
        
        # If no hashtags found in response, generate some
        if not hashtag_line:
            print("No hashtags found in response, generating some...")
            all_text = ' '.join(tweet_lines)
            hashtag_line = extract_hashtags_from_text(all_text, max_tags=3)
        
        # Ensure exactly 3 hashtags
        hashtags = re.findall(r'#\w+', hashtag_line)
        if len(hashtags) > 3:
            hashtags = hashtags[:3]
        elif len(hashtags) < 3:
            # Add more hashtags if needed
            all_text = ' '.join(tweet_lines)
            additional = extract_hashtags_from_text(all_text, max_tags=3-len(hashtags))
            additional_tags = re.findall(r'#\w+', additional)
            hashtags.extend(additional_tags[:3-len(hashtags)])
        
        hashtag_line = ' '.join(hashtags[:3])
        
        # Create the final tweet
        tweet_text_only = '\n\n'.join(tweet_lines)
        final_tweet = f"{tweet_text_only}\n\n{hashtag_line}"
        
        # Truncate if necessary
        if len(final_tweet) > 280:
            final_tweet = final_tweet[:277] + "..."
        
        print(f"Final tweet ({len(final_tweet)} chars):")
        print(final_tweet)
        print(f"\nHashtags: {hashtag_line}")
        
        # Create image with just the tweet text (no hashtags)
        print("\nCreating image...")
        image_text = tweet_text_only  # No hashtags on image
        image_bytes = create_image_with_text(image_text)
        
        print(f"Image created: {len(image_bytes)} bytes")
        
        return final_tweet, hashtag_line, image_bytes
        
    except Exception as e:
        print(f"❌ AI generation failed: {e}")
        
        # Fallback: Create simple tweet
        try:
            title = entry['title'][:100]
            hashtag_line = extract_hashtags_from_text(title, max_tags=3)
            tweet_text = f"{title}\n\n{hashtag_line}"
            
            if len(tweet_text) > 280:
                tweet_text = tweet_text[:277] + "..."
            
            image_bytes = create_image_with_text(title)
            
            return tweet_text, hashtag_line, image_bytes
            
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            return None, None, None

# =============================
# MAIN FUNCTION
# =============================
def main():
    print("🚀 Reddit to Twitter Bot")
    print("="*50)
    
    # Check environment variables
    missing_vars = []
    if not TWITTER_API_KEY:
        missing_vars.append("TWITTER_API_KEY")
    if not TWITTER_API_SECRET:
        missing_vars.append("TWITTER_API_SECRET")
    if not TWITTER_ACCESS_TOKEN:
        missing_vars.append("TWITTER_ACCESS_TOKEN")
    if not TWITTER_ACCESS_TOKEN_SECRET:
        missing_vars.append("TWITTER_ACCESS_TOKEN_SECRET")
    if not GEMINI_API_KEY:
        missing_vars.append("GEMINI_API_KEY")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return
    
    print("✓ All environment variables found")
    
    # Generate content
    post_text, hashtags, image_bytes = generate_engaging_post()
    
    if not post_text:
        print("❌ Failed to generate content. Exiting.")
        return
    
    print("\n" + "="*50)
    print("POSTING TO TWITTER")
    print("="*50)
    
    # Post to Twitter with image
    print("Posting tweet with image...")
    success = post_to_twitter_with_image(
        post_text,
        image_bytes,
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    )
    
    if success:
        print("✅ Successfully posted to Twitter with image!")
    else:
        print("⚠️ Failed to post with image, trying text-only...")
        
        # Try text-only as fallback
        success = post_to_twitter(
            post_text,
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET
        )
        
        if success:
            print("✅ Successfully posted text-only tweet!")
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
        import traceback
        traceback.print_exc()