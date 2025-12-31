import os
import random
import feedparser
import re
import tweepy

# ✅ NEW Gemini SDK (FIXED)
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
# INITIALIZE GEMINI (FIXED)
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

def extract_hashtags_from_text(text, max_tags=3):
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    common = sorted(set(words), key=lambda w: -words.count(w))
    tags = []

    for w in common:
        tag = "#" + w.capitalize()
        if tag not in tags:
            tags.append(tag)
        if len(tags) == max_tags:
            break

    return " ".join(tags)

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
# GENERATE TWEET (FIXED)
# =============================

def generate_engaging_post():
    entries = parse_reddit_rss()
    if not entries:
        print("No valid RSS entries found.")
        return None, None

    entry = random.choice(entries)
    posted_links.add(entry['link'])

    hashtag_text = extract_hashtags_from_text(
        entry['title'] + " " + entry['summary']
    )

    prompt = (
        f"Create ONE standalone, easy-to-read tweet about this online discussion:\n\n"
        f"Title: {entry['title']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"Requirements:\n"
        f"- Funny/observational about modern life, work, relationships or internet behavior\n"
        f"- Use line breaks and emojis for readability\n"
        f"- Include about 3 hashtags (not at start)\n"
        f"- Must make sense by itself\n"
        f"- Max 250 characters including hashtags\n"
        f"- Do NOT mention Reddit or sources\n\n"
        f"Example format:\n"
        f"😂 First thought here.\n\n"
        f"🤔 Another thought.\n\n"
        f"#Hashtag1 #Hashtag2 #Hashtag3"
    )

    try:
        # ✅ NEW SAFE GEMINI CALL
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

        text = re.sub(r'\*\*|\*|__|_', '', text).strip()

        final_tweet = f"{text}\n\n{hashtag_text}"

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