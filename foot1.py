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
        "style": "like a stats fan who spots what others miss",
        "focus": "stats like xG, pass accuracy, and possession numbers - keep it simple, point out what the numbers actually mean",
        "hashtags": ["#FootballStats", "#Analytics", "#Data", "#SoccerAnalysis", "#SportsData"]
    },
    "tactical_nerd": {
        "style": "like a coach explaining things to friends at the pub",
        "focus": "formations, pressing, and subtle game changes - explain it like you're talking to someone, not writing a textbook",
        "hashtags": ["#Tactics", "#FootballTalk", "#GameAnalysis", "#Soccer", "#Strategy"]
    },
    "transfer_whisperer": {
        "style": "like someone who follows transfer gossip but keeps it real",
        "focus": "transfers, contracts, rumors - talk about the business side like it's football gossip with friends",
        "hashtags": ["#TransferTalk", "#Rumors", "#SoccerNews", "#Football", "#MarketWatch"]
    },
    "cultural_historian": {
        "style": "like an older fan sharing cool stories",
        "focus": "old moments, legendary players, iconic games - tell stories like you're reminiscing, not giving a history lesson",
        "hashtags": ["#Throwback", "#FootballHistory", "#OldSchool", "#Soccer", "#Nostalgia"]
    },
    "fan_philosopher": {
        "style": "like a regular fan chatting about football life",
        "focus": "what it's really like to support a team, rivalries, matchday feelings - keep it real and relatable",
        "hashtags": ["#FanLife", "#FootballCulture", "#Matchday", "#Soccer", "#Supporters"]
    }
}

# =============================
# CURATED HIGH-PERFORMING HASHTAG POOL
# Natural, conversational hashtags that real people use
# =============================

TOP_SOCCER_HASHTAGS = [
    # Natural, conversational hashtags
    "#football", "#soccer", "#futbol", "#footballtalk", "#footballfan",
    "#matchday", "#gameday", "#footballlife", "#soccerfan", "#footballculture",
    
    # League and team hashtags (natural usage)
    "#premierleague", "#laliga", "#bundesliga", "#seriea", "#ucl",
    "#championsleague", "#worldcup", "#euro",
    
    # Player hashtags (only top players people actually tag)
    "#messi", "#ronaldo", "#mbappe", "#haaland",
    
    # Content type hashtags
    "#analysis", "#stats", "#tactics", "#history", "#throwback",
    "#rumors", "#transfers", "#news", "#highlights", "#goals",
    
    # Engagement and community
    "#footballtwitter", "#soccertwitter", "#viral", "#fyp", "#footballcommunity"
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
    """Selects 5-6 random hashtags from the curated pool."""
    num_to_pick = random.randint(5, 6)
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
                        'summary': summary[:300] if summary else ''  # Shorter summary for shorter tweets
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

        # NATURAL LANGUAGE PROMPT - SHORT AND HUMAN-LIKE
        prompt = (
            f"Write a short, natural soccer tweet (2 lines max) based on this:\n\n"
            f"Title: {entry['title']}\n"
            f"Summary: {entry['summary']}\n\n"
            f"WRITE LIKE A REAL PERSON CHATTING:\n"
            f"- Sound like {selected_type['style']}\n"
            f"- Keep it to 2 lines maximum\n"
            f"- Use normal, everyday language\n"
            f"- NO AI-sounding words like 'behold', 'thus', 'indeed'\n"
            f"- NO first-person (I, me, my, we, our, us)\n"
            f"- Use casual emojis if they fit naturally 😅👍⚽\n"
            f"- Make it something a real fan would actually say\n"
            f"- Under 200 characters for the message part\n"
            f"- DON'T mention Reddit or where it came from\n\n"
            f"Examples of natural style:\n"
            f"'That defending was something else. Just completely fell apart at the back.'\n"
            f"'Stats say they dominated possession. Funny how it never felt that way watching.'\n"
            f"'Remember that game? Still gives me goosebumps thinking about it.'\n\n"
            f"Just write the tweet text, nothing else."
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

            # Clean up the text to sound more natural
            text = re.sub(r'\*\*|\*|__|_', '', text).strip()
            
            # Remove any remaining AI-sounding phrases
            ai_phrases = [
                r'\b(behold|thus|indeed|henceforth|hereby|wherein)\b',
                r'\b(as an ai|as a language model|as an artificial)\b',
                r'\b(in summary|in conclusion|to summarize)\b',
                r'\b(dear reader|valued audience|esteemed followers)\b'
            ]
            for phrase in ai_phrases:
                text = re.sub(phrase, '', text, flags=re.IGNORECASE)
            
            text = re.sub(r'\b(reddit|subreddit|r/\w+)\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\b(I|me|my|we|our|us)\b', '', text, flags=re.IGNORECASE)
            
            # Clean up extra spaces and newlines
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n+', '\n', text)
            
            # Ensure it's exactly 1-2 lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) > 2:
                text = '\n'.join(lines[:2])
            elif len(lines) == 1 and len(text) > 100:
                # If one line is too long, split it naturally
                words = text.split()
                if len(words) > 15:
                    mid = len(words) // 2
                    text = ' '.join(words[:mid]) + '\n' + ' '.join(words[mid:])
            
            # ADD RANDOMIZED HASHTAGS (5-6 now)
            dynamic_hashtags = get_random_hashtags()
            final_tweet = text + "\n\n" + dynamic_hashtags

            if len(final_tweet) > 280:
                # Trim the text part, not the hashtags
                text_max_len = 280 - len(dynamic_hashtags) - 3  # -3 for newlines
                text = text[:text_max_len].rsplit(' ', 1)[0]  # Don't cut words
                final_tweet = text + "\n\n" + dynamic_hashtags

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
    print("⚽ Soccer Content Bot - Natural Human Edition")
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
    print(f"✓ Hashtag pool: {len(TOP_SOCCER_HASHTAGS)} natural tags")
    print("✓ Writing style: Natural human conversation")
    print("✓ Tweet length: 2 lines maximum")
    print("✓ Hashtags: 5-6 per tweet")
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