import os
import google.generativeai as genai
import random
import feedparser
import re
import tweepy

# Configuration
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Reddit RSS feeds for niche
REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/AskReddit/.rss",
    "https://www.reddit.com/r/relationships/.rss",
    "https://www.reddit.com/r/antiwork/.rss",
    "https://www.reddit.com/r/selfimprovement/.rss",
    "https://www.reddit.com/r/technology/.rss"
]

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

posted_links = set()

# =============================
# TWITTER API
# =============================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret):
    """Post text-only tweet"""
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

# =============================
# HELPERS
# =============================

def contains_political_content(text):
    POLITICAL_KEYWORDS = [
        'trump', 'biden', 'president', 'election', 'government', 'policy',
        'tax', 'war', 'political', 'democrat', 'republican', 'vote'
    ]
    return any(k in text.lower() for k in POLITICAL_KEYWORDS) if text else False

# =============================
# PARSE REDDIT RSS
# =============================

def parse_reddit_rss(rss_feeds):
    """Parse RSS feeds from provided list"""
    entries = []
    for url in rss_feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.link in posted_links:
                    continue
                if contains_political_content(entry.title) or contains_political_content(entry.get('summary', '')):
                    continue
                entries.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary', '')
                })
        except Exception as e:
            print(f"RSS error {url}: {e}")
    return entries

# =============================
# GENERATE TWEET WITH HASHTAGS
# =============================

def generate_engaging_post(rss_feeds):
    """Generate a complete tweet with AI-generated hashtags"""
    entries = parse_reddit_rss(rss_feeds)
    
    if not entries:
        print("No valid RSS entries found.")
        return None
    
    entry = random.choice(entries)  
    posted_links.add(entry['link'])
    
    prompt = (
        f"Create ONE standalone, easy-to-read tweet about this online discussion:\n\n"
        f"Title: {entry['title'][:200]}\n"
        f"Summary: {entry['summary'][:500]}\n\n"
        f"Requirements:\n"
        f"- Funny/observational about modern life, work, relationships or internet behavior\n"
        f"- Use line breaks and emojis for readability\n"
        f"- Include EXACTLY 3 relevant hashtags at the end\n"
        f"- Hashtags should be about the topic, not generic\n"
        f"- Must make sense by itself\n"
        f"- Max 250 characters including hashtags\n"
        f"- Do NOT mention Reddit or sources\n"
        f"- Format: Tweet content with line breaks, then 3 hashtags separated by spaces\n\n"
        f"Example format:\n"
        f"😂 First thought here.\n\n"
        f"🤔 Another thought.\n\n"
        f"#Hashtag1 #Hashtag2 #Hashtag3"
    )
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean up formatting
        text = re.sub(r'\*\*|\*|__|_', '', text).strip()
        
        # Ensure it has hashtags
        hashtag_count = len(re.findall(r'#\w+', text))
        if hashtag_count < 3:
            # Add missing hashtags
            hashtag_prompt = f"Generate 3 relevant hashtags for this text: {text[:100]}"
            hashtag_response = model.generate_content(hashtag_prompt)
            hashtags = re.findall(r'#\w+', hashtag_response.text)
            hashtags = hashtags[:3] if hashtags else ["#Life", "#Thoughts", "#Internet"]
            
            if hashtag_count == 0:
                text = f"{text}\n\n{' '.join(hashtags[:3])}"
            else:
                existing_hashtags = re.findall(r'#\w+', text)
                needed = 3 - len(existing_hashtags)
                if needed > 0:
                    text = f"{text} {' '.join(hashtags[:needed])}"
        
        # Ensure max length
        if len(text) > 280:
            text = text[:277] + "..."
            
        return text
        
    except Exception as e:
        print(f"AI generation failed: {e}")
        return None

# =============================
# MAIN EXECUTION
# =============================

def main():
    print("🐦 Reddit Content - Twitter Edition")
    
    # Check API credentials
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        return
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return
    
    # Generate tweet
    post_text = generate_engaging_post(REDDIT_RSS_FEEDS)
    
    # Skip if AI failed
    if not post_text:
        print("❌ AI failed to generate a tweet. Skipping post.")
        return
    
    print(f"Generated Tweet:\n{post_text}\n")
    print(f"Tweet length: {len(post_text)} characters\n")
    
    # Post to Twitter
    success = post_to_twitter(
        post_text,
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    )
    
    print("✅ Posted successfully!" if success else "❌ Failed to post.")

if __name__ == "__main__":
    main()