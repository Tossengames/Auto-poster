import tweepy
import os

def tweet_hello():
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_SECRET")

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api = tweepy.API(auth)

    try:
        api.update_status("Hello from GitHub Actions!")
        print("✅ Tweet posted successfully!")
    except Exception as e:
        print("❌ Error posting tweet:", e)

if __name__ == "__main__":
    tweet_hello()
