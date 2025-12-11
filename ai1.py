import os
import requests
import random
import time
import json
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

# AI & ML RSS Feeds - Quality technical sources
AI_RSS_FEEDS = [
    'https://ai.googleblog.com/feeds/posts/default',
    'https://openai.com/blog/rss/',
    'https://deepmind.google/blog/feed.xml',
    'https://research.facebook.com/blog/rss/',
    'https://aws.amazon.com/blogs/machine-learning/feed/',
    'https://cloud.google.com/blog/topics/developers-practitioners/feeds/gcp-blogs-atom-ai-machine-learning.xml',
    'https://www.microsoft.com/en-us/research/feed/tag/artificial-intelligence/',
    'https://ai.meta.com/blog/rss/',
    'https://huggingface.co/blog/feed.xml',
    'https://blog.tensorflow.org/feeds/posts/default',
    'https://pytorch.org/blog/feed/',
    'https://distill.pub/rss.xml',
    'https://www.fast.ai/rss.xml'
]

# AI categories for targeted content
AI_CATEGORIES = [
    'machine-learning',
    'deep-learning',
    'nlp',
    'computer-vision',
    'reinforcement-learning',
    'generative-ai',
    'llms',
    'multimodal',
    'ethics-ai',
    'research',
    'applications',
    'tools-frameworks'
]

# Promotional keywords to filter out
PROMOTIONAL_KEYWORDS = [
    'discount', 'sale', 'coupon', 'promo', 'deal', 'offer', 'limited time',
    'buy now', 'shop', 'store', 'price drop', 'save', 'percent off',
    'exclusive offer', 'special offer', 'flash sale', 'sponsored',
    'advertisement', 'affiliate', 'partner', 'promotion', 'bundle',
    'free trial', 'subscribe', 'sign up', 'get started', 'enterprise',
    'contact sales', 'request demo', 'pricing', 'upgrade', 'premium'
]

# Post styles for variety - focused on AI expertise
POST_STYLES = [
    "research_analyst",
    "technical_explainer", 
    "practitioner_perspective",
    "ethics_discussion",
    "future_trends",
    "educational_content"
]

# ================================
# AI & ML HASHTAGS DATABASE
# ================================

AI_HASHTAGS = {
    "general": ["#AI", "#MachineLearning", "#ArtificialIntelligence", "#DataScience"],
    "deep_learning": ["#DeepLearning", "#NeuralNetworks", "#TensorFlow", "#PyTorch"],
    "nlp": ["#NLP", "#LLM", "#GenerativeAI", "#ChatGPT"],
    "computer_vision": ["#ComputerVision", "#CV", "#ImageRecognition", "#OpenCV"],
    "research": ["#AIResearch", "#MLResearch", "#arXiv", "#Innovation"],
    "ethics": ["#AIEthics", "#ResponsibleAI", "#FairAI", "#Privacy"],
    "tools": ["#MLOps", "#DataEngineering", "#BigData", "#CloudAI"],
    "applications": ["#AIAutomation", "#SmartTech", "#FutureOfWork", "#DigitalTransformation"],
    "trending": ["#Tech", "#Innovation", "#Technology", "#Science"]
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

def is_quality_ai_content(article):
    """Check if article is genuine AI content with technical depth"""
    title = article.get('title', '').lower()
    summary = article.get('summary', '').lower()
    
    # Positive indicators of quality AI content
    quality_indicators = [
        'ai', 'machine learning', 'deep learning', 'neural network',
        'algorithm', 'model', 'training', 'inference', 'dataset',
        'nlp', 'natural language', 'transformer', 'llm', 'gpt',
        'computer vision', 'cv', 'image', 'recognition', 'detection',
        'reinforcement learning', 'rl', 'agent', 'policy',
        'generative', 'diffusion', 'gan', 'synthesis',
        'research', 'paper', 'arxiv', 'experiment', 'result',
        'framework', 'library', 'tool', 'implementation',
        'ethics', 'bias', 'fairness', 'explainability', 'transparency',
        'application', 'use case', 'deployment', 'production'
    ]
    
    # Check if content has technical depth
    content = title + " " + summary
    technical_score = sum(1 for indicator in quality_indicators if indicator in content)
    
    return technical_score >= 2  # Require at least 2 AI-related terms

def filter_articles(articles):
    """Filter out promotional and low-quality articles"""
    filtered_articles = []
    
    for article in articles:
        if not is_promotional_content(article) and is_quality_ai_content(article):
            filtered_articles.append(article)
        else:
            print(f"🚫 Filtered out: {article['title'][:60]}...")
    
    print(f"✅ Filtered {len(articles)} -> {len(filtered_articles)} quality AI articles")
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

def fetch_ai_news():
    """Fetch current AI news from RSS feeds"""
    try:
        print("🤖 Fetching latest AI news...")
        articles = fetch_news_from_feeds(AI_RSS_FEEDS, "ai")
        
        # Filter out promotional content
        filtered_articles = filter_articles(articles)
        
        random.shuffle(filtered_articles)
        print(f"🎲 Randomly selected from {len(filtered_articles)} quality AI articles")
        return filtered_articles
        
    except Exception as e:
        print(f"❌ AI RSS fetch error: {e}")
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
                
                # Skip if article is too old (1 week for AI news)
                if article_date and (datetime.now() - article_date).days > 14:
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

def get_ai_hashtags(topic):
    """Get relevant AI hashtags based on topic"""
    # Extract key terms from topic
    topic_lower = topic.lower()
    
    # Select hashtag categories based on topic
    selected_hashtags = []
    
    # Always include general AI hashtags
    selected_hashtags.extend(AI_HASHTAGS["general"])
    
    # Add specific hashtags based on topic content
    if any(term in topic_lower for term in ['deep learning', 'neural', 'tensorflow', 'pytorch']):
        selected_hashtags.extend(AI_HASHTAGS["deep_learning"])
    
    if any(term in topic_lower for term in ['nlp', 'language', 'llm', 'gpt', 'transformer']):
        selected_hashtags.extend(AI_HASHTAGS["nlp"])
    
    if any(term in topic_lower for term in ['computer vision', 'image', 'recognition', 'detection']):
        selected_hashtags.extend(AI_HASHTAGS["computer_vision"])
    
    if any(term in topic_lower for term in ['ethics', 'bias', 'fairness', 'responsible']):
        selected_hashtags.extend(AI_HASHTAGS["ethics"])
    
    if any(term in topic_lower for term in ['research', 'paper', 'arxiv']):
        selected_hashtags.extend(AI_HASHTAGS["research"])
    
    # Add trending tech hashtags
    selected_hashtags.extend(AI_HASHTAGS["trending"][:2])
    
    # Remove duplicates and limit to 4-5 hashtags
    unique_hashtags = []
    for tag in selected_hashtags:
        if tag not in unique_hashtags and len(unique_hashtags) < 5:
            unique_hashtags.append(tag)
    
    return " ".join(unique_hashtags)

def get_post_style_prompt(style, topic):
    """Get writing prompts for AI content"""
    prompts = {
        "research_analyst": f"""
        Provide a concise analysis of this AI research topic: {topic}
        
        Focus on:
        1. Key technical innovations
        2. Methodology overview
        3. Potential applications
        4. Impact on the field
        
        Tone: Professional, analytical, insightful
        Length: 200-250 characters
        Include relevant AI hashtags
        """,
        
        "technical_explainer": f"""
        Explain this AI concept in accessible terms: {topic}
        
        Include:
        - Simple explanation
        - How it works at high level
        - Why it's important
        - Real-world examples
        
        Tone: Educational, clear, engaging
        Length: 200-250 characters
        Include relevant AI hashtags
        """,
        
        "practitioner_perspective": f"""
        Provide practical insights about: {topic}
        
        Cover:
        - Implementation considerations
        - Best practices
        - Common challenges
        - Tips for success
        
        Tone: Practical, experienced, helpful
        Length: 200-250 characters
        Include relevant AI hashtags
        """,
        
        "ethics_discussion": f"""
        Discuss ethical considerations of: {topic}
        
        Discuss:
        - Potential risks and benefits
        - Societal impact
        - Responsible development
        - Future implications
        
        Tone: Thoughtful, balanced, forward-looking
        Length: 200-250 characters
        Include relevant AI hashtags
        """,
        
        "future_trends": f"""
        Explore future trends related to: {topic}
        
        Focus on:
        - Emerging developments
        - Where the field is heading
        - Potential breakthroughs
        - Long-term implications
        
        Tone: Visionary, informed, speculative
        Length: 200-250 characters
        Include relevant AI hashtags
        """,
        
        "educational_content": f"""
        Create educational content about: {topic}
        
        Address:
        - Key concepts to understand
        - Learning resources
        - Common misconceptions
        - Starting points for beginners
        
        Tone: Helpful, encouraging, informative
        Length: 200-250 characters
        Include relevant AI hashtags
        """
    }
    
    return prompts.get(style, prompts["research_analyst"])

def generate_ai_insight(articles):
    """Generate valuable AI insights"""
    if not articles:
        return create_ai_fallback(), None
    
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
                    hashtags = get_ai_hashtags(topic)
                    post_text += f" {hashtags}"
                
                # Clean up
                post_text = remove_ai_indicators(post_text)
                
                # Final length check
                if len(post_text) > 280:
                    post_text = post_text[:277] + "..."
                
                print(f"✅ AI insight created ({len(post_text)} chars)")
                return post_text, image_url
    
    except Exception as e:
        print(f"❌ AI insight generation error: {e}")
    
    # Fallback
    return create_ai_fallback(), image_url

def generate_technical_explanation(articles):
    """Generate technical explanations of AI concepts"""
    if not articles:
        return create_ai_fallback(), None
    
    # Find technical articles
    tech_articles = [a for a in articles if any(term in a['title'].lower() for term in 
                    ['algorithm', 'model', 'architecture', 'technique', 'method'])]
    
    if not tech_articles:
        tech_articles = articles
    
    article = random.choice(tech_articles)
    topic = article['title']
    image_url = article.get('image_url')
    
    prompt = f"""
    Explain this AI technical concept in simple terms: {topic}
    
    Provide:
    1. Simple analogy or metaphor
    2. Core idea without jargon
    3. Why it matters
    4. Example application
    
    Format: Conversational, engaging, educational
    Length: 220-260 characters
    Include 3-4 relevant AI hashtags
    
    Example format:
    "Think of attention in transformers like highlighting important words when reading. The model focuses on relevant parts of input to make better predictions. Revolutionized NLP tasks like translation. #AI #NLP #Transformers #MachineLearning"
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
                    hashtags = get_ai_hashtags(topic)
                    post_text += f" {hashtags}"
                
                post_text = remove_ai_indicators(post_text)
                
                if len(post_text) > 280:
                    post_text = post_text[:277] + "..."
                
                print(f"✅ Technical explanation created ({len(post_text)} chars)")
                return post_text, image_url
    
    except Exception as e:
        print(f"❌ Technical explanation error: {e}")
    
    return create_ai_fallback(), image_url

def generate_ai_tips():
    """Generate practical AI tips"""
    ai_tips = [
        "ML tip: Always split your data into train/validation/test sets before any analysis. This prevents data leakage and gives honest performance estimates. #MachineLearning #DataScience #Tips",
        "Debugging models: When your model isn't learning, check: 1) Learning rate 2) Data quality 3) Model capacity 4) Loss function. Small changes can have big impacts. #DeepLearning #MLOps #AI",
        "Feature engineering: Sometimes simple features work better than complex ones. Start with domain knowledge-based features before trying automated feature selection. #DataScience #MachineLearning #AI",
        "Model interpretability: Use SHAP or LIME to explain model predictions. Understanding why models make decisions builds trust and helps debugging. #ExplainableAI #ML #DataScience",
        "Data preprocessing: Spend time cleaning and understanding your data. Better data often beats fancier algorithms. Garbage in, garbage out applies to AI too. #DataEngineering #MachineLearning #AI",
        "Transfer learning: Leverage pretrained models for your tasks. Fine-tuning existing models often works better than training from scratch with limited data. #DeepLearning #TransferLearning #AI",
        "Regularization techniques: Use dropout, weight decay, and early stopping to prevent overfitting. The goal is generalization, not perfect training accuracy. #MachineLearning #DeepLearning #AI",
        "Evaluation metrics: Choose metrics aligned with business goals. Accuracy isn't everything - consider precision, recall, F1, or custom metrics for imbalanced data. #DataScience #Evaluation #ML",
        "Version control: Track code, data, and model versions. Tools like DVC or MLflow help reproduce experiments and manage the ML lifecycle. #MLOps #VersionControl #AI",
        "Ethical considerations: Regularly audit models for bias and fairness. Diverse training data and fairness metrics should be part of your development process. #AIEthics #ResponsibleAI #MachineLearning"
    ]
    
    post_text = random.choice(ai_tips)
    
    # Ensure proper length
    if len(post_text) > 280:
        post_text = post_text[:277] + "..."
    
    return post_text, None

def generate_research_highlights(articles):
    """Generate highlights of recent AI research"""
    if not articles:
        return create_ai_fallback(), None
    
    # Find research-related articles
    research_articles = [a for a in articles if any(term in a['title'].lower() for term in 
                        ['research', 'paper', 'study', 'arxiv', 'finding'])]
    
    if not research_articles:
        research_articles = articles
    
    article = random.choice(research_articles)
    topic = article['title']
    image_url = article.get('image_url')
    
    prompt = f"""
    Summarize key findings from this AI research: {topic}
    
    Include:
    1. Main contribution or discovery
    2. Methodology approach
    3. Key results
    4. Implications for the field
    
    Format: Concise, highlight-focused
    Length: 230-270 characters
    Include relevant research and AI hashtags
    
    Example:
    "New research introduces efficient transformer architecture reducing computation by 40% while maintaining accuracy. Uses novel attention mechanism and optimized layers. Could enable larger models on limited hardware. #AIResearch #Transformers #DeepLearning"
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
                    hashtags = get_ai_hashtags(topic)
                    post_text += f" {hashtags}"
                
                post_text = remove_ai_indicators(post_text)
                
                if len(post_text) > 280:
                    post_text = post_text[:277] + "..."
                
                print(f"✅ Research highlights created ({len(post_text)} chars)")
                return post_text, image_url
    
    except Exception as e:
        print(f"❌ Research highlights error: {e}")
    
    return create_ai_fallback(), image_url

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

def create_ai_fallback():
    """Create fallback AI posts"""
    fallbacks = [
        "Transformers have revolutionized NLP, but new architectures like Mamba show promising alternatives for efficient sequence modeling. #AI #NLP #MachineLearning #Research",
        "Multimodal AI combining vision, language, and audio is creating more versatile systems. Next-gen models understand and generate across multiple modalities. #MultimodalAI #DeepLearning #Innovation",
        "Explainable AI (XAI) is crucial for trust and adoption. Techniques like SHAP and LIME help understand model decisions in critical applications. #ExplainableAI #ResponsibleAI #MachineLearning",
        "Few-shot learning enables models to learn from minimal examples. This moves us closer to human-like learning efficiency in AI systems. #FewShotLearning #AI #DeepLearning",
        "Reinforcement learning from human feedback (RLHF) is key for aligning LLMs with human values. It's how models like ChatGPT became so helpful. #RLHF #LLM #AIAlignment",
        "Federated learning enables model training without centralizing sensitive data. Privacy-preserving AI is essential for healthcare and finance applications. #FederatedLearning #Privacy #AI",
        "Diffusion models have transformed image generation. The gradual denoising process creates high-quality, diverse outputs from random noise. #DiffusionModels #GenerativeAI #ComputerVision",
        "Self-supervised learning uses unlabeled data for pretraining, reducing dependency on expensive annotations. A key trend in modern ML. #SelfSupervisedLearning #MachineLearning #AI",
        "Model compression techniques like pruning, quantization, and distillation make AI efficient for edge devices. Democratizing AI access. #ModelCompression #EdgeAI #Efficiency",
        "AI for science accelerates discovery in fields from biology to materials science. Models predict protein structures, discover new materials, and more. #AIScience #Research #Innovation"
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
        ('ai_insight', 0.35),          # 35% AI insights
        ('technical_explanation', 0.25), # 25% technical explanations
        ('ai_tips', 0.20),              # 20% AI tips
        ('research_highlights', 0.20)   # 20% research highlights
    ]
    
    choices, weights = zip(*post_types)
    return random.choices(choices, weights=weights)[0]

# ================================
# MAIN EXECUTION
# ================================

def main():
    print("🤖 AI & ML Content Creator")
    print("=" * 50)
    print("💎 VALUABLE AI INSIGHTS • NO PROMOTIONAL CONTENT")
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
    
    # Fetch AI articles
    articles = fetch_ai_news()
    
    if not articles:
        print("⚠️ No quality AI articles found, using fallback content")
    
    # Select post type
    post_type = select_post_type()
    print(f"🎯 Selected post type: {post_type.replace('_', ' ').title()}")
    
    # Generate content based on post type
    image_url = None
    if post_type == 'ai_insight':
        post_text, image_url = generate_ai_insight(articles)
    elif post_type == 'technical_explanation':
        post_text, image_url = generate_technical_explanation(articles)
    elif post_type == 'ai_tips':
        post_text, image_url = generate_ai_tips()
    else:  # research_highlights
        post_text, image_url = generate_research_highlights(articles)
    
    print(f"📝 Final Post: {post_text}")
    print(f"📏 Character count: {len(post_text)}")
    print(f"🖼️ Image available: {'Yes' if image_url else 'No'}")
    
    # Post to Twitter
    print("\n🚀 Posting AI insights...")
    success = post_to_twitter(
        post_text, 
        TWITTER_API_KEY, 
        TWITTER_API_SECRET, 
        TWITTER_ACCESS_TOKEN, 
        TWITTER_ACCESS_TOKEN_SECRET,
        image_url
    )
    
    if success:
        print("\n✅ Successfully posted AI content!")
        print(f"🎯 Post type: {post_type.replace('_', ' ').title()}")
        print(f"🖼️ Image included: {'Yes' if image_url else 'No'}")
        print(f"🔗 Hashtags: {len([t for t in post_text.split() if t.startswith('#')])}")
    else:
        print("\n❌ Failed to post.")

if __name__ == "__main__":
    main()