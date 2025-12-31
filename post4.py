import os
import random
import feedparser
import re
import tweepy

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
MODEL_NAME = "gemini-2.5-flash"

# =============================
# REDDIT RSS FEEDS
# =============================

REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/AskReddit/.rss",
    "https://www.reddit.com/r/relationships/.rss",
    "https://www.reddit.com/r/antiwork/.rss",
    "https://www.reddit.com/r/selfimprovement/.rss",
    "https://www.reddit.com/r/technology/.rss"
]

posted_links = set()

# =============================
# TWITTER API
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
# HELPERS
# =============================

def contains_political_content(text):
    POLITICAL_KEYWORDS = [
        'trump','biden','president','election','government','policy',
        'tax','war','political','democrat','republican','vote'
    ]
    return any(k in text.lower() for k in POLITICAL_KEYWORDS) if text else False

# =============================
# PARSE REDDIT RSS
# =============================

def parse_reddit_rss():
    entries = []

    for url in REDDIT_RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.link in posted_links:
                    continue
                if contains_political_content(entry.title) or contains_political_content(entry.get('summary', '')):
                    continue

                entries.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary', '')
                })
        except Exception as e:
            print(f"RSS error {url}: {e}")

    return entries

# =============================
# GENERATE TWEET (NEUTRAL VOICE)
# =============================

def generate_engaging_post():
    entries = parse_reddit_rss()
    if not entries:
        print("No valid RSS entries found.")
        return None, None

    entry = random.choice(entries)
    posted_links.add(entry['link'])

    prompt = (
        f"Create ONE standalone, easy-to-read tweet about this online discussion:\n\n"
        f"Title: {entry['title']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"Requirements:\n"
        f"- Funny or insightful observation about modern life, work, relationships, or internet culture\n"
        f"- MUST be written in third-person or neutral tone\n"
        f"- DO NOT use first-person words (I, me, my, we, our, us)\n"
        f"- No personal storytelling\n"
        f"- Use line breaks and emojis for readability\n"
        f"- Include about 3 hashtags at the END\n"
        f"- Must make sense by itself\n"
        f"- Max 250 characters\n"
        f"- Do NOT mention Reddit or sources\n\n"
        f"Example style:\n"
        f"People say technology saves time.\n"
        f"Funny how everyone feels busier than ever. 🤔\n\n"
        f"#ModernLife #TechCulture #WorkLife"
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
            raise ValueError("Gemini returned no text content")

        # Clean markdown
        text = re.sub(r'\*\*|\*|__|_', '', text).strip()

        # Remove duplicate hashtags
        text = re.sub(r'(#\w+)(\s+\1)+', r'\1', text)

        # HARD safety: remove first-person if any slip through
        text = re.sub(r'\b(I|me|my|we|our|us)\b', '', text, flags=re.IGNORECASE)

        final_tweet = text

        if len(final_tweet) > 280:
            final_tweet = final_tweet[:277] + "..."

        return final_tweet, None

    except Exception as e:
        print(f"AI generation failed: {e}")
        return None, None

# =============================
# MAIN
# =============================

def main():
    print("🐦 Reddit Content - Twitter Edition")

    if not all([
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    ]):
        print("❌ Missing Twitter API credentials")
        return

    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return

    post_text, _ = generate_engaging_post()
    if not post_text:
        print("❌ AI failed to generate a tweet. Skipping post.")
        return

    print(f"Tweet:\n{post_text}\n")

    success = post_to_twitter(
        post_text,
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET
    )

    print("✅ Posted!" if success else "❌ Failed to post.")

if __name__ == "__main__":
    main()