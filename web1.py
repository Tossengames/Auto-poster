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
# WEB3 SECURITY RSS FEEDS (20+ Sources)
# ================================

RSS_FEEDS = [
    # Core Security Research & Blogs
    'https://blog.trailofbits.com/feed/',
    'https://medium.com/feed/immunefi',
    'https://rekt.news/feed/',
    'https://halborn.com/blog/feed/',
    'https://slowmist.medium.com/feed',
    'https://chainsecurity.com/news/feed/',
    'https://quantstamp.com/blog/feed/',
    'https://blog.openzeppelin.com/feed/',
    
    # Major Crypto/Web3 Media
    'https://consensys.io/blog/feed/',
    'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'https://cointelegraph.com/rss',
    'https://decrypt.co/feed',
    'https://thedefiant.io/feed',
    
    # Audit Firms & Security Companies
    'https://www.certik.com/resources/blog/rss',
    'https://www.peckshield.com/blog?format=rss',
    'https://blog.solidityscan.com/rss/',
    'https://mixbytes.io/blog/feed/',
    'https://blog.cyfrin.io/rss/',
    
    # Protocol & Ecosystem Blogs
    'https://blog.ethereum.org/feed.xml',
    'https://solana.com/news/rss',
    'https://www.paradigm.xyz/feed.xml',
    'https://a16zcrypto.com/feed/'
]

# ================================
# CONTENT FILTERING
# ================================

def is_spam_or_irrelevant(article):
    """
    Filter out spam, promotions, and non-Web3 content.
    Returns True if article should be filtered out.
    """
    title = article.get('title', '').lower()
    
    # Hard filters - clear spam/promotions
    spam_phrases = [
        'buy now', 'limited time offer', 'discount code', 'coupon code',
        'airdrop live', 'whitelist open', 'presale starting', 'ico launch',
        'investment opportunity', 'earn passive', 'double your',
        '100x potential', 'get rich quick', 'sign up bonus'
    ]
    
    for phrase in spam_phrases:
        if phrase in title:
            return True
    
    # Soft filters - might be irrelevant to Web3 security
    irrelevant_indicators = [
        'price prediction', 'market analysis', 'trading tips',
        'exchange listing', 'partnership announcement', 'mainnet launch',
        'tokenomics explained', 'roadmap update', 'ama announcement'
    ]
    
    # Check if title contains Web3 security relevance
    # If it doesn't have security terms AND has irrelevant terms, filter
    has_security_terms = any(term in title for term in 
        ['hack', 'exploit', 'vulnerability', 'security', 'audit', 
         'breach', 'attack', 'risk', 'threat', 'flash loan', 'reentrancy'])
    
    has_irrelevant_terms = any(term in title for term in irrelevant_indicators)
    
    if has_irrelevant_terms and not has_security_terms:
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
    
    print(f"✅ Found {len(all_articles)} recent, relevant articles")
    return all_articles

def generate_structured_post(article):
    """
    Generate a post with: What Happened, Why It Matters, What To Do
    """
    title = article['title']
    summary = article['summary'][:500]  # Limit summary length
    
    prompt = f"""
    Create a Twitter post about this Web3 security incident/development:
    
    TITLE: {title}
    
    CONTEXT: {summary}
    
    FORMAT THE POST AS FOLLOWS:
    
    1. WHAT HAPPENED: Briefly explain the security incident or development.
    2. WHY IT MATTERS: Explain the significance, impact, or broader implications.
    3. WHAT TO DO: Provide 1-2 actionable security recommendations or takeaways.
    
    GUIDELINES:
    - Write in a concise, professional tone (like a security analyst)
    - Use plain language but include technical accuracy
    - Total length: 220-250 characters (leaving room for hashtags)
    - DO NOT use phrases like "As an AI" or "According to analysis"
    - Sound like a human security expert, not a robot
    - Make it genuinely useful for developers/investors
    
    Return ONLY the post text (no hashtags, no explanations).
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
                post_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                post_text = post_text.replace('```', '').strip()
                
                # Clean up any AI artifacts
                post_text = re.sub(r'\b(as an ai|according to|language model)\b', '', post_text, flags=re.IGNORECASE)
                post_text = ' '.join(post_text.split())  # Normalize whitespace
                
                return post_text
                
    except Exception as e:
        print(f"⚠️ Content generation failed: {e}")
    
    return None

def generate_relevant_hashtags(article_title, post_text):
    """Generate context-relevant hashtags"""
    prompt = f"""
    Based on this Web3 security post, suggest 3-4 relevant hashtags:
    
    POST: {post_text}
    
    Requirements:
    - Include 1-2 popular Web3 security hashtags
    - Include 1-2 specific/niche hashtags related to the topic
    - All hashtags must be directly relevant
    - Return ONLY the hashtags as: #First #Second #Third
    
    Examples:
    - For smart contract exploit: #Web3Security #SmartContracts #DeFi
    - For wallet security: #CryptoSecurity #WalletSafety #Web3
    - For audit findings: #SecurityAudit #Blockchain #SmartContracts
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
                    return ' '.join(hashtag_list[:4])
                    
    except Exception:
        pass
    
    # Fallback to general security hashtags
    return "#Web3Security #Blockchain #Crypto"

# ================================
# AI QUALITY CHECK
# ================================

def audit_post_quality(article, post_text):
    """
    AI-powered quality check to ensure post is useful and authentic
    Returns (is_approved, feedback_message)
    """
    prompt = f"""
    CRITICAL REVIEW: Evaluate this Twitter post about a Web3 security topic.
    
    ORIGINAL ARTICLE TITLE: {article['title']}
    
    GENERATED POST: {post_text}
    
    EVALUATE ON THESE CRITERIA:
    1. USEFULNESS: Does it provide genuine value? (explains what happened, why it matters, what to do)
    2. AUTHENTICITY: Does it sound like a human security expert wrote it? (not AI-generated)
    3. RELEVANCE: Is it actually about Web3/blockchain security?
    4. CLARITY: Is it clear and understandable?
    5. ACTIONABLE: Does it provide practical insights or recommendations?
    
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
    print("🔐 WEB3 SECURITY CONTENT GENERATOR")
    print("=" * 60)
    print("✓ Structured format (What/Why/What To Do)")
    print("✓ 20+ RSS feeds for diverse content")
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
    post_text = generate_structured_post(article)
    
    if not post_text:
        print("❌ Failed to generate post content")
        return
    
    # Step 4: Generate hashtags
    hashtags = generate_relevant_hashtags(article['title'], post_text)
    full_post = f"{post_text} {hashtags}"
    
    # Step 5: AI quality check
    print("\n🔍 Running AI quality audit...")
    is_approved, feedback = audit_post_quality(article, post_text)
    
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