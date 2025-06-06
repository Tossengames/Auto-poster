import feedparser
import tweepy
import os
import random

# Twitter auth
api_key = os.environ["TWITTER_API_KEY"]
api_secret = os.environ["TWITTER_API_SECRET"]
access_token = os.environ["TWITTER_ACCESS_TOKEN"]
access_secret = os.environ["TWITTER_ACCESS_SECRET"]

auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
api = tweepy.API(auth)

# Sports RSS feed (you can change this to any)
rss_url = "http://feeds.bbci.co.uk/sport/rss.xml"
feed = feedparser.parse(rss_url)

# Choose latest news
entry = feed.entries[0]
title = entry.title
link = entry.link

# Add hashtags
hashtags = ["#Sports", "#BreakingNews", "#Football", "#NBA", "#F1", "#Soccer", "#Tennis"]
random.shuffle(hashtags)
tags = " ".join(hashtags[:3])

# Final tweet
tweet = f"{title}\n{link}\n{tags}"
api.update_status(tweet)
