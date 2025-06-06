import tweepy
import os

auth = tweepy.OAuth1UserHandler(
    os.getenv("TWITTER_API_KEY"),
    os.getenv("TWITTER_API_SECRET"),
    os.getenv("TWITTER_ACCESS_TOKEN"),
    os.getenv("TWITTER_ACCESS_SECRET")
)

api = tweepy.API(auth)

try:
    tweet = "🚀 Test tweet from GitHub Actions! #AutoTweet"
    api.update_status(tweet)
    print("✅ Tweet posted:", tweet)
except Exception as e:
    print("❌ Tweet failed:", str(e))
