import os
import google.genai as genai
import random
import feedparser
import re
import tweepy

# =============================
# CONFIGURATION
# =============================
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini with NEW API - DIFFERENT SYNTAX
# No configure() needed, just set the API key as parameter
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
# TWITTER API
# =============================

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

def clean_text(text):
    """Clean text from markdown and extra spaces"""
    if not text:
        return ""
    
    text = re.sub(r'[#*_~`]', '', text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text)
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
# CONTENT GENERATION - USING NEW GEMINI API
# =============================

def generate_engaging_post():
    """Generate a tweet from Reddit content"""
    entries = parse_reddit_rss()
    
    if not entries:
        print("❌ No valid RSS entries found.")
        return None
    
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
    6. Total length: Under 280 characters including hashtags
    
    EXAMPLE FORMAT:
    Sometimes the best life advice comes from strangers online. 🤔
    Today's gem: "If it won't matter in 5 years, don't waste 5 minutes worrying about it."
    
    #Wisdom #LifeAdvice #Perspective
    """
    
    try:
        # NEW GEMINI API SYNTAX
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        generated_text = response.text.strip()
        cleaned_text = clean_text(generated_text)
        
        lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
        
        if not lines:
            print("❌ AI generated empty content")
            return None
        
        tweet_lines = []
        hashtag_line = ""
        
        for line in lines:
            if line.startswith('#') and len(line.split()) <= 5:
                hashtag_line = line
            else:
                tweet_lines.append(line)
        
        # Validate hashtags
        if not hashtag_line:
            print("❌ No hashtags found in AI response")
            return None
        
        hashtags = re.findall(r'#\w+', hashtag_line)
        if len(hashtags) < 3:
            print(f"❌ Only {len(hashtags)} hashtags found, need exactly 3")
            return None
            
        hashtag_line = ' '.join(hashtags[:3])
        
        # Combine tweet text with hashtags
        tweet_text_only = '\n\n'.join(tweet_lines)
        final_tweet = f"{tweet_text_only}\n\n{hashtag_line}"
        
        # Final validation
        if len(final_tweet) > 280:
            print(f"❌ Tweet too long: {len(final_tweet)} characters")
            return None
        
        if len(final_tweet) < 50:
            print("❌ Tweet too short")
            return None
        
        return final_tweet
        
    except Exception as e:
        print(f"❌ AI generation failed: {e}")
        return None

# =============================
# MAIN FUNCTION
# =============================

def main():
    print("🚀 Reddit to Twitter Bot")
    print("="*50)
    
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
    
    post_text = generate_engaging_post()
    
    if not post_text:
        print("❌ Failed to generate content. Skipping post.")
        return
    
    print(f"\nGenerated Tweet ({len(post_text)} characters):")
    print(post_text)
    
    print("\n" + "="*50)
    print("POSTING TO TWITTER")
    print("="*50)
    
    print("Posting tweet...")
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