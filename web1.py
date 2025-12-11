import os
import requests
import random
import time
import feedparser
from datetime import datetime
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
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# ================================
# RSS FEEDS - Web3, Tech, and General Web
# ================================

RSS_FEEDS = [
    # Web3 & Blockchain
    'https://blog.ethereum.org/feed.xml',
    'https://solana.com/news/rss',
    'https://consensys.io/blog/feed/',
    'https://www.paradigm.xyz/feed.xml',
    'https://a16zcrypto.com/feed/',
    'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'https://cointelegraph.com/rss',
    'https://decrypt.co/feed',
    'https://thedefiant.io/feed',
    
    # Web3 Security
    'https://blog.trailofbits.com/feed/',
    'https://medium.com/feed/immunefi',
    'https://rekt.news/feed/',
    'https://halborn.com/blog/feed/',
    'https://slowmist.medium.com/feed',
    'https://chainsecurity.com/news/feed/',
    'https://quantstamp.com/blog/feed/',
    'https://blog.openzeppelin.com/feed/',
    
    # General Tech & Web
    'https://techcrunch.com/feed/',
    'https://www.wired.com/feed/rss',
    'https://arstechnica.com/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://news.ycombinator.com/rss',
    'https://stackoverflow.blog/feed/',
    'https://github.blog/feed/',
    
    # AI & Developer Tools
    'https://openai.com/blog/rss/',
    'https://ai.googleblog.com/feed.xml',
    'https://www.anthropic.com/index.xml',
    'https://blog.cloudflare.com/rss/',
    'https://netflixtechblog.com/feed',
    
    # Protocol & Ecosystem Blogs
    'https://www.certik.com/resources/blog/rss',
    'https://www.peckshield.com/blog?format=rss',
    'https://blog.solidityscan.com/rss/',
    'https://mixbytes.io/blog/feed/',
    'https://blog.cyfrin.io/rss/'
]

# ================================
# CONTENT FILTERING
# ================================

def is_spam_or_irrelevant(article):
    """
    Filter out spam, promotions, and completely irrelevant content.
    Returns True if article should be filtered out.
    """
    title = article.get('title', '').lower()
    
    # Hard filters - clear spam/promotions
    spam_phrases = [
        'buy now', 'limited time offer', 'discount code', 'coupon code',
        'airdrop live', 'whitelist open', 'presale starting', 'ico launch',
        'investment opportunity', 'earn passive', 'double your',
        '100x potential', 'get rich quick', 'sign up bonus',
        'gambling', 'casino', 'betting', 'adult content'
    ]
    
    for phrase in spam_phrases:
        if phrase in title:
            return True
    
    return False

def is_recent(article_date):
    """Check if article is recent (within 3 days)"""
    if not article_date:
        return False
    return (datetime.now() - article_date).days <= 3

# ================================
# CONTENT GENERATION
# ================================

def fetch_articles():
    """Fetch and filter articles from all RSS feeds"""
    all_articles = []
    
    print(f"📡 Checking {len(RSS_FEEDS)} RSS feeds...")
    
    for rss_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                continue
                
            for entry in feed.entries[:5]:  # Check latest 5 entries
                # Parse date
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_date = datetime(*entry.published_parsed[:6])
                
                # Check recency
                if not is_recent(article_date):
                    continue
                
                # Extract image
                image_url = None
                if hasattr(entry, 'media_content') and entry.media_content:
                    for media in entry.media_content:
                        if 'url' in media and media.get('type', '').startswith('image'):
                            image_url = media['url']
                            break
                
                # Try other image sources
                if not image_url and hasattr(entry, 'links'):
                    for link in entry.links:
                        if hasattr(link, 'type') and link.type and 'image' in link.type:
                            image_url = link.href
                            break
                
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'published': article_date,
                    'source': feed.feed.get('title', rss_url),
                    'image_url': image_url
                }
                
                # Apply filters
                if not is_spam_or_irrelevant(article):
                    all_articles.append(article)
                    
        except Exception as e:
            continue  # Silently skip failed feeds
    
    print(f"✅ Found {len(all_articles)} recent articles")
    return all_articles

def categorize_article(article):
    """
    Determine the category of the article for appropriate content generation
    """
    title = article['title'].lower()
    summary = article.get('summary', '').lower()
    content = title + " " + summary
    
    # Define category keywords
    categories = {
        'web3_security': [
            'hack', 'exploit', 'vulnerability', 'breach', 'drain', 'stolen',
            'attack', 'reentrancy', 'flash loan', 'audit finding', 'critical bug',
            'rug pull', 'phishing', 'security flaw', 'risk', 'threat', 'mitigation'
        ],
        'web3_general': [
            'web3', 'blockchain', 'crypto', 'defi', 'nft', 'dao', 'dapp',
            'ethereum', 'bitcoin', 'solana', 'token', 'protocol', 'layer 2',
            'zk', 'zero knowledge', 'rollup', 'validator', 'staking'
        ],
        'tech_ai': [
            'ai', 'artificial intelligence', 'machine learning', 'llm',
            'gpt', 'anthropic', 'openai', 'deep learning', 'neural network',
            'model', 'training', 'inference', 'prompt engineering'
        ],
        'tech_development': [
            'code', 'programming', 'software', 'developer', 'github', 'git',
            'api', 'framework', 'library', 'tool', 'vs code', 'jetbrains',
            'docker', 'kubernetes', 'cloud', 'aws', 'azure', 'gcp'
        ],
        'tech_news': [
            'tech', 'technology', 'startup', 'funding', 'raise', 'series',
            'acquisition', 'merge', 'ipo', 'market', 'industry', 'trend'
        ]
    }
    
    # Score each category
    category_scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if keyword in content)
        category_scores[category] = score
    
    # Return the highest scoring category
    best_category = max(category_scores, key=category_scores.get)
    return best_category if category_scores[best_category] > 0 else 'tech_news'

def generate_content_prompt(article, category):
    """
    Generate appropriate prompt based on article category
    """
    title = article['title']
    summary = article['summary'][:500]
    
    base_prompt = f"""
    Create a Twitter post about this topic: {title}
    
    CONTEXT: {summary}
    
    FORMAT THE POST AS FOLLOWS:
    
    1. WHAT'S HAPPENING: Briefly explain the key development or news.
    2. WHY IT MATTERS: Explain the significance, impact, or broader implications.
    3. KEY TAKEAWAY: Provide 1-2 insights, implications, or things to watch.
    
    GUIDELINES:
    - Write in a concise, professional tone
    - Use plain language but maintain accuracy
    - Total length: 200-240 characters (leaving room for hashtags)
    - DO NOT use phrases like "As an AI" or "According to analysis"
    - Sound like a knowledgeable expert, not a robot
    - Make it genuinely useful and informative
    
    Return ONLY the post text (no hashtags, no explanations).
    """
    
    # Category-specific adjustments
    if category == 'web3_security':
        prompt_addition = """
        Focus on the security aspects: the vulnerability, impact, and how to protect against similar issues.
        """
    elif category == 'web3_general':
        prompt_addition = """
        Focus on Web3/blockchain innovation, adoption, or technical developments.
        """
    elif category == 'tech_ai':
        prompt_addition = """
        Focus on AI developments, capabilities, limitations, or implications.
        """
    elif category == 'tech_development':
        prompt_addition = """
        Focus on practical implications for developers, tools, or workflows.
        """
    else:
        prompt_addition = """
        Focus on the broader tech industry implications and trends.
        """
    
    return base_prompt + prompt_addition

def generate_structured_post(article):
    """
    Generate a post based on article category
    """
    # Determine category first
    category = categorize_article(article)
    print(f"📊 Article category: {category.replace('_', ' ').title()}")
    
    # Generate appropriate prompt
    prompt = generate_content_prompt(article, category)
    
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
                post_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                post_text = post_text.replace('```', '').strip()
                
                # Clean up any AI artifacts
                post_text = re.sub(r'\b(as an ai|according to|language model)\b', '', post_text, flags=re.IGNORECASE)
                post_text = ' '.join(post_text.split())  # Normalize whitespace
                
                return post_text, category
                
    except Exception as e:
        print(f"⚠️ Content generation failed: {e}")
    
    return None, category

def generate_relevant_hashtags(post_text, category):
    """Generate context-relevant hashtags based on category and content"""
    
    prompt = f"""
    Based on this {category.replace('_', ' ')} post, suggest 3-5 relevant hashtags:
    
    POST: {post_text}
    
    CATEGORY: {category.replace('_', ' ')}
    
    Requirements:
    - Include 2-3 popular hashtags in this category
    - Include 1-2 specific/niche hashtags related to the exact topic
    - All hashtags must be directly relevant
    - Return ONLY the hashtags as: #First #Second #Third
    
    Examples:
    - Web3 security: #Web3Security #Crypto #SmartContracts #DeFi
    - General Web3: #Web3 #Blockchain #Crypto #Innovation
    - AI news: #AI #ArtificialIntelligence #Tech #Innovation
    - Tech development: #Programming #Developer #Tech #Tools
    """
    
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=20
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                hashtags = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                hashtags = hashtags.replace('```', '').strip()
                
                # Validate hashtags
                hashtag_list = [h for h in hashtags.split() if h.startswith('#') and len(h) > 1]
                if len(hashtag_list) >= 2:
                    return ' '.join(hashtag_list[:5])
                    
    except Exception:
        pass
    
    # Fallback hashtags by category
    fallback_hashtags = {
        'web3_security': '#Web3Security #Crypto #Blockchain',
        'web3_general': '#Web3 #Blockchain #Crypto',
        'tech_ai': '#AI #Technology #Innovation',
        'tech_development': '#Tech #Development #Programming',
        'tech_news': '#Technology #TechNews #Innovation'
    }
    
    return fallback_hashtags.get(category, '#Tech #News #Update')

# ================================
# AI QUALITY CHECK
# ================================

def audit_post_quality(article, post_text, category):
    """
    AI-powered quality check to ensure post is useful and authentic
    Returns (is_approved, feedback_message)
    """
    prompt = f"""
    CRITICAL REVIEW: Evaluate this Twitter post.
    
    CATEGORY: {category.replace('_', ' ')}
    ORIGINAL ARTICLE TITLE: {article['title']}
    
    GENERATED POST: {post_text}
    
    EVALUATE ON THESE CRITERIA:
    1. USEFULNESS: Does it provide genuine value? (explains what's happening, why it matters, key takeaways)
    2. AUTHENTICITY: Does it sound like a human expert wrote it? (not AI-generated)
    3. RELEVANCE: Is it relevant to the category/topic?
    4. CLARITY: Is it clear and understandable?
    5. ACTIONABLE/INSIGHTFUL: Does it provide practical insights or valuable information?
    
    SCORING:
    - APPROVED: Meets all criteria, post is valuable and authentic
    - REJECTED: Fails any criteria
    
    If REJECTED, provide brief reason.
    
    Return EXACTLY ONE OF THESE FORMATS:
    APPROVED
    or
    REJECTED: [specific reason]
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
                result = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                if result.startswith('APPROVED'):
                    return True, "Post approved by quality check"
                elif result.startswith('REJECTED:'):
                    return False, result[9:].strip()
                    
    except Exception as e:
        print(f"⚠️ Quality check failed: {e}")
    
    # Default to rejection if check fails
    return False, "Quality check system error"

# ================================
# TWITTER POSTING
# ================================

def post_to_twitter(content, image_url=None):
    """Post content to Twitter/X"""
    try:
        # Ensure content length
        if len(content) > 280:
            content = content[:277] + "..."
        
        media_ids = []
        
        # Handle image if provided
        if image_url:
            try:
                # Clean URL
                clean_url = image_url.split('?')[0].split('&#')[0]
                
                # Download image
                response = requests.get(clean_url, timeout=30)
                if response.status_code == 200:
                    # Save temp file
                    temp_file = "/tmp/tweet_image.jpg"
                    with open(temp_file, "wb") as f:
                        f.write(response.content)
                    
                    # Upload to Twitter
                    auth_v1 = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
                    auth_v1.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
                    api_v1 = tweepy.API(auth_v1)
                    
                    media = api_v1.media_upload(filename=temp_file)
                    media_ids.append(media.media_id_string)
                    
                    # Clean up
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        
            except Exception:
                pass  # Continue without image
        
        # Post tweet
        client_v2 = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        
        if media_ids:
            response = client_v2.create_tweet(text=content, media_ids=media_ids)
        else:
            response = client_v2.create_tweet(text=content)
        
        if response and response.data:
            print(f"✅ Tweet posted successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Twitter posting failed: {e}")
    
    return False

# ================================
# MAIN EXECUTION FLOW
# ================================

def main():
    print("=" * 60)
    print("🤖 TECH & WEB3 CONTENT GENERATOR")
    print("=" * 60)
    print("✓ Categorizes content (Web3, Security, AI, Dev, Tech)")
    print("✓ Structured format (What/Why/Key Takeaway)")
    print("✓ 30+ RSS feeds for diverse content")
    print("✓ AI quality check for usefulness")
    print("=" * 60)
    
    # Validate environment
    if not GEMINI_API_KEY:
        print("❌ Missing Gemini API key")
        return
        
    twitter_creds = [TWITTER_API_KEY, TWITTER_API_SECRET, 
                    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]
    if not all(twitter_creds):
        print("❌ Missing Twitter API credentials")
        return
    
    # Step 1: Fetch articles
    articles = fetch_articles()
    
    if not articles:
        print("No suitable articles found. Exiting.")
        return
    
    # Step 2: Select random article
    article = random.choice(articles)
    print(f"\n📰 Selected article: {article['title'][:80]}...")
    print(f"📅 Published: {article['published'].strftime('%Y-%m-%d') if article['published'] else 'Unknown'}")
    
    # Step 3: Generate structured post
    print("\n🤖 Generating structured post...")
    post_text, category = generate_structured_post(article)
    
    if not post_text:
        print("❌ Failed to generate post content")
        return
    
    # Step 4: Generate hashtags
    hashtags = generate_relevant_hashtags(post_text, category)
    full_post = f"{post_text} {hashtags}"
    
    # Step 5: AI quality check
    print("\n🔍 Running AI quality audit...")
    is_approved, feedback = audit_post_quality(article, post_text, category)
    
    if not is_approved:
        print(f"❌ POST REJECTED: {feedback}")
        print(f"\nGenerated post was:\n{post_text}")
        return
    
    print(f"✅ QUALITY CHECK PASSED: {feedback}")
    
    # Step 6: Final length check
    if len(full_post) > 280:
        # Trim main content, preserve hashtags
        hashtag_part = ' ' + hashtags
        max_content = 280 - len(hashtag_part) - 3  # Leave room for "..."
        if max_content > 50:  # Ensure we have meaningful content
            main_content = post_text[:max_content].rsplit(' ', 1)[0] + "..."
            full_post = main_content + hashtag_part
        else:
            full_post = full_post[:277] + "..."
    
    # Step 7: Preview and confirm
    print("\n" + "=" * 60)
    print("📝 FINAL POST PREVIEW:")
    print("=" * 60)
    print(full_post)
    print("=" * 60)
    print(f"Character count: {len(full_post)}")
    print(f"Category: {category.replace('_', ' ').title()}")
    print(f"Hashtags: {len([h for h in full_post.split() if h.startswith('#')])}")
    
    # Step 8: Post to Twitter
    print("\n🚀 Posting to Twitter...")
    success = post_to_twitter(full_post, article.get('image_url'))
    
    if success:
        print("🎉 Content successfully published!")
    else:
        print("⚠️ Failed to publish (but content passed quality checks)")

if __name__ == "__main__":
    main()