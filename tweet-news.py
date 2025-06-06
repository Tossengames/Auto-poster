import tweepy
import os
import random

print("🔧 Starting tweet script...")

# Authenticate with environment variables from GitHub Secrets
auth = tweepy.OAuth1UserHandler(
    os.getenv("TWITTER_API_KEY"),
    os.getenv("TWITTER_API_SECRET"),
    os.getenv("TWITTER_ACCESS_TOKEN"),
    os.getenv("TWITTER_ACCESS_SECRET")
)

api = tweepy.API(auth)

try:
    tweet = "🚀 Auto Tweet Test from GitHub! #" + str(random.randint(1000, 9999))
    print("📢 Tweet content:", tweet)
    api.update_status(tweet)
    print("✅ Tweet posted successfully.")
except Exception as e:
    print("❌ Failed to post tweet:", str(e))
