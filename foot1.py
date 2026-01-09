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
# PERSONA CONFIGURATION WITH FALLBACK PRIORITY
# =============================
CONTENT_TYPES = {
    "fan_philosopher": {
        "style": "like a regular fan chatting about football life",
        "focus": "what it's really like to support a team, rivalries, matchday feelings",
        "hashtags": ["#FanLife", "#FootballCulture", "#Matchday"],
        "filter_keywords": ["fan", "support", "rivalry", "atmosphere", "passion", "feeling"],
        "fallback_priority": 1,
        "flexible": True
    },
    "tactical_nerd": {
        "style": "like a coach explaining things to friends at the pub",
        "focus": "formations, pressing, and subtle game changes",
        "hashtags": ["#Tactics", "#FootballTalk", "#GameAnalysis"],
        "filter_keywords": ["formation", "tactic", "press", "midfield", "defense", "system"],
        "fallback_priority": 2,
        "flexible": True
    },
    "data_driven": {
        "style": "like a stats fan who spots what others miss",
        "focus": "stats like xG, pass accuracy, and possession numbers",
        "hashtags": ["#FootballStats", "#Analytics", "#Data"],
        "filter_keywords": ["stats", "data", "xg", "expected", "percentage", "metric"],
        "fallback_priority": 3,
        "flexible": True
    },
    "transfer_whisperer": {
        "style": "like someone who follows transfer gossip but keeps it real",
        "focus": "transfers, contracts, rumors - talk about the business side",
        "hashtags": ["#TransferTalk", "#Rumors", "#SoccerNews"],
        "filter_keywords": ["transfer", "signing", "contract", "rumor", "agent", "deal"],
        "fallback_priority": 4,
        "flexible": True
    },
    "cultural_historian": {
        "style": "like an older fan sharing cool stories",
        "focus": "past games, legends, or historical moments",
        "hashtags": ["#Throwback", "#FootballHistory", "#OldSchool"],
        "filter_keywords": ["remember", "throwback", "199", "198", "classic", "legend"],
        "fallback_priority": 5,
        "flexible": False
    }
}

FLEXIBLE_PERSONAS = [name for name, config in CONTENT_TYPES.items() if config.get("flexible", True)]

# =============================
# OPTIMIZED HASHTAG STRATEGY
# =============================
# Core strategy: 1 persona-specific + 1-2 general = 2-3 total hashtags

PERSONA_HASHTAGS = {
    "fan_philosopher": ["#FanLife", "#FootballCulture", "#Matchday"],
    "tactical_nerd": ["#Tactics", "#GameAnalysis", "#FootballTalk"],
    "data_driven": ["#FootballStats", "#Analytics", "#Data"],
    "transfer_whisperer": ["#TransferTalk", "#Rumors", "#SoccerNews"],
    "cultural_historian": ["#Throwback", "#FootballHistory", "#OldSchool"]
}

GENERAL_HASHTAGS = [
    # High-value general tags (pick 1-2 from these)
    "#football", "#soccer", "#futbol",
    
    # League/competition tags (contextual)
    "#premierleague", "#laliga", "#bundesliga", "#ucl", "#championsleague",
    
    # High-engagement tags
    "#footballtwitter", "#soccertwitter"
]

# =============================
# HELPER FUNCTIONS
# =============================
def post_to_twitter(content):
    try:
        if len(content) > 280:
            content = content[:277] + "..."
        client_v2 = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        response = client_v2.create_tweet(text=content)
        return bool(response and response.data)
    except Exception as e:
        print(f"Twitter post error: {e}")
        return False

def clean_html(text):
    if not text: return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    return text.strip()

def get_optimized_hashtags(persona_name, count=3):
    """
    Returns 2-3 optimized hashtags:
    1. One persona-specific hashtag (core identity)
    2. 1-2 general high-value hashtags
    """
    persona_hashtags = PERSONA_HASHTAGS.get(persona_name, ["#football"])
    
    # Pick 1 persona-specific hashtag
    selected = [random.choice(persona_hashtags)]
    
    # Pick 1-2 general hashtags
    remaining = count - len(selected)
    if remaining > 0:
        selected.extend(random.sample(GENERAL_HASHTAGS, min(remaining, len(GENERAL_HASHTAGS))))
    
    return ' '.join(selected)

def filter_for_persona(entry, persona_name):
    title = entry['title'].lower()
    summary = entry['summary'].lower()
    persona = CONTENT_TYPES[persona_name]
    keywords = persona.get("filter_keywords", [])
    
    if persona_name == "cultural_historian":
        if any(keyword in title or keyword in summary for keyword in keywords):
            return True
        year_pattern = r'\b(19\d{2}|200\d|201[0-7])\b'
        if re.search(year_pattern, title) or re.search(year_pattern, summary):
            return True
        return False
    
    if keywords:
        return any(keyword in title or keyword in summary for keyword in keywords)
    return True

def adapt_content_to_persona(entry, persona_name):
    title = entry['title']
    
    adaptation_prompts = {
        "fan_philosopher": f"Take this football topic and turn it into a fan's perspective: '{title}'. Talk about how fans feel about it. Write a short 2-line tweet using natural, casual language.",
        "tactical_nerd": f"Find a tactical angle in this: '{title}'. How would a tactics enthusiast view this situation? Write a short 2-line tweet using natural language.",
        "data_driven": f"Look for statistical or data angles in: '{title}'. What numbers or metrics come to mind? Write a short 2-line tweet using natural language.",
        "transfer_whisperer": f"Find transfer/business angles in: '{title}'. Could this affect transfers or contracts? Write a short 2-line tweet using natural language.",
    }
    
    return adaptation_prompts.get(persona_name)

# =============================
# RSS PARSING
# =============================
def parse_reddit_rss():
    entries = []
    custom_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    feedparser.USER_AGENT = custom_headers['User-Agent']
    
    for url in random.sample(REDDIT_RSS_FEEDS, min(5, len(REDDIT_RSS_FEEDS))):
        try:
            response = requests.get(url, headers=custom_headers, timeout=10)
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:10]:
                if not hasattr(entry, 'link') or entry.link in posted_links:
                    continue
                
                title = clean_html(getattr(entry, 'title', ''))
                summary = clean_html(getattr(entry, 'summary', ''))
                
                if len(title) < 15:
                    continue
                
                entries.append({
                    'title': title,
                    'link': entry.link,
                    'summary': summary[:200] if summary else ''
                })
                
                if len(entries) >= 15:
                    break
                    
            if len(entries) >= 15:
                break
                
        except Exception as e:
            print(f"  Feed error: {e}")
            continue
    
    return entries

# =============================
# CONTENT GENERATION WITH FALLBACK SYSTEM
# =============================
def generate_with_persona(persona_name, entries, attempt_adaptation=True):
    persona = CONTENT_TYPES[persona_name]
    
    # 1. First try: Find matching content
    matching_entries = [e for e in entries if filter_for_persona(e, persona_name)]
    
    if matching_entries:
        print(f"  ✓ Found {len(matching_entries)} matching entries for {persona_name}")
        entry = random.choice(matching_entries)
        prompt = f"Write a short 2-line tweet as a {persona['style']} about: '{entry['title']}'. Use natural, casual language like a real person. No AI-sounding words."
    elif attempt_adaptation and persona.get("flexible", True):
        # 2. Second try: Adapt general content
        print(f"  ⚠️  No direct matches for {persona_name}, attempting adaptation...")
        general_entries = [e for e in entries if e['link'] not in posted_links]
        if general_entries:
            entry = random.choice(general_entries)
            adaptation = adapt_content_to_persona(entry, persona_name)
            if adaptation:
                prompt = adaptation
            else:
                return None, None
        else:
            return None, None
    else:
        # 3. This persona can't work with available content
        return None, None
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        if response and response.candidates:
            text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
            
            text = clean_ai_text(text)
            if text and len(text) > 20:
                # OPTIMIZED: Now using 2-3 hashtags instead of 5-6
                hashtags = get_optimized_hashtags(persona_name, count=random.randint(2, 3))
                final_tweet = format_tweet(text, hashtags)
                posted_links.add(entry['link'])
                return final_tweet, persona_name
                
    except Exception as e:
        print(f"  Generation error: {e}")
    
    return None, None

def clean_ai_text(text):
    text = text.strip()
    text = re.sub(r'\*\*|\*|__|_', '', text)
    ai_phrases = [r'\b(behold|thus|indeed|henceforth|hereby|wherein)\b',
                  r'\b(as an ai|as a language model|as an artificial)\b',
                  r'\b(in summary|in conclusion|to summarize)\b']
    for phrase in ai_phrases:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(reddit|subreddit|r/\w+)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(I|me|my|we|our|us)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    
    # Ensure 1-2 lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 2:
        text = '\n'.join(lines[:2])
    elif len(lines) == 1 and len(text) > 100:
        words = text.split()
        if len(words) > 15:
            mid = len(words) // 2
            text = ' '.join(words[:mid]) + '\n' + ' '.join(words[mid:])
    
    return text

def format_tweet(text, hashtags):
    tweet = text + "\n\n" + hashtags
    if len(tweet) > 280:
        text_max = 280 - len(hashtags) - 3
        text = text[:text_max].rsplit(' ', 1)[0]
        tweet = text + "\n\n" + hashtags
    return tweet

# =============================
# MAIN GENERATION WITH FALLBACK SYSTEM
# =============================
def generate_tweet():
    print("\n📊 Fetching content...")
    entries = parse_reddit_rss()
    
    if not entries:
        print("❌ No content found")
        return None, None
    
    print(f"✓ Found {len(entries)} total entries")
    
    # STRATEGY 1: Try original random persona first
    original_persona = random.choice(list(CONTENT_TYPES.keys()))
    print(f"\n🎯 Strategy 1: Trying original persona - {original_persona}")
    
    tweet, used_persona = generate_with_persona(original_persona, entries, attempt_adaptation=True)
    
    if tweet:
        print(f"  ✅ Success with {used_persona}")
        return tweet, used_persona
    
    # STRATEGY 2: Try flexible personas (can adapt any content)
    print(f"\n🔄 Strategy 2: Trying flexible personas...")
    for persona_name in FLEXIBLE_PERSONAS:
        if persona_name == original_persona:
            continue
            
        print(f"  Trying {persona_name}...")
        tweet, used_persona = generate_with_persona(persona_name, entries, attempt_adaptation=True)
        
        if tweet:
            print(f"    ✅ Adapted content for {used_persona}")
            return tweet, used_persona
    
    # STRATEGY 3: Last resort - general fan perspective
    print(f"\n⚡ Strategy 3: Using general fan perspective...")
    general_prompt = (
        f"Write a short 2-line tweet about football/soccer. "
        f"Sound like a real fan chatting casually. Use natural language. "
        f"Topic ideas: matchday feelings, fan experiences, or general football talk."
    )
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=general_prompt)
        if response and response.candidates:
            text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
            
            text = clean_ai_text(text)
            if text:
                # Even general tweets get optimized hashtags
                hashtags = get_optimized_hashtags("fan_philosopher", count=2)
                tweet = format_tweet(text, hashtags)
                print(f"  ✅ Created general fan tweet")
                return tweet, "fan_philosopher"
    except Exception as e:
        print(f"  General generation failed: {e}")
    
    print("\n❌ All generation strategies failed")
    return None, None

# =============================
# MAIN EXECUTION
# =============================
def main():
    print("=" * 50)
    print("⚽ Smart Soccer Bot - Optimized Hashtag Edition")
    print("=" * 50)
    
    # Check credentials
    required = [TWITTER_API_KEY, TWITTER_API_SECRET, 
                TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET, GEMINI_API_KEY]
    if not all(required):
        print("❌ Missing credentials")
        return
    
    print("✓ All systems ready")
    print(f"✓ Hashtag strategy: 2-3 optimized tags per tweet")
    print(f"✓ Persona flexibility: {len(FLEXIBLE_PERSONAS)} flexible, 1 specific")
    print(f"✓ Fallback system: 3-tier strategy")
    
    tweet, persona = generate_tweet()
    
    if not tweet:
        print("\n❌ Could not generate tweet")
        return
    
    print(f"\n" + "=" * 50)
    print(f"FINAL TWEET ({persona}):")
    print("=" * 50)
    print(tweet)
    print("=" * 50)
    print(f"Length: {len(tweet)} chars")
    print(f"Hashtags: {len(tweet.split('#') )-1} (optimized)")
    print("=" * 50)
    
    print("\n📤 Posting to Twitter...")
    if post_to_twitter(tweet):
        print("✅ Posted successfully!")
    else:
        print("❌ Post failed")

if __name__ == "__main__":
    main()