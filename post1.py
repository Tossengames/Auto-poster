import os
import requests
import random
import time
import json
import feedparser
from datetime import datetime
import pytrends
from pytrends.request import TrendReq
import re
import tweepy

# ================================
# CONFIGURATION
# ================================

# Get from GitHub Secrets
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
TWITTER_BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Expanded RSS Feeds - Tech + Game Dev
TECH_RSS_FEEDS = [
    'https://techcrunch.com/feed',
    'https://www.wired.com/feed/rss',
    'https://arstechnica.com/feed',
    'https://venturebeat.com/feed',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.mashable.com/mashable/tech',
    'https://www.digitaltrends.com/feed'
]

GAME_DEV_RSS_FEEDS = [
    'https://blog.unity.com/feed',
    'https://80.lv/feed/',
    'https://www.gamedeveloper.com/rss',
    'https://www.gamesindustry.biz/feed',
    'https://videogamemarketing.com/feed/',
    'https://www.indiedb.com/engine/unity/feed',
    'https://www.rockpapershotgun.com/feed',
    'https://kotaku.com/rss'
]

# Strategic Hashtags (shorter for Twitter)
STRATEGIC_HASHTAGS = [
    "#StrategicThinking", "#TechStrategy", "#GameDev",
    "#FutureTrends", "#Innovation", "#Leadership",
    "#OpinionPoll", "#IndustryDebate", "#DevThoughts"
]

# ================================
# TWITTER/X API FUNCTIONS
# ================================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret):
    """Post content to Twitter/X using Tweepy"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Authenticate with Twitter API
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Ensure content is within Twitter limits (280 chars)
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        # Post the tweet
        response = client.create_tweet(text=content)
        
        if response and response.data:
            tweet_id = response.data['id']
            print(f"🎉 Successfully tweeted! Tweet ID: {tweet_id}")
            return True
        else:
            print("❌ Twitter post failed: No response data")
            return False
            
    except tweepy.TweepyException as e:
        print(f"❌ Twitter API error: {e}")
        return False
    except Exception as e:
        print(f"💥 Twitter post error: {e}")
        return False

# ================================
# CONTENT GENERATION FUNCTIONS
# ================================

def fetch_tech_news_from_rss():
    """Fetch current tech news from RSS feeds - RANDOM SELECTION"""
    try:
        print("📰 Fetching latest tech news...")
        articles = fetch_news_from_feeds(TECH_RSS_FEEDS, "tech")
        
        # RANDOM SELECTION: Shuffle articles and pick random ones
        random.shuffle(articles)
        print(f"🎲 Randomly selected from {len(articles)} tech articles")
        return articles
        
    except Exception as e:
        print(f"❌ Tech RSS fetch error: {e}")
        return []

def fetch_game_dev_news_from_rss():
    """Fetch current game development news from RSS feeds - RANDOM SELECTION"""
    try:
        print("🎮 Fetching latest game dev news...")
        articles = fetch_news_from_feeds(GAME_DEV_RSS_FEEDS, "game dev")
        
        # RANDOM SELECTION: Shuffle articles and pick random ones
        random.shuffle(articles)
        print(f"🎲 Randomly selected from {len(articles)} game dev articles")
        return articles
        
    except Exception as e:
        print(f"❌ Game dev RSS fetch error: {e}")
        return []

def fetch_news_from_feeds(feed_list, category):
    """Generic function to fetch news from RSS feeds"""
    all_articles = []
    
    for rss_url in feed_list:
        try:
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                continue
            
            for entry in feed.entries[:3]:
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_date = datetime(*entry.published_parsed[:6])
                
                # Skip if article is too old
                if article_date and (datetime.now() - article_date).days > 3:
                    continue
                
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'published': article_date,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else rss_url.split('//')[-1].split('/')[0],
                    'category': category
                }
                all_articles.append(article)
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"⚠️ Error parsing {rss_url}: {e}")
            continue
    
    print(f"✅ Found {len(all_articles)} recent {category} articles")
    return all_articles

def get_google_trends_topics():
    """Get current trending topics"""
    try:
        print("📈 Checking Google Trends...")
        
        pytrends = TrendReq(hl='en-US', tz=360)
        trending_searches = pytrends.trending_searches(pn='united_states')
        
        trends = trending_searches[0].tolist()[:10]  # Get more trends for variety
        print(f"✅ Found trending topics: {trends}")
        return trends
        
    except Exception as e:
        print(f"❌ Google Trends error: {e}")
        return ['AI technology', 'gaming trends', 'tech innovation']

def generate_strategic_cta(topic, content_type):
    """Generate AI-powered strategic CTA"""
    prompt = f"""
    Create a sophisticated, strategic call-to-action for a Twitter post about {topic}.
    
    Content type: {content_type}
    
    Requirements:
    - Sound like a master strategist challenging conventional thinking
    - Pose a thought-provoking question that requires strategic analysis
    - Make readers feel they're part of an intellectual discussion
    - Avoid generic phrases like "what do you think"
    - Keep it under 100 characters for Twitter
    
    Examples of good CTAs:
    "The pattern reveals itself. Your strategic assessment?"
    "Most react. The insightful anticipate. Your perspective?"
    
    Return ONLY the CTA text.
    """
    
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                cta = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                cta = cta.replace('```', '').strip()
                cta = remove_ai_indicators(cta)
                print(f"🎯 AI-generated CTA: {cta}")
                return cta
    except Exception as e:
        print(f"❌ CTA generation error: {e}")
    
    # Fallback CTA
    return "Strategic implications worth discussing?"

def generate_tech_analysis_post(articles):
    """Generate sophisticated tech analysis post"""
    if not articles:
        return create_fallback_post('tech')
    
    # RANDOM SELECTION: Pick 1-2 random articles
    selected_articles = random.sample(articles, min(2, len(articles)))
    main_topic = selected_articles[0]['title']
    
    prompt = f"""
    Create a Twitter post analyzing technology trends with a sophisticated, strategic tone.
    Sound like a master strategist revealing patterns others miss.

    Recent tech developments:
    {chr(10).join([f"- {article['title']}" for article in selected_articles])}

    Writing style:
    - Sophisticated, strategic, intellectually superior
    - Connect developments to reveal larger patterns
    - Focus on strategic implications
    - Pose thought-provoking questions
    - Sound like you're revealing truths most overlook

    Structure:
    1. Start with an insightful observation
    2. Connect developments to show patterns
    3. Discuss strategic implications
    4. End with a provocative question (leave space for CTA)

    Important: 
    - DO NOT include a final CTA question - leave space for it to be added later.
    - Make it sound completely human-written. No AI phrasing.
    - Keep it under 180 characters to leave space for CTA and hashtags.
    - Be concise for Twitter format.

    Return ONLY the post text.
    """
    
    return generate_ai_content(prompt, selected_articles, 'tech', main_topic)

def generate_game_dev_post(articles):
    """Generate sophisticated game development post"""
    if not articles:
        return create_fallback_post('game dev')
    
    # RANDOM SELECTION: Pick 1-2 random articles
    selected_articles = random.sample(articles, min(2, len(articles)))
    main_topic = selected_articles[0]['title']
    
    prompt = f"""
    Create a Twitter post about game development with a strategic, mastermind tone.
    Analyze industry movements like a chess grandmaster anticipating moves.

    Recent game industry developments:
    {chr(10).join([f"- {article['title']}" for article in selected_articles])}

    Writing style:
    - Calculated, precise, intellectually superior
    - Reveal how developments create strategic opportunities
    - Focus on patterns rather than individual events
    - Sound like you understand the underlying game theory

    Structure:
    1. Start with a strategic observation
    2. Connect developments to show strategic landscape
    3. Discuss positioning and advantage
    4. End with a strategic insight (leave space for CTA)

    Important: 
    - DO NOT include a final CTA question - leave space for it to be added later.
    - Make it sound completely human-written. No AI phrasing.
    - Keep it under 180 characters to leave space for CTA and hashtags.
    - Be concise for Twitter format.

    Return ONLY the post text.
    """
    
    return generate_ai_content(prompt, selected_articles, 'game dev', main_topic)

def generate_trending_topic_post(trends):
    """Generate post about trending topics"""
    if not trends:
        return create_fallback_post('trending')
    
    main_topic = trends[0]
    
    prompt = f"""
    Create a Twitter post analyzing current trending topics with sophisticated strategic insight.
    Sound like an analyst who understands why things trend when they do.

    Current trending topics: {', '.join(trends[:3])}

    Writing style:
    - Strategic, analytical, intellectually curious
    - Explain the underlying reasons for these trends
    - Connect trends to larger cultural/technological shifts
    - Pose insightful questions

    Structure:
    1. Start with an observation about trend patterns
    2. Analyze what's driving these trends
    3. Discuss broader implications
    4. End with an analytical insight (leave space for CTA)

    Important: 
    - DO NOT include a final CTA question - leave space for it to be added later.
    - Make it sound completely human-written. No AI phrasing.
    - Keep it under 180 characters to leave space for CTA and hashtags.
    - Be concise for Twitter format.

    Return ONLY the post text.
    """
    
    return generate_ai_content(prompt, trends, 'trending', main_topic)

def generate_trend_based_opinion_poll(trends):
    """Generate opinion poll post based on trending topics"""
    if not trends:
        return create_opinion_fallback()
    
    # Select a trending topic for the poll
    poll_topic = random.choice(trends[:5])
    
    prompt = f"""
    Create a Twitter opinion poll post that sparks strategic debate about this trending topic: {poll_topic}
    
    Sound like a sophisticated industry analyst presenting strategic perspectives.
    
    Create a post that:
    1. Presents the trending topic as a strategic dilemma
    2. Offers 2-3 distinct strategic perspectives
    3. Formats it as clear options for discussion
    
    Format it exactly like this:
    [Your strategic analysis - 1-2 sentences max]
    
    The strategic question: [Pose the core question]
    
    Option A: [First perspective]
    Option B: [Second perspective]
    
    [Brief concluding thought]
    
    Make it sound completely human-written with sophisticated, strategic language.
    Keep it under 250 characters.
    
    Return ONLY the post text.
    """
    
    try:
        print(f"🗳️ Generating opinion poll about trending topic: {poll_topic}")
        
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                post_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                post_text = post_text.replace('```', '').strip()
                post_text = remove_ai_indicators(post_text)
                
                # Ensure proper formatting for poll options
                if "Option A:" not in post_text:
                    # Add poll formatting if missing
                    post_text += f"\n\nOption A: Immediate market capture\nOption B: Long-term differentiation"
                
                print(f"✅ Opinion poll created ({len(post_text)} chars)")
                return post_text
        else:
            print(f"❌ Poll generation error: {response.text}")
            
    except Exception as e:
        print(f"❌ Opinion poll generation error: {e}")
    
    return create_opinion_fallback(poll_topic)

def generate_ai_content(prompt, content, content_type, main_topic):
    """Generate content using AI and add AI-powered CTA"""
    try:
        print(f"🎭 Generating {content_type} post...")
        
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                post_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                post_text = post_text.replace('```', '').strip()
                
                # Add AI-generated CTA
                cta = generate_strategic_cta(main_topic, content_type)
                post_text += f"\n\n{cta}"
                
                # Add hashtags (fewer for Twitter)
                selected_hashtags = random.sample(STRATEGIC_HASHTAGS, 2)
                post_text += f"\n\n{' '.join(selected_hashtags)}"
                
                post_text = remove_ai_indicators(post_text)
                
                print(f"✅ {content_type.title()} post created ({len(post_text)} chars)")
                return post_text
        else:
            print(f"❌ AI generation error: {response.text}")
            
    except Exception as e:
        print(f"❌ {content_type} generation error: {e}")
    
    return create_fallback_post(content_type)

def remove_ai_indicators(text):
    """Remove any phrases that sound AI-generated"""
    ai_phrases = [
        "as an AI", "according to AI", "AI-generated", "language model",
        "based on the provided", "in this content", "the writer",
        "this analysis", "the author", "in this piece"
    ]
    
    for phrase in ai_phrases:
        text = text.replace(phrase, "")
        text = text.replace(phrase.title(), "")
    
    return ' '.join(text.split())

def create_fallback_post(content_type):
    """Create sophisticated fallback posts"""
    if content_type == 'tech':
        fallbacks = [
            "Tech evolution reveals strategic patterns most overlook. The convergence of AI, cloud, and edge computing reshapes digital interaction paradigms.",
            "Strategic advantage lies in understanding underlying currents that make developments inevitable. Forward-thinkers position for the next paradigm shift."
        ]
    elif content_type == 'game dev':
        fallbacks = [
            "Gaming's evolution shows fascinating patterns. Real battles are in distribution and community engagement—building moats beyond individual games.",
            "Player expectations evolve faster than studios adapt. It's about deeper engagement and authentic community, not just better graphics."
        ]
    else:
        fallbacks = [
            "Trends reveal collective psychology. The strategic mind looks beyond popularity to understand unmet needs driving adoption.",
            "Pattern recognition separates reactive from strategic. While most chase trends, the insightful analyze why ideas gain traction."
        ]
    
    post_text = random.choice(fallbacks)
    cta = generate_strategic_cta("industry trends", content_type)
    post_text += f"\n\n{cta}"
    
    selected_hashtags = random.sample(STRATEGIC_HASHTAGS, 2)
    post_text += f"\n\n{' '.join(selected_hashtags)}"
    
    return post_text

def create_opinion_fallback(topic=None):
    """Create fallback opinion poll"""
    if not topic:
        topic = "industry strategy"
    
    fallback_polls = [
        f"Strategic landscape around {topic} presents a compelling dilemma.\n\nThe question: Which approach delivers sustainable advantage?\n\nOption A: Market penetration & scaling\nOption B: Niche specialization\n\nYour strategic analysis?",
        
        f"Evolution of {topic} creates strategic crossroads.\n\nThe question: Optimal positioning in shifting landscape?\n\nOption A: First-mover advantage\nOption B: Fast-follower strategy\n\nYour perspective?"
    ]
    
    post_text = random.choice(fallback_polls)
    selected_hashtags = random.sample(STRATEGIC_HASHTAGS, 2)
    post_text += f"\n\n{' '.join(selected_hashtags)}"
    
    return post_text

# ================================
# POST TYPE SELECTOR
# ================================

def select_post_type():
    """Randomly select post type with weighted probability"""
    post_types = [
        ('tech', 0.3),        # 30% tech posts
        ('game_dev', 0.3),    # 30% game dev posts  
        ('trending', 0.2),    # 20% trending topics
        ('opinion_poll', 0.2) # 20% opinion polls
    ]
    
    choices, weights = zip(*post_types)
    return random.choices(choices, weights=weights)[0]

# ================================
# MAIN EXECUTION
# ================================

def main():
    print("🐦 Strategic Content Analyst - Twitter Edition")
    print("=" * 50)
    print("📰 Multi-Source Intelligence • AI-Powered CTAs")
    print("🗳️ Trend-Based Polls • Strategic Personality")
    print("=" * 50)
    
    # Validate configuration
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API secrets")
        return
        
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY secret")
        return
    
    print(f"✅ Twitter API Key: {'*' * 20}{TWITTER_API_KEY[-4:] if TWITTER_API_KEY else 'MISSING'}")
    print(f"✅ Gemini API Key: {'*' * 20}{GEMINI_API_KEY[-4:] if GEMINI_API_KEY else 'MISSING'}")
    print("")
    
    # Select post type
    post_type = select_post_type()
    print(f"🎯 Selected post type: {post_type.replace('_', ' ').title()}")
    
    # Gather content based on post type
    if post_type == 'tech':
        articles = fetch_tech_news_from_rss()
        post_text = generate_tech_analysis_post(articles)
        
    elif post_type == 'game_dev':
        articles = fetch_game_dev_news_from_rss()
        post_text = generate_game_dev_post(articles)
        
    elif post_type == 'trending':
        trends = get_google_trends_topics()
        post_text = generate_trending_topic_post(trends)
        
    else:  # opinion_poll
        trends = get_google_trends_topics()
        post_text = generate_trend_based_opinion_poll(trends)
    
    print(f"📝 Post preview: {post_text[:100]}...")
    print(f"📏 Character count: {len(post_text)}")
    
    # Post to Twitter
    print("\n🚀 Deploying strategic content to Twitter...")
    success = post_to_twitter(
        post_text, 
        TWITTER_API_KEY, 
        TWITTER_API_SECRET, 
        TWITTER_ACCESS_TOKEN, 
        TWITTER_ACCESS_TOKEN_SECRET
    )
    
    if success:
        print("\n✅ Strategic content successfully deployed to Twitter!")
        print(f"🎯 Post type: {post_type.replace('_', ' ').title()}")
        print("🤖 AI-generated CTAs and analysis")
        print("🧠 Sophisticated personality maintained")
    else:
        print("\n❌ Twitter deployment failed.")

if __name__ == "__main__":
    main()