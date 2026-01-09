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
# REDDIT RSS FEEDS
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
# PERSONA CONFIGURATION
# =============================
CONTENT_TYPES = {
    "fan_philosopher": {
        "style": "regular fan chatting",
        "focus": "fan feelings and matchday experiences",
        "hashtags": ["#FanLife", "#FootballCulture", "#Matchday"],
        "filter_keywords": ["fan", "support", "rivalry", "atmosphere", "passion"],
        "flexible": True,
        "prompt_examples": [
            "Nothing beats that pre-match buzz. Even the nervous wait is part of it! 😅",
            "Derby day tension hits different. Can't explain it to non-fans. ⚽"
        ]
    },
    "tactical_nerd": {
        "style": "tactics enthusiast explaining simply",
        "focus": "formations, pressing, game plans",
        "hashtags": ["#Tactics", "#GameAnalysis", "#FootballTalk"],
        "filter_keywords": ["formation", "tactic", "press", "midfield", "defense"],
        "flexible": True,
        "prompt_examples": [
            "That high press completely disrupted their buildup from the back.",
            "Switching to a back three in the second half changed everything."
        ]
    },
    "data_driven": {
        "style": "stats fan noticing patterns",
        "focus": "xG, possession stats, key metrics",
        "hashtags": ["#FootballStats", "#Analytics", "#Data"],
        "filter_keywords": ["stats", "data", "xg", "expected", "percentage"],
        "flexible": True,
        "prompt_examples": [
            "65% possession but only 1 shot on target. What's the point?",
            "xG says they should've scored 2.5 goals. Finishing let them down."
        ]
    },
    "transfer_whisperer": {
        "style": "transfer gossip follower",
        "focus": "transfers, contracts, rumors",
        "hashtags": ["#TransferTalk", "#Rumors", "#SoccerNews"],
        "filter_keywords": ["transfer", "signing", "contract", "rumor", "agent"],
        "flexible": True,
        "prompt_examples": [
            "Hearing whispers about a big summer move for that midfielder.",
            "That contract situation is getting messy. Could see him leaving."
        ]
    },
    "cultural_historian": {
        "style": "older fan sharing memories",
        "focus": "historical moments and legends",
        "hashtags": ["#Throwback", "#FootballHistory", "#OldSchool"],
        "filter_keywords": ["remember", "throwback", "classic", "legend", "iconic"],
        "flexible": False,
        "prompt_examples": [
            "Remember that 2005 final? Still gives me goosebumps.",
            "Zidane's volley in '02. Perfection that never gets old. 🎯"
        ]
    }
}

FLEXIBLE_PERSONAS = [name for name, config in CONTENT_TYPES.items() if config.get("flexible", True)]

# =============================
# HASHTAG STRATEGY
# =============================
GENERAL_HASHTAGS = ["#football", "#soccer", "#premierleague", "#laliga", "#ucl", "#footballtwitter"]

def get_optimized_hashtags(persona_name):
    persona_tags = CONTENT_TYPES[persona_name]["hashtags"]
    selected = [random.choice(persona_tags)]
    selected.append(random.choice(GENERAL_HASHTAGS))
    if random.random() > 0.5:  # 50% chance for third tag
        selected.append(random.choice([tag for tag in GENERAL_HASHTAGS if tag not in selected]))
    return ' '.join(selected)

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

def filter_for_persona(entry, persona_name):
    title = entry['title'].lower()
    summary = entry['summary'].lower()
    keywords = CONTENT_TYPES[persona_name].get("filter_keywords", [])
    
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

# =============================
# RSS PARSING
# =============================
def parse_reddit_rss():
    entries = []
    custom_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    feedparser.USER_AGENT = custom_headers['User-Agent']
    
    for url in random.sample(REDDIT_RSS_FEEDS, min(3, len(REDDIT_RSS_FEEDS))):
        try:
            response = requests.get(url, headers=custom_headers, timeout=10)
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:8]:
                if not hasattr(entry, 'link') or entry.link in posted_links:
                    continue
                
                title = clean_html(getattr(entry, 'title', ''))
                if len(title) < 20 or "?" in title:  # Skip questions
                    continue
                
                entries.append({
                    'title': title,
                    'link': entry.link,
                    'summary': clean_html(getattr(entry, 'summary', ''))[:150]
                })
                
                if len(entries) >= 10:
                    break
                    
            if len(entries) >= 10:
                break
                
        except Exception:
            continue
    
    return entries

# =============================
# STRICT TWEET GENERATION
# =============================
def generate_natural_tweet(persona_name, entry):
    persona = CONTENT_TYPES[persona_name]
    examples = "\n".join(persona["prompt_examples"])
    
    # STRICTER PROMPT - forces natural output
    prompt = f"""Write ONLY the tweet text, nothing else.

As a {persona['style']}, write a short 2-line tweet about this football topic:
"{entry['title']}"

REQUIREMENTS:
- Sound like a real person having a casual conversation
- Maximum 2 lines total
- Use natural, everyday language
- Absolutely NO explanations, NO "here's a tactical angle", NO AI phrases
- Just write the tweet as if you're texting a friend

Good examples from your style:
{examples}

Now write your tweet about "{entry['title'][:50]}...":"""
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        if response and response.candidates:
            text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
            
            # STRICT CLEANING
            text = text.strip()
            
            # Remove any explanatory prefixes
            prefixes_to_remove = [
                r'^Tweet:\s*', r'^Here(?:.*?)tweet:\s*', r'^As a.*?:?\s*',
                r'^From.*?perspective:\s*', r'^.*?angle.*?:?\s*'
            ]
            for prefix in prefixes_to_remove:
                text = re.sub(prefix, '', text, flags=re.IGNORECASE)
            
            # Remove AI analysis phrases
            ai_phrases = [
                r'\b(?:here is|here\'s|this is|tactical angle|analysis|perspective|take|viewpoint)\b.*?:',
                r'^.*?looking at.*?:',
                r'^.*?considering.*?:'
            ]
            for phrase in ai_phrases:
                text = re.sub(phrase, '', text, flags=re.IGNORECASE)
            
            text = re.sub(r'\*\*|\*|__|_', '', text)
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n+', '\n', text)
            
            # Ensure it's exactly the tweet
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if not lines:
                return None
            
            # Take first 2 lines that look like a tweet (not explanations)
            tweet_lines = []
            for line in lines:
                if len(line) > 10 and not line.lower().startswith(('tweet', 'here', 'as a', 'from', 'analysis')):
                    tweet_lines.append(line)
                if len(tweet_lines) >= 2:
                    break
            
            if not tweet_lines:
                return None
            
            tweet_text = '\n'.join(tweet_lines[:2])
            
            # Final naturalness check
            if any(word in tweet_text.lower() for word in ['tactical angle', 'perspective', 'analysis', 'here is']):
                return None
            
            if len(tweet_text) < 15 or len(tweet_text) > 180:
                return None
            
            return tweet_text
            
    except Exception as e:
        print(f"  Generation error: {e}")
    
    return None

def generate_with_persona(persona_name, entries):
    persona = CONTENT_TYPES[persona_name]
    
    # Try matching content first
    matching_entries = [e for e in entries if filter_for_persona(e, persona_name)]
    if not matching_entries and persona.get("flexible", True):
        matching_entries = [e for e in entries if e['link'] not in posted_links]
    
    if not matching_entries:
        return None, None
    
    for entry in random.sample(matching_entries, min(3, len(matching_entries))):
        print(f"  Trying: {entry['title'][:60]}...")
        tweet_text = generate_natural_tweet(persona_name, entry)
        
        if tweet_text:
            hashtags = get_optimized_hashtags(persona_name)
            final_tweet = tweet_text + "\n\n" + hashtags
            
            if len(final_tweet) <= 280:
                posted_links.add(entry['link'])
                return final_tweet, persona_name
    
    return None, None

# =============================
# MAIN GENERATION
# =============================
def generate_tweet():
    print("\n📊 Fetching content...")
    entries = parse_reddit_rss()
    
    if not entries:
        print("❌ No content found")
        return None, None
    
    print(f"✓ Found {len(entries)} entries")
    
    # Try original persona
    original_persona = random.choice(list(CONTENT_TYPES.keys()))
    print(f"\n🎯 Trying {original_persona}...")
    
    tweet, used_persona = generate_with_persona(original_persona, entries)
    
    if tweet:
        print(f"  ✅ Success with natural tweet")
        return tweet, used_persona
    
    # Try flexible personas
    print(f"\n🔄 Trying other personas...")
    for persona_name in FLEXIBLE_PERSONAS:
        if persona_name == original_persona:
            continue
        
        print(f"  Trying {persona_name}...")
        tweet, used_persona = generate_with_persona(persona_name, entries)
        
        if tweet:
            print(f"    ✅ Adapted successfully")
            return tweet, used_persona
    
    # Fallback: simple fan tweet
    print(f"\n⚡ Creating simple fan tweet...")
    fallback_prompts = [
        "Matchday feeling is back. Nothing quite like it! ⚽",
        "Football's simple pleasures. A good game, some banter. Perfect. 😅",
        "That pre-kickoff anticipation. Gets me every time!"
    ]
    
    tweet_text = random.choice(fallback_prompts)
    hashtags = get_optimized_hashtags("fan_philosopher")
    tweet = tweet_text + "\n\n" + hashtags
    posted_links.add("fallback_" + str(time.time()))
    
    return tweet, "fan_philosopher"

# =============================
# MAIN EXECUTION
# =============================
def main():
    print("=" * 50)
    print("⚽ Natural Soccer Bot - Human-Like Tweets")
    print("=" * 50)
    
    # Check credentials
    required = [TWITTER_API_KEY, TWITTER_API_SECRET, 
                TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET, GEMINI_API_KEY]
    if not all(required):
        print("❌ Missing credentials")
        return
    
    print("✓ Systems ready")
    print("✓ Natural language enforcement: STRICT")
    print("✓ Hashtags: 2-3 optimized")
    
    tweet, persona = generate_tweet()
    
    if not tweet:
        print("\n❌ Could not generate tweet")
        return
    
    print(f"\n" + "=" * 50)
    print(f"FINAL TWEET ({persona}):")
    print("=" * 50)
    print(tweet)
    print("=" * 50)
    print(f"Length: {len(tweet)} chars | Hashtags: {len(tweet.split('#') )-1}")
    print("=" * 50)
    
    print("\n📤 Posting...")
    if post_to_twitter(tweet):
        print("✅ Posted successfully!")
    else:
        print("❌ Post failed")

if __name__ == "__main__":
    main()