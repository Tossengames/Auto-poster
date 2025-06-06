import os
import tweepy

def main():
    # Get Twitter API keys from environment variables
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_secret = os.getenv('TWITTER_ACCESS_SECRET')

    # Authenticate to Twitter
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api = tweepy.API(auth)

    # Post a tweet
    api.update_status("Hello from GitHub Actions! 🚀")

if __name__ == "__main__":
    main()
