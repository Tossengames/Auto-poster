import os
import random
import feedparser
import re
import tweepy
import time
import requests

# =============================
# GEMINI (NEW SDK)
# =============================
from google import genai

# =============================
# CONFIGURATION
# =============================

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# =============================
# INITIALIZE GEMINI
# =============================

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash-lite"

# =============================
# EXPANDED REDDIT RSS FEEDS FOR SOCCER
# =============================

REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/soccer/.rss",
    "https://www.reddit.com/r/football/.rss",
    "https://www.reddit.com/r/PremierLeague/.rss",
    "https://www.reddit.com/r/footballtactics/.rss",
    "https://www.reddit.com/r/Bundesliga/.rss",
    "https://www.reddit.com/r/LaLiga/.rss",
    "https://www.reddit.com/r/classicsoccer/.rss",
    "https://www.reddit.com/r/footballmemes/.rss",
    "https://www.reddit.com/r/soccercirclejerk/.rss",
    "https://www.reddit.com/r/MLS/.rss",
]

posted_links = set()

# =============================
# RANDOM CONTENT TYPE PERSONALITIES
# =============================

CONTENT_TYPES = {
    "data_driven": {
        "style": "analytical and stats-focused",
        "focus": "expected goals (xG), pass completion, defensive stats, possession metrics, and what the numbers truly reveal about the game",
        "hashtags": ["#FootballAnalytics", "#SoccerStats", "#Data", "#xG", "#SportsScience"]
    },
    "tactical_nerd": {
        "style": "technical and educational",
        "focus": "formations, pressing traps, midfield structures, tactical fouls, manager philosophies, and subtle in-game adjustments",
        "hashtags": ["#FootballTactics", "#TacticalAnalysis", "#Soccer", "#Coach", "#GamePlan"]
    },
    "transfer_whisperer": {
        "style": "speculative and market-savvy",
        "focus": "transfer rumors, contract details, agent activity, club finances, youth prospects, and the business behind the sport",
        "hashtags": ["#TransferNews", "#DeadlineDay", "#SoccerTransfers", "#Football", "#Rumors"]
    },
    "cultural_historian": {
        "style": "nostalgic and story-driven",
        "focus": "iconic moments, legendary players, historic kits, forgotten teams, stadium lore, and the cultural impact of soccer",
        "hashtags": ["#FootballHistory", "#ClassicFootball", "#SoccerLegends", "#Nostalgia", "#Throwback"]
    },
    "fan_philosopher": {
        "style": "observational and witty",
        "focus": "fan behavior, the agony and ecstasy of support, rivalries, superstitions, and the universal truths of being a football fan",
        "hashtags": ["#FanCulture", "#FootballLife", "#Soccer", "#LoveFootball", "#GameDay"]
    }
}

# =============================
# CURATED HIGH-PERFORMING HASHTAG POOL
# Based on popular soccer/sports hashtag research
# =============================

TOP_SOCCER_HASHTAGS = [
    # High-Reach General Soccer Hashtags
    "#soccer", "#football", "#futbol", "#sports", "#fifa",
    # Top Player & League Hashtags
    "#messi", "#ronaldo", "#premierleague", "#laliga", "#bundesliga", "#seriea", "#ucl",
    # Engaging & Community Hashtags
    "#goals", "#championsleague", "#worldcup", "#transfer", "#skills", "#training", "#matchday",
    # Platform & Viral Hashtags
    "#viral", "#fyp", "#soccertiktok", "#footballtwitter"
]

# =============================
# TWITTER API FUNCTION
# =============================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret):
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
# HELPER FUNCTIONS
# =============================

def contains_political_content(text):
    POLITICAL_KEYWORDS = [
        'trump','biden','president','election','government','policy',
        'tax','war','democrat','republican','vote','congress','senate'
    ]
    return any(k in text.lower() for k in POLITICAL_KEYWORDS) if text else False

def clean_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    return text.strip()

def get_random_hashtags():
    """Selects 3-4 random hashtags from the curated pool."""
    num_to_pick = random.randint(3, 4)
    selected = random.sample(TOP_SOCCER_HASHTAGS, num_to_pick)
    return ' '.join(selected)

# =============================
# PARSE REDDIT RSS WITH RETRY
# =============================

def parse_reddit_rss(max_retries=3):
    entries = []
    
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    feedparser.USER_AGENT = custom_headers['User-Agent']
    shuffled_feeds = random.sample(REDDIT_RSS_FEEDS, len(REDDIT_RSS_FEEDS))
    
    for url in shuffled_feeds:
        success = False
        for retry in range(max_retries):
            try:
                print(f"  Trying feed: {url.split('/')[4]}...")
                response = requests.get(url, headers=custom_headers, timeout=15)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                
                if not feed.entries:
                    print(f"    No entries found")
                    break
                
                print(f"    Found {len(feed.entries)} entries")
                
                for entry in feed.entries[:15]:
                    if not hasattr(entry, 'link') or not entry.link:
                        continue
                    
                    link = entry.link
                    if link in posted_links:
                        continue
                    
                    title = clean_html(getattr(entry, 'title', 'No title'))
                    summary = clean_html(getattr(entry, 'summary', ''))
                    
                    if len(title) < 10 or title == 'No title':
                        continue
                    
                    if contains_political_content(title) or contains_political_content(summary):
                        continue
                    
                    entries.append({
                        'title': title,
                        'link': link,
                        'summary': summary[:500] if summary else ''
                    })
                
                success = True
                break
                
            except requests.exceptions.RequestException as e:
                print(f"    Request error (attempt {retry + 1}/{max_retries}): {e}")
                if retry < max_retries - 1:
                    time.sleep(2)
                continue
            except Exception as e:
                print(f"    Parsing error: {e}")
                break
        
        if len(entries) >= 20:
            print(f"  Collected {len(entries)} entries, moving to generation")
            break
    
    print(f"Total entries collected: {len(entries)}")
    return entries

# =============================
# GENERATE TWEET WITH RANDOM STYLE
# =============================

def generate_engaging_post(max_rss_retries=3, max_entry_tries=5):
    entries = []
    
    for retry in range(max_rss_retries):
        print(f"\nRSS Fetch Attempt {retry + 1}/{max_rss_retries}")
        entries = parse_reddit_rss(max_retries=2)
        
        if entries:
            print(f"✓ Successfully collected {len(entries)} entries")
            break
        elif retry < max_rss_retries - 1:
            print(f"✗ No entries found, waiting 3 seconds before retry...")
            time.sleep(3)
    
    if not entries:
        print("\n❌ No valid RSS entries found after all retries.")
        return None, None
    
    # RANDOMLY SELECT A CONTENT PERSONALITY
    selected_type_name = random.choice(list(CONTENT_TYPES.keys()))
    selected_type = CONTENT_TYPES[selected_type_name]
    print(f"\n🎭 Selected Content Personality: {selected_type_name.replace('_', ' ').title()}")
    print(f"   Style: {selected_type['style']}")
    print(f"   Focus: {selected_type['focus'][:80]}...")
    
    attempted_entries = []
    for attempt in range(min(max_entry_tries, len(entries))):
        available_entries = [e for e in entries if e['link'] not in attempted_entries]
        if not available_entries:
            break
            
        entry = random.choice(available_entries)
        attempted_entries.append(entry['link'])
        
        print(f"\n📝 Generation Attempt {attempt + 1}/{min(max_entry_tries, len(entries))}")
        print(f"   Source: {entry['link'].split('/')[4] if len(entry['link'].split('/')) > 4 else 'reddit'}")
        print(f"   Title: {entry['title'][:80]}...")
        
        posted_links.add(entry['link'])

        # DYNAMIC PROMPT BASED ON RANDOMLY SELECTED STYLE
        prompt = (
            f"Create ONE standalone, engaging tweet about soccer, inspired by this discussion:\n\n"
            f"Title: {entry['title']}\n"
            f"Summary: {entry['summary']}\n\n"
            f"IMPORTANT - ADOPT THIS SPECIFIC PERSONA:\n"
            f"You are a {selected_type['style']} commentator. Your focus is on {selected_type['focus']}.\n\n"
            f"Tweet Requirements:\n"
            f"- Write from a third-person or neutral observer perspective\n"
            f"- DO NOT use first-person words (I, me, my, we, our, us)\n"
            f"- Be insightful, witty, or intriguing based on your persona\n"
            f"- Use 1-2 relevant emojis for tone\n"
            f"- Must make sense by itself without needing the source\n"
            f"- Max 250 characters for the tweet text\n"
            f"- Do NOT mention Reddit, 'subreddit', or 'OP'\n\n"
            f"Generate ONLY the tweet text. Do not add explanations.\n"
        )

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            text = ""
            if response and response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text

            text = text.strip()
            if not text:
                print(f"✗ Gemini returned empty content")
                if attempt < min(max_entry_tries - 1, len(entries) - 1):
                    time.sleep(1)
                continue

            # Clean and format the generated text
            text = re.sub(r'\*\*|\*|__|_', '', text).strip()
            text = re.sub(r'\b(reddit|subreddit|r/\w+)\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\b(I|me|my|we|our|us)\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\n\s*\n+', '\n\n', text)
            
            # ADD RANDOMIZED HASHTAGS
            dynamic_hashtags = get_random_hashtags()
            final_tweet = text + "\n\n" + dynamic_hashtags

            if len(final_tweet) > 280:
                final_tweet = final_tweet[:274] + "..."

            print(f"✓ Successfully generated tweet ({len(final_tweet)} chars)")
            print(f"   Hashtags: {dynamic_hashtags}")
            return final_tweet, None

        except Exception as e:
            print(f"✗ AI generation failed: {e}")
            if attempt < min(max_entry_tries - 1, len(entries) - 1):
                time.sleep(1)
            continue
    
    print("\n❌ Failed to generate tweet from all attempted entries.")
    return None, None

# =============================
# MAIN EXECUTION FUNCTION
# =============================

def main():
    print("=" * 50)
    print("⚽ Soccer Content Bot - Multi-Style Edition")
    print("=" * 50)

    # Check credentials
    credentials = {
        'TWITTER_API_KEY': TWITTER_API_KEY,
        'TWITTER_API_SECRET': TWITTER_API_SECRET,
        'TWITTER_ACCESS_TOKEN': TWITTER_ACCESS_TOKEN,
        'TWITTER_ACCESS_TOKEN_SECRET': TWITTER_ACCESS_TOKEN_SECRET,
        'GEMINI_API_KEY': GEMINI_API_KEY
    }
    
    missing = [key for key, value in credentials.items() if not value]
    if missing:
        print("❌ Missing credentials:")
        for m in missing:
            print(f"   - {m}")
        return

    print("✓ All credentials present")
    print(f"✓ Using {len(REDDIT_RSS_FEEDS)} soccer RSS feeds")
    print(f"✓ Hashtag pool: {len(TOP_SOCCER_HASHTAGS)} curated tags")
    print("\n🚀 Starting content generation...")

    post_text, _ = generate_engaging_post()
    
    if not post_text:
        print("\n❌ Failed to generate a tweet after all retries. Skipping post.")
        return

    print(f"\n" + "=" * 50)
    print("FINAL TWEET:")
    print("=" * 50)
    print(post_text)
    print("=" * 50)
    print(f"Length: {len(post_text)} characters")
    print("=" * 50)

    print("\n📤 Posting to Twitter...")
    success = post_to_twitter(
        post_text,
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    )

    if success:
        print("\n✅ Successfully posted to Twitter!")
    else:
        print("\n❌ Failed to post to Twitter.")

if __name__ == "__main__":
    main()