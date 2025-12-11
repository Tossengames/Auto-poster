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
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Web3 Security RSS Feeds - Quality security sources
WEB3_SECURITY_RSS_FEEDS = [
    'https://blog.trailofbits.com/feed/',
    'https://medium.com/feed/immunefi',
    'https://rekt.news/feed/',
    'https://halborn.com/blog/feed/',
    'https://slowmist.medium.com/feed',
    'https://consensys.io/blog/feed/',
    'https://blog.openzeppelin.com/feed/',
    'https://chainsecurity.com/news/feed/',
    'https://quantstamp.com/blog/feed/'
]

# Security categories for targeted content
SECURITY_CATEGORIES = [
    'smart-contract',
    'blockchain',
    'defi-security',
    'wallet-security',
    'governance',
    'cryptography',
    'zero-knowledge',
    'audit-findings',
    'vulnerability',
    'incident-analysis'
]

# Promotional keywords to filter out
PROMOTIONAL_KEYWORDS = [
    'discount', 'sale', 'coupon', 'promo', 'deal', 'offer', 'limited time',
    'buy now', 'shop', 'store', 'price drop', 'save', 'percent off',
    'exclusive offer', 'special offer', 'flash sale', 'sponsored',
    'advertisement', 'affiliate', 'partner', 'promotion', 'bundle',
    'free trial', 'subscribe', 'sign up', 'get started', 'token sale',
    'ico', 'ido', 'presale', 'airdrop', 'whitelist', 'mint'
]

# Post styles for variety - focused on security expertise
POST_STYLES = [
    "security_analyst",
    "technical_researcher", 
    "incident_responder",
    "auditor_perspective",
    "cryptography_expert",
    "defi_security"
]

# ================================
# WEB3 SECURITY HASHTAGS DATABASE
# ================================

WEB3_SECURITY_HASHTAGS = {
    "general": ["#Web3Security", "#BlockchainSecurity", "#CryptoSecurity", "#DeFiSecurity"],
    "smart_contract": ["#SmartContracts", "#Solidity", "#Audit", "#Vulnerability"],
    "incident": ["#IncidentResponse", #Rekt", "#Exploit", "#SecurityAlert"],
    "tools": ["#SecurityTools", #Auditing", #StaticAnalysis", "#Fuzzing"],
    "privacy": ["#ZeroKnowledge", #ZKP", #Privacy", #Cryptography"],
    "research": ["#SecurityResearch", #BugBounty", #WhiteHat", #Hack"],
    "layer": ["#Layer2Security", #ZKProofs", #Rollups", #L2"],
    "trending": ["#Crypto", #Blockchain", #Ethereum", #Bitcoin"]
}

# ================================
# CONTENT FILTERING FUNCTIONS
# ================================

def is_promotional_content(article):
    """Check if article contains promotional content"""
    title = article.get('title', '').lower()
    summary = article.get('summary', '').lower()
    
    # Check for promotional keywords
    for keyword in PROMOTIONAL_KEYWORDS:
        if keyword in title or keyword in summary:
            print(f"🚫 Filtered out promotional content: {keyword}")
            return True
    
    # Check for sponsored indicators
    if 'sponsored' in title or 'sponsored' in summary:
        print(f"🚫 Filtered out sponsored content")
        return True
    
    return False

def is_quality_security_content(article):
    """Check if article is genuine security content with technical depth"""
    title = article.get('title', '').lower()
    summary = article.get('summary', '').lower()
    
    # Positive indicators of quality security content
    quality_indicators = [
        'security', 'vulnerability', 'exploit', 'attack', 'audit',
        'breach', 'hack', 'incident', 'analysis', 'research',
        'finding', 'bug', 'flaw', 'risk', 'threat', 'mitigation',
        'smart contract', 'solidity', 'defi', 'wallet', 'bridge',
        'governance', 'cryptography', 'zero knowledge', 'zk', 
        'formal verification', 'static analysis', 'fuzzing',
        'reentrancy', 'oracle', 'flash loan', 'front-running'
    ]
    
    # Check if content has technical depth
    content = title + " " + summary
    technical_score = sum(1 for indicator in quality_indicators if indicator in content)
    
    return technical_score >= 2  # Require at least 2 security-related terms

def filter_articles(articles):
    """Filter out promotional and low-quality articles"""
    filtered_articles = []
    
    for article in articles:
        if not is_promotional_content(article) and is_quality_security_content(article):
            filtered_articles.append(article)
        else:
            print(f"🚫 Filtered out: {article['title'][:60]}...")
    
    print(f"✅ Filtered {len(articles)} -> {len(filtered_articles)} quality security articles")
    return filtered_articles

# ================================
# TWITTER/X API FUNCTIONS
# ================================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret, image_url=None):
    """Post content to Twitter/X with optional image"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Ensure content is within Twitter limits
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        # Upload media if image exists
        media_ids = []
        if image_url:
            print(f"📤 Uploading media from {image_url}...")
            
            # Clean up image URL
            clean_image_url = image_url.split('?')[0].split('&#')[0]
            
            # Use v1.1 API for media upload
            auth_v1 = tweepy.OAuthHandler(api_key, api_secret)
            auth_v1.set_access_token(access_token, access_token_secret)
            api_v1 = tweepy.API(auth_v1)
            
            # Download image and upload
            try:
                response = requests.get(clean_image_url, timeout=30)
                response.raise_for_status()
                
                # Save temporarily
                temp_file = "/tmp/tweet_image.jpg"
                with open(temp_file, "wb") as f:
                    f.write(response.content)
                
                # Check file size
                file_size = os.path.getsize(temp_file)
                if file_size > 5 * 1024 * 1024:  # 5MB limit
                    print(f"⚠️ Image too large ({file_size} bytes), skipping...")
                else:
                    media = api_v1.media_upload(filename=temp_file)
                    media_ids.append(media.media_id_string)
                    print(f"✅ Media uploaded successfully! ID: {media.media_id_string}")
                
                # Clean up
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            except Exception as e:
                print(f"⚠️ Failed to download/upload image: {e}")
                # Continue without image
        
        # Create tweet using v2
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Post the tweet
        if media_ids:
            response = client_v2.create_tweet(text=content, media_ids=media_ids)
        else:
            response = client_v2.create_tweet(text=content)
        
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

def fetch_web3_security_news():
    """Fetch current web3 security news from RSS feeds"""
    try:
        print("🔐 Fetching latest Web3 security news...")
        articles = fetch_news_from_feeds(WEB3_SECURITY_RSS_FEEDS, "web3 security")
        
        # Filter out promotional content
        filtered_articles = filter_articles(articles)
        
        random.shuffle(filtered_articles)
        print(f"🎲 Randomly selected from {len(filtered_articles)} quality security articles")
        return filtered_articles
        
    except Exception as e:
        print(f"❌ Security RSS fetch error: {e}")
        return []

def fetch_news_from_feeds(feed_list, category):
    """Generic function to fetch news from RSS feeds"""
    all_articles = []
    
    for rss_url in feed_list:
        try:
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                continue
            
            for entry in feed.entries[:10]:  # Get more entries to filter from
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_date = datetime(*entry.published_parsed[:6])
                
                # Skip if article is too old (1 week for security)
                if article_date and (datetime.now() - article_date).days > 7:
                    continue
                
                # Extract image from entry
                image_url = extract_image_from_entry(entry)
                
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'published': article_date,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else rss_url.split('//')[-1].split('/')[0],
                    'category': category,
                    'image_url': image_url
                }
                all_articles.append(article)
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"⚠️ Error parsing {rss_url}: {e}")
            continue
    
    print(f"✅ Found {len(all_articles)} recent {category} articles")
    return all_articles

def extract_image_from_entry(entry):
    """Extract image URL from RSS entry"""
    try:
        # Check multiple possible locations for images
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if 'url' in media and media.get('type', '').startswith('image'):
                    return media['url']
        
        if hasattr(entry, 'links'):
            for link in entry.links:
                if hasattr(link, 'type') and link.type and 'image' in link.type:
                    return link.href
        
        # Try to extract from content/summary
        content_text = ""
        if hasattr(entry, 'content'):
            for content in entry.content:
                content_text += content.value + " "
        elif hasattr(entry, 'summary'):
            content_text = entry.summary
        
        # Simple regex to find image URLs in content
        image_urls = re.findall(r'<img[^>]+src="([^">]+)"', content_text)
        if image_urls:
            return image_urls[0]
                    
        return None
    except Exception as e:
        print(f"⚠️ Error extracting image: {e}")
        return None

def get_security_hashtags(topic):
    """Get relevant security hashtags based on topic"""
    # Extract key terms from topic
    topic_lower = topic.lower()
    
    # Select hashtag categories based on topic
    selected_hashtags = []
    
    # Always include general security hashtags
    selected_hashtags.extend(WEB3_SECURITY_HASHTAGS["general"])
    
    # Add specific hashtags based on topic content
    if any(term in topic_lower for term in ['smart contract', 'solidity', 'audit']):
        selected_hashtags.extend(WEB3_SECURITY_HASHTAGS["smart_contract"])
    
    if any(term in topic_lower for term in ['exploit', 'hack', 'breach', 'incident']):
        selected_hashtags.extend(WEB3_SECURITY_HASHTAGS["incident"])
    
    if any(term in topic_lower for term in ['zero knowledge', 'zk', 'privacy', 'cryptography']):
        selected_hashtags.extend(WEB3_SECURITY_HASHTAGS["privacy"])
    
    if any(term in topic_lower for term in ['defi', 'decentralized', 'finance']):
        selected_hashtags.extend(WEB3_SECURITY_HASHTAGS["general"][3:4])  # DeFiSecurity
    
    # Add trending blockchain hashtags
    selected_hashtags.extend(WEB3_SECURITY_HASHTAGS["trending"][:2])
    
    # Remove duplicates and limit to 4-5 hashtags
    unique_hashtags = []
    for tag in selected_hashtags:
        if tag not in unique_hashtags and len(unique_hashtags) < 5:
            unique_hashtags.append(tag)
    
    return " ".join(unique_hashtags)

def get_post_style_prompt(style, topic):
    """Get writing prompts for security content"""
    prompts = {
        "security_analyst": f"""
        Provide a concise security analysis of this Web3 security topic: {topic}
        
        Focus on:
        1. Key security implications
        2. Technical details (without being too complex)
        3. Real-world impact
        4. Best practices to mitigate
        
        Tone: Professional, analytical, valuable
        Length: 200-250 characters
        Include relevant security hashtags
        """,
        
        "technical_researcher": f"""
        Share technical research insights about: {topic}
        
        Include:
        - Specific vulnerability details
        - Attack vectors
        - Security patterns
        - Research findings
        
        Tone: Technical but accessible, research-focused
        Length: 200-250 characters
        Include relevant security hashtags
        """,
        
        "incident_responder": f"""
        Analyze this security incident/topic: {topic}
        
        Cover:
        - What happened
        - Root cause analysis
        - Lessons learned
        - Prevention strategies
        
        Tone: Practical, experienced, actionable
        Length: 200-250 characters
        Include relevant security hashtags
        """,
        
        "auditor_perspective": f"""
        Provide an auditor's perspective on: {topic}
        
        Discuss:
        - Common vulnerabilities
        - Audit findings
        - Security best practices
        - Risk assessment
        
        Tone: Expert, thorough, educational
        Length: 200-250 characters
        Include relevant security hashtags
        """,
        
        "cryptography_expert": f"""
        Explain cryptographic aspects of: {topic}
        
        Focus on:
        - Cryptographic principles
        - Security guarantees
        - Implementation concerns
        - Latest advances
        
        Tone: Knowledgeable, precise, forward-looking
        Length: 200-250 characters
        Include relevant security hashtags
        """,
        
        "defi_security": f"""
        Discuss DeFi security considerations for: {topic}
        
        Address:
        - DeFi-specific risks
        - Smart contract security
        - Economic security
        - Protocol safety
        
        Tone: Specialized, financial security focus
        Length: 200-250 characters
        Include relevant security hashtags
        """
    }
    
    return prompts.get(style, prompts["security_analyst"])

def generate_security_insight(articles):
    """Generate valuable security insights"""
    if not articles:
        return create_security_fallback(), None
    
    # Select random article
    article = random.choice(articles)
    topic = article['title']
    
    # Get image if available
    image_url = article.get('image_url')
    
    # Choose random style
    style = random.choice(POST_STYLES)
    print(f"🎨 Using post style: {style}")
    
    prompt = get_post_style_prompt(style, topic)
    
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
                
                # Ensure hashtags are included
                if not any('#' in post_text for tag in post_text.split()):
                    hashtags = get_security_hashtags(topic)
                    post_text += f" {hashtags}"
                
                # Clean up
                post_text = remove_ai_indicators(post_text)
                
                # Final length check
                if len(post_text) > 280:
                    post_text = post_text[:277] + "..."
                
                print(f"✅ Security insight created ({len(post_text)} chars)")
                return post_text, image_url
    
    except Exception as e:
        print(f"❌ Security insight generation error: {e}")
    
    # Fallback
    return create_security_fallback(), image_url

def generate_vulnerability_analysis(articles):
    """Generate analysis of specific vulnerabilities"""
    if not articles:
        return create_security_fallback(), None
    
    # Find articles with vulnerability mentions
    vuln_articles = [a for a in articles if any(term in a['title'].lower() for term in 
                    ['vulnerability', 'exploit', 'bug', 'flaw', 'reentrancy', 'flash loan'])]
    
    if not vuln_articles:
        vuln_articles = articles
    
    article = random.choice(vuln_articles)
    topic = article['title']
    image_url = article.get('image_url')
    
    prompt = f"""
    Analyze this Web3 security vulnerability: {topic}
    
    Provide:
    1. Brief technical explanation
    2. Potential impact severity
    3. Mitigation strategies
    4. Similar vulnerabilities to watch for
    
    Format: Concise, technical but readable
    Length: 220-260 characters
    Include 3-4 relevant security hashtags
    
    Example format:
    "Reentrancy vulnerability in XYZ protocol allowed attackers to drain funds. Root cause: unsafe external calls before state updates. Mitigation: use checks-effects-interactions pattern. #SmartContracts #Audit #Web3Security"
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
                
                # Ensure hashtags
                if not any('#' in post_text for tag in post_text.split()):
                    hashtags = get_security_hashtags(topic)
                    post_text += f" {hashtags}"
                
                post_text = remove_ai_indicators(post_text)
                
                if len(post_text) > 280:
                    post_text = post_text[:277] + "..."
                
                print(f"✅ Vulnerability analysis created ({len(post_text)} chars)")
                return post_text, image_url
    
    except Exception as e:
        print(f"❌ Vulnerability analysis error: {e}")
    
    return create_security_fallback(), image_url

def generate_security_tips():
    """Generate practical security tips"""
    security_tips = [
        "Smart contract security tip: Always use the latest compiler version with security patches enabled. Old compilers may have known vulnerabilities that attackers can exploit. #SmartContracts #Security #Web3",
        "DeFi security: Implement time locks for critical governance changes. This gives users time to react to potentially malicious proposals. #DeFiSecurity #Governance #Blockchain",
        "Wallet security: Use hardware wallets for significant funds. Never share seed phrases & consider multi-sig for team wallets. #WalletSecurity #Crypto #Web3Security",
        "Audit importance: Multiple audit rounds with different firms catch different issues. Don't rely on a single audit before mainnet launch. #Audit #SmartContracts #Security",
        "Incident response: Have a pre-planned response strategy for security incidents. This includes communication plans, mitigation steps, and post-mortem processes. #IncidentResponse #Web3Security",
        "Access control: Implement proper role-based access control in smart contracts. Use modifiers to restrict critical functions to authorized addresses only. #SmartContracts #AccessControl #Security",
        "Oracle security: Use multiple oracle sources with price aggregation. Single oracle failures can lead to significant protocol losses. #Oracle #DeFiSecurity #Web3",
        "Code review: Peer review is essential. Four eyes see more than two - especially for security-critical code. #CodeReview #Security #Development",
        "Upgrade patterns: Use proxy patterns for upgradeable contracts but ensure proper access controls on upgrade functions. #Upgradeability #SmartContracts #Security",
        "Testing: Comprehensive test coverage including edge cases and fuzz testing. 95%+ test coverage should be standard for DeFi protocols. #Testing #Fuzzing #Security"
    ]
    
    post_text = random.choice(security_tips)
    
    # Ensure proper length
    if len(post_text) > 280:
        post_text = post_text[:277] + "..."
    
    return post_text, None

def generate_audit_findings_analysis(articles):
    """Generate analysis of audit findings"""
    if not articles:
        return create_security_fallback(), None
    
    # Find audit-related articles
    audit_articles = [a for a in articles if any(term in a['title'].lower() for term in 
                     ['audit', 'finding', 'report', 'review'])]
    
    if not audit_articles:
        audit_articles = articles
    
    article = random.choice(audit_articles)
    topic = article['title']
    image_url = article.get('image_url')
    
    prompt = f"""
    Summarize key security audit findings from: {topic}
    
    Include:
    1. Type of vulnerabilities found
    2. Severity levels
    3. Common patterns observed
    4. Recommendations for developers
    
    Format: Bullet-point style in a single paragraph
    Length: 230-270 characters
    Include relevant audit and security hashtags
    
    Example:
    "Recent audit revealed critical reentrancy issues & medium-severity access control flaws. Common patterns: unsafe external calls, missing modifiers. Recommendation: implement checks-effects-interactions & proper RBAC. #Audit #SmartContracts #Security"
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
                
                # Add hashtags if missing
                if not any('#' in post_text for tag in post_text.split()):
                    hashtags = get_security_hashtags(topic)
                    post_text += f" {hashtags}"
                
                post_text = remove_ai_indicators(post_text)
                
                if len(post_text) > 280:
                    post_text = post_text[:277] + "..."
                
                print(f"✅ Audit findings analysis created ({len(post_text)} chars)")
                return post_text, image_url
    
    except Exception as e:
        print(f"❌ Audit analysis error: {e}")
    
    return create_security_fallback(), image_url

def remove_ai_indicators(text):
    """Remove any phrases that sound AI-generated"""
    ai_phrases = [
        "as an AI", "according to AI", "AI-generated", "language model",
        "based on the provided", "in this content", "the writer",
        "this analysis", "the author", "in this piece", "according to the",
        "as a large language model", "I am designed to", "my purpose is to"
    ]
    
    for phrase in ai_phrases:
        text = text.replace(phrase, "")
        text = text.replace(phrase.title(), "")
    
    return ' '.join(text.split())

def create_security_fallback():
    """Create fallback security posts"""
    fallbacks = [
        "Smart contract security is evolving rapidly. Recent trends show increasing focus on formal verification and automated vulnerability detection tools. #Web3Security #SmartContracts #Blockchain",
        "DeFi security requires multiple layers: smart contract audits, economic security analysis, and incident response planning. No single solution provides complete protection. #DeFiSecurity #Audit #RiskManagement",
        "Wallet security fundamentals: hardware wallets for storage, multi-sig for teams, and never interacting with suspicious dApps. Basic hygiene prevents most attacks. #WalletSecurity #Crypto #Web3",
        "Zero-knowledge proofs are revolutionizing privacy and scaling. Understanding zk-SNARKs vs zk-STARKs is crucial for next-gen blockchain security. #ZeroKnowledge #ZKP #Cryptography",
        "Cross-chain security remains challenging. Bridge vulnerabilities have caused billions in losses. Always verify bridge security audits before large transfers. #CrossChain #BridgeSecurity #Web3",
        "Governance security: Time-locked proposals, multi-sig execution, and gradual decentralization prevent governance attacks in DeFi protocols. #Governance #DeFi #Security",
        "Oracle manipulation attacks continue to plague DeFi. Using multiple data sources with aggregation mechanisms reduces single-point failure risks. #Oracle #DeFiSecurity #Web3",
        "Formal verification mathematically proves smart contract correctness. While resource-intensive, it's becoming essential for high-value protocols. #FormalVerification #SmartContracts #Security",
        "Incident response planning is often overlooked. Having a playbook for security breaches can mean the difference between recovery and collapse. #IncidentResponse #Security #Web3",
        "Upgradeable contracts introduce new risks. Proper proxy patterns with transparent upgrade processes are essential for maintaining security during updates. #Upgradeability #SmartContracts #Security"
    ]
    
    post_text = random.choice(fallbacks)
    
    # Ensure proper length
    if len(post_text) > 280:
        post_text = post_text[:277] + "..."
    
    return post_text

# ================================
# POST TYPE SELECTOR
# ================================

def select_post_type():
    """Randomly select post type with weighted probability"""
    post_types = [
        ('security_insight', 0.35),      # 35% security insights
        ('vulnerability_analysis', 0.25), # 25% vulnerability analysis
        ('security_tips', 0.20),          # 20% security tips
        ('audit_findings', 0.20)          # 20% audit findings
    ]
    
    choices, weights = zip(*post_types)
    return random.choices(choices, weights=weights)[0]

# ================================
# MAIN EXECUTION
# ================================

def main():
    print("🔐 Web3 Security Content Creator")
    print("=" * 50)
    print("💎 VALUABLE SECURITY INSIGHTS • NO PROMOTIONAL CONTENT")
    print("🔗 RELEVANT HASHTAGS • TECHNICAL DEPTH")
    print("🤖 USING GEMINI 2.0 FLASH")
    print("=" * 50)
    
    # Validate configuration
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API secrets")
        return
        
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY secret")
        return
    
    print(f"✅ Twitter API configured")
    print(f"✅ Gemini 2.0 Flash configured")
    print("")
    
    # Fetch security articles
    articles = fetch_web3_security_news()
    
    if not articles:
        print("⚠️ No quality security articles found, using fallback content")
    
    # Select post type
    post_type = select_post_type()
    print(f"🎯 Selected post type: {post_type.replace('_', ' ').title()}")
    
    # Generate content based on post type
    image_url = None
    if post_type == 'security_insight':
        post_text, image_url = generate_security_insight(articles)
    elif post_type == 'vulnerability_analysis':
        post_text, image_url = generate_vulnerability_analysis(articles)
    elif post_type == 'security_tips':
        post_text, image_url = generate_security_tips()
    else:  # audit_findings
        post_text, image_url = generate_audit_findings_analysis(articles)
    
    print(f"📝 Final Post: {post_text}")
    print(f"📏 Character count: {len(post_text)}")
    print(f"🖼️ Image available: {'Yes' if image_url else 'No'}")
    
    # Post to Twitter
    print("\n🚀 Posting security insights...")
    success = post_to_twitter(
        post_text, 
        TWITTER_API_KEY, 
        TWITTER_API_SECRET, 
        TWITTER_ACCESS_TOKEN, 
        TWITTER_ACCESS_TOKEN_SECRET,
        image_url
    )
    
    if success:
        print("\n✅ Successfully posted security content!")
        print(f"🎯 Post type: {post_type.replace('_', ' ').title()}")
        print(f"🖼️ Image included: {'Yes' if image_url else 'No'}")
        print(f"🔗 Hashtags: {len([t for t in post_text.split() if t.startswith('#')])}")
    else:
        print("\n❌ Failed to post.")

if __name__ == "__main__":
    main()