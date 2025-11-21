import os
import tweepy

# Get from GitHub Secrets
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

def post_to_twitter():
    """Post a simple test message to Twitter"""
    try:
        print("Testing Twitter connection...")
        
        # Authenticate with Twitter API
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)
        
        # Simple human-sounding message
        messages = [
            "Interesting how technology continues to reshape our daily interactions. The pace of change never slows.",
            "Observing patterns in how people adapt to new tools reveals so much about human nature and innovation.",
            "The intersection of creativity and technology always produces the most fascinating developments worth watching.",
            "Some days you notice the small shifts that eventually become major trends. Today feels like one of those days."
        ]
        
        import random
        message = random.choice(messages)
        
        # Post the tweet
        response = api.update_status(message)
        
        print("✅ Success! Tweet posted:")
        print(f"📝 {message}")
        print(f"🔗 Tweet ID: {response.id}")
        return True
            
    except tweepy.TweepyException as e:
        print(f"❌ Twitter API error: {e}")
        return False
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

if __name__ == "__main__":
    post_to_twitter()