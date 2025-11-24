import os
import google.generativeai as genai
import requests
import random
import feedparser
from datetime import datetime
import re
import time
import tweepy

# Configuration
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Clean RSS feeds - only science/nature/technology (NO POLITICAL CONTENT)
RSS_FEEDS = [
    "https://www.nationalgeographic.com/index.rss",
    "https://feeds.sciencedaily.com/sciencedaily",
    "https://www.sciencedaily.com/rss/all.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
    "https://feeds.arstechnica.com/arstechnica/science/",
]

# Political content filter - expanded list
POLITICAL_KEYWORDS = [
    'trump', 'biden', 'president', 'election', 'government', 'policy', 
    'tariff', 'tax', 'war', 'conflict', 'political', 'democrat', 'republican',
    'congress', 'senate', 'white house', 'administration', 'vote', 'campaign'
]

# Topic-specific hashtag mapping
TOPIC_HASHTAGS = {
    'space': ['#Space', '#NASA', '#SpaceX', '#Astronomy', '#Cosmos', '#Universe', '#Galaxy', '#SpaceExploration'],
    'climate': ['#Climate', '#ClimateChange', '#Sustainability', '#EcoFriendly', '#GreenTech', '#RenewableEnergy', '#SaveThePlanet'],
    'tech': ['#Tech', '#Innovation', '#AI', '#Technology', '#FutureTech', '#DigitalTransformation', '#TechNews'],
    'health': ['#Health', '#Medicine', '#Wellness', '#Healthcare', '#MedicalResearch', '#PublicHealth', '#HealthyLiving'],
    'nature': ['#Nature', '#Wildlife', '#Biodiversity', '#Conservation', '#Ecology', '#PlanetEarth', '#NatureLovers'],
    'science': ['#Science', '#Research', '#Discovery', '#STEM', '#ScientificDiscovery', '#ScienceNews', '#LabLife'],
    'biology': ['#Biology', '#Genetics', '#Microbiology', '#LifeSciences', '#Biotech', '#CellBiology'],
    'physics': ['#Physics', '#Quantum', '#Astrophysics', '#ParticlePhysics', '#TheoreticalPhysics'],
    'environment': ['#Environment', '#Eco', '#Green', '#Sustainability', '#ClimateAction', '#Earth'],
    'innovation': ['#Innovation', '#Future', '#Breakthrough', '#NextGen', '#CuttingEdge'],
    'ocean': ['#Ocean', '#MarineBiology', '#OceanConservation', '#SeaLife', '#BluePlanet'],
    'energy': ['#Energy', '#CleanEnergy', '#Solar', '#WindPower', '#EnergyTransition'],
    'neuroscience': ['#Neuroscience', '#Brain', '#Psychology', '#Mind', '#CognitiveScience'],
    'robotics': ['#Robotics', '#AI', '#Automation', '#FutureOfWork', '#TechInnovation']
}

# Cache to avoid duplicate posts
posted_links = set()

# ================================
# TWITTER/X API FUNCTIONS
# ================================

def post_to_twitter(content, api_key, api_secret, access_token, access_token_secret, image_url=None):
    """Post content to Twitter/X with optional image using the correct API versions"""
    try:
        print("🐦 Posting to Twitter/X...")
        
        # Ensure content is within Twitter limits
        if len(content) > 280:
            print(f"📏 Content too long ({len(content)} chars), truncating...")
            content = content[:277] + "..."
        
        # --- UPLOAD MEDIA (using v1.1) ---
        media_ids = []
        if image_url:
            print(f"📤 Uploading media from {image_url}...")
            
            # Clean up image URL
            clean_image_url = image_url.split('?')[0].split('&#')[0]
            
            # Use v1.1 API for media upload (this is allowed on Free tier)
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
        
        # --- CREATE TWEET (using v2) ---
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Post the tweet using v2 endpoint
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
# CONTENT FUNCTIONS (SAME AS THREADS)
# ================================

def contains_political_content(text):
    """Check if text contains political keywords"""
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in POLITICAL_KEYWORDS)

def extract_images_from_rss(entry):
    """Extract all images from RSS entry"""
    images = []
    
    # Check multiple possible image sources in RSS
    if hasattr(entry, 'links'):
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                images.append(link.href)
    
    # Check media content
    if hasattr(entry, 'media_content'):
        for media in entry.media_content:
            if media.get('type', '').startswith('image/'):
                images.append(media['url'])
    
    # Check for enclosures
    if hasattr(entry, 'enclosures'):
        for enclosure in entry.enclosures:
            if enclosure.get('type', '').startswith('image/'):
                images.append(enclosure.href)
    
    # Parse HTML content for images
    if hasattr(entry, 'content'):
        for content in entry.content:
            images.extend(re.findall(r'<img[^>]+src="([^">]+)"', content.value))
    
    if hasattr(entry, 'summary'):
        images.extend(re.findall(r'<img[^>]+src="([^">]+)"', entry.summary))
    
    # Remove duplicates and invalid URLs
    unique_images = []
    for img in images:
        if img and img.startswith(('http://', 'https://')) and img not in unique_images:
            unique_images.append(img)
    
    return unique_images

def parse_rss_feeds():
    """Parse all RSS feeds and return non-political entries with images"""
    all_entries = []
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                # Skip if recently posted
                if entry.link in posted_links:
                    continue
                
                # Skip political content
                if contains_political_content(entry.title) or contains_political_content(entry.get('summary', '')):
                    continue
                
                # Skip old articles (older than 3 days)
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_date = datetime(*entry.published_parsed[:6])
                    if article_date and (datetime.now() - article_date).days > 3:
                        continue
                
                # Get images from RSS
                images = extract_images_from_rss(entry)
                
                all_entries.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary', ''),
                    'published': article_date,
                    'source': feed.feed.title if hasattr(feed.feed, 'title') else feed_url.split('//')[-1].split('/')[0],
                    'images': images
                })
                
        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")
    
    return all_entries

def verify_image_url(image_url):
    """Verify that an image URL is accessible"""
    try:
        response = requests.head(image_url, timeout=10)
        return response.status_code == 200
    except:
        return False

def detect_topic(title, summary):
    """Detect the main topic of the content for relevant hashtags"""
    text = (title + ' ' + summary).lower()
    
    topic_weights = {}
    
    if any(word in text for word in ['space', 'nasa', 'astronomy', 'planet', 'galaxy', 'universe']):
        topic_weights['space'] = 3
    if any(word in text for word in ['climate', 'warming', 'carbon', 'emission', 'sustainable']):
        topic_weights['climate'] = 3
    if any(word in text for word in ['tech', 'ai', 'robot', 'digital', 'software', 'algorithm']):
        topic_weights['tech'] = 3
    if any(word in text for word in ['health', 'medical', 'disease', 'treatment', 'medicine']):
        topic_weights['health'] = 3
    if any(word in text for word in ['nature', 'wildlife', 'animal', 'plant', 'ecosystem']):
        topic_weights['nature'] = 2
    if any(word in text for word in ['biology', 'genetic', 'cell', 'dna', 'evolution']):
        topic_weights['biology'] = 2
    if any(word in text for word in ['physics', 'quantum', 'particle', 'energy', 'theory']):
        topic_weights['physics'] = 2
    if any(word in text for word in ['environment', 'eco', 'green', 'sustainable']):
        topic_weights['environment'] = 2
    if any(word in text for word in ['innovation', 'breakthrough', 'discovery', 'new']):
        topic_weights['innovation'] = 1
    if any(word in text for word in ['ocean', 'marine', 'sea', 'coral']):
        topic_weights['ocean'] = 2
    if any(word in text for word in ['energy', 'solar', 'wind', 'renewable']):
        topic_weights['energy'] = 2
    if any(word in text for word in ['brain', 'neuroscience', 'psychology', 'cognitive']):
        topic_weights['neuroscience'] = 2
    if any(word in text for word in ['robot', 'automation', 'ai', 'machine learning']):
        topic_weights['robotics'] = 2
    
    # Always include science
    topic_weights['science'] = 1
    
    # Get top 3 topics by weight
    sorted_topics = sorted(topic_weights.items(), key=lambda x: x[1], reverse=True)[:3]
    return [topic for topic, weight in sorted_topics]

def get_topic_hashtags(topics):
    """Get relevant hashtags for detected topics"""
    hashtags = []
    for topic in topics:
        if topic in TOPIC_HASHTAGS:
            hashtags.extend(TOPIC_HASHTAGS[topic][:2])  # Take top 2 from each topic
    
    # Ensure we have a good mix without duplicates
    unique_hashtags = list(set(hashtags))
    
    # Add some general science hashtags if we have space
    general_hashtags = ['#Science', '#Discovery', '#STEM']
    for hashtag in general_hashtags:
        if hashtag not in unique_hashtags and len(unique_hashtags) < 6:  # Reduced for Twitter
            unique_hashtags.append(hashtag)
    
    return ' '.join(unique_hashtags[:6])  # Max 6 hashtags for Twitter

def generate_topic_specific_cta(topic, content):
    """Generate a topic-specific call to action"""
    cta_templates = {
        'space': [
            "What space discovery amazes you most? 🌌",
            "Which planet would you visit if you could? 🚀",
            "What's your favorite space fact? 👇",
            "If you could ask an astronaut one question, what would it be? 🛰️"
        ],
        'climate': [
            "What's one eco-friendly change you've made? 🌱",
            "Which climate solution excites you most? 💚",
            "Share your favorite sustainability tip! 👇",
            "What gives you hope for our planet? ✨"
        ],
        'tech': [
            "What tech innovation are you most excited about? 🤖",
            "Which emerging technology will change everything? 💡",
            "Share the coolest tech you've seen! 👇",
            "What future technology can't you wait for? 🚀"
        ],
        'health': [
            "What health fact surprised you recently? 🧠",
            "What wellness tip has made a difference? 💪",
            "Which medical breakthrough gives you hope? ❤️",
            "Share your favorite health hack! 👇"
        ],
        'nature': [
            "What's the most incredible nature fact you know? 🌿",
            "Which animal behavior blows your mind? 🐾",
            "What natural wonder do you want to see? 🌄",
            "Share your favorite nature spot! 👇"
        ]
    }
    
    # Find the best matching topic
    for main_topic, templates in cta_templates.items():
        if main_topic in topic:
            return random.choice(templates)
    
    # Fallback CTAs (shorter for Twitter)
    fallback_ctas = [
        "What scientific discovery amazes you? 👇",
        "What topic should we explore next? 💫",
        "Share your thoughts! 👇",
        "What's your take? 💭"
    ]
    return random.choice(fallback_ctas)

def generate_engaging_post():
    """Generate an engaging English post with conversational tone - optimized for Twitter"""
    entries = parse_rss_feeds()
    
    if not entries:
        return generate_fallback_post()
    
    # Prioritize entries with images
    entries_with_images = [e for e in entries if e.get('images')]
    if entries_with_images:
        entry = random.choice(entries_with_images)
    else:
        entry = random.choice(entries)
    
    posted_links.add(entry['link'])
    
    try:
        # Get a valid image from RSS
        image_url = None
        if entry.get('images'):
            for img in entry['images'][:3]:  # Check up to 3 images
                if verify_image_url(img):
                    image_url = img
                    print(f"✅ Using RSS image: {image_url}")
                    break
        
        # Detect topics for relevant hashtags and CTAs
        detected_topics = detect_topic(entry['title'], entry.get('summary', ''))
        topic_hashtags = get_topic_hashtags(detected_topics)
        topic_cta = generate_topic_specific_cta(detected_topics, entry)
        
        print(f"🎯 Detected topics: {detected_topics}")
        print(f"🏷️ Selected hashtags: {topic_hashtags}")
        print(f"📢 Topic CTA: {topic_cta}")
        
        # Engaging prompt for Twitter with topic-specific CTA (shorter for Twitter)
        prompt = (
            f"Create an engaging, conversational Twitter post about this science topic:\n\n"
            f"1. Start with an exciting discovery/fact\n"
            f"2. Keep it brief and conversational\n"
            f"3. End with this CTA: '{topic_cta}'\n\n"
            f"Topic: {entry['title']}\n"
            f"Details: {entry.get('summary', '')}\n\n"
            f"CRITICAL REQUIREMENTS:\n"
            f"- Use a bright, friendly personality 🌟\n"
            f"- Sound like you're talking to friends\n"
            f"- Use natural conversational English ONLY\n"
            f"- Include 1-2 relevant emojis\n"
            f"- Keep it under 200 characters (before hashtags)\n"
            f"- Make it welcoming and inclusive\n"
            f"- No markdown formatting\n"
            f"- MUST end with the provided CTA\n\n"
            f"Example tone:\n"
            f"'Plants can communicate through fungal networks! 🌱 How cool is that? 🤯 What's the most surprising nature fact you've learned? 👇'\n"
        )
        
        response = model.generate_content(prompt)
        text_content = response.text.strip()
        
        # Clean any remaining formatting
        text_content = re.sub(r'\*\*|\*|__|_|#', '', text_content)
        
        # Combine with topic-specific hashtags
        final_text = f"{text_content} {topic_hashtags}"
        
        return final_text, image_url
        
    except Exception as e:
        print(f"Content generation error: {e}")
        return generate_fallback_post()

def generate_fallback_post():
    """Fallback content with engaging tone and topic-specific elements - optimized for Twitter"""
    fallbacks = [
        {
            'text': "Trees communicate through underground fungal networks! 🌱✨ Nature is incredible! 🤯 What's the most amazing natural phenomenon you know? 👇 #Nature #Biology #Science #Discovery",
            'image': None
        },
        {
            'text': "New biodegradable plastics from algae could save our oceans! 🌊♻️ What eco-innovation excites you most? 👇 #Climate #Sustainability #EcoFriendly #Innovation",
            'image': None
        },
        {
            'text': "Your gut bacteria can influence your mood! 🧠💫 Mind-gut connection is wild! What recent discovery made you say 'wow'? 👇 #Health #Science #Neuroscience #Wellness",
            'image': None
        }
    ]
    fallback = random.choice(fallbacks)
    return fallback['text'], fallback['image']

# ================================
# MAIN EXECUTION
# ================================

def main():
    print("🐦 Science Content - Twitter Edition")
    print("=" * 50)
    print("🔬 SCIENCE & DISCOVERY CONTENT")
    print("💬 CONVERSATIONAL ENGLISH POSTS")
    print("🌟 FRIENDLY & ENGAGING TONE")
    print("🏷️ TOPIC-SPECIFIC HASHTAGS & CTAs")
    print("🤖 USING GEMINI 2.5 FLASH")
    print("=" * 50)
    
    # Validate configuration
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        return
        
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return
    
    print(f"✅ Twitter API configured")
    print(f"✅ Gemini 2.5 Flash configured")
    print("")
    
    # Generate content
    post_text, image_url = generate_engaging_post()
    
    print(f"📝 Post: {post_text}")
    print(f"📏 Character count: {len(post_text)}")
    print(f"🖼️ RSS Image: {'Yes' if image_url else 'No'}")
    
    # Post to Twitter
    print("\n🚀 Posting to Twitter...")
    success = post_to_twitter(
        post_text, 
        TWITTER_API_KEY, 
        TWITTER_API_SECRET, 
        TWITTER_ACCESS_TOKEN, 
        TWITTER_ACCESS_TOKEN_SECRET,
        image_url
    )
    
    if success:
        print("\n✅ Successfully posted to Twitter!")
        print(f"🎯 Content type: Science & Discovery")
        print(f"🖼️ Image included: {'Yes' if image_url else 'No'}")
        print(f"💬 Engagement style: Value -> Question -> Topic CTA")
    else:
        print("\n❌ Failed to post to Twitter.")

if __name__ == "__main__":
    main()