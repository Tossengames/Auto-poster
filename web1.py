import feedparser
import openai
import random
import re
from datetime import datetime

openai.api_key = "YOUR_API_KEY"

# --------------------------------------------
# 1. RSS FEEDS (Web3 Only)
# --------------------------------------------
WEB3_FEEDS = [
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "https://thedefiant.io/feed",
    "https://blockworks.co/feed",
]

# --------------------------------------------
# 2. Filtering: Skip useless promotional junk
# --------------------------------------------
SKIP_KEYWORDS = [
    "airdrop", "giveaway", "casino", "gambling",
    "sponsored", "token sale", "pre-sale", "ICO",
    "bonus", "affiliate"
]

# --------------------------------------------
# 3. Hashtag Generator
# Creates hashtags based on topic
# --------------------------------------------
def generate_hashtags(text):
    base_tags = ["#Web3", "#Crypto", "#Blockchain"]

    topic_tags_map = {
        "Bitcoin": ["#BTC", "#Bitcoin"],
        "Ethereum": ["#ETH", "#Ethereum"],
        "DeFi": ["#DeFi", "#YieldFarming", "#DEX"],
        "NFT": ["#NFT", "#NFTCommunity", "#NFTs"],
        "security": ["#Web3Security", "#CryptoSecurity"],
        "hack": ["#Exploit", "#SecurityAlert"],
        "smart contract": ["#SmartContracts", "#Solidity"],
        "AI": ["#AI", "#AICrypto"],
    }

    final_tags = base_tags.copy()

    for keyword, tags in topic_tags_map.items():
        if keyword.lower() in text.lower():
            final_tags.extend(tags)

    final_tags = list(set(final_tags))
    return " ".join(final_tags[:6])

# --------------------------------------------
# 4. AI Content Generator
# Creates valuable Web3 posts (not shallow)
# --------------------------------------------
def create_web3_post(title, summary, link):
    prompt = f"""
You are an expert Web3 researcher.

Write a **high-value Twitter/X post** about this article:

Title: {title}
Summary: {summary}

Your output MUST follow this structure:

1. **A strong hook**
2. **A useful explanation**
3. **A valuable insight or warning**
4. **A practical takeaway**
5. **Smart hashtags** (based on topic)

Keep it short, punchy, and valuable.
Do NOT repeat the title.
Do NOT mention the article or say “according to”.
Do NOT include any links.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    post = response["choices"][0]["message"]["content"]
    hashtags = generate_hashtags(title + " " + summary)

    return post + "\n\n" + hashtags

# --------------------------------------------
# 5. Fetch & Filter Articles
# --------------------------------------------
def fetch_articles():
    items = []

    for feed in WEB3_FEEDS:
        parsed = feedparser.parse(feed)

        for entry in parsed.entries:
            text = (entry.title + " " + entry.get("summary", "")).lower()

            if any(bad in text for bad in SKIP_KEYWORDS):
                continue

            items.append({
                "title": entry.title,
                "summary": entry.get("summary", ""),
                "link": entry.link
            })

    return items

# --------------------------------------------
# 6. MAIN – Generate a Post
# --------------------------------------------
def generate_web3_content():
    articles = fetch_articles()

    if not articles:
        return "No suitable Web3 content found."

    chosen = random.choice(articles)

    return create_web3_post(
        title=chosen["title"],
        summary=chosen["summary"],
        link=chosen["link"]
    )

# --------------------------------------------
# 7. Run the Script Once
# --------------------------------------------
if __name__ == "__main__":
    print(generate_web3_content())