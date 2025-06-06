import { TwitterApi } from 'twitter-api-v2';

async function main() {
  const client = new TwitterApi({
    appKey: process.env.TWITTER_API_KEY,
    appSecret: process.env.TWITTER_API_SECRET,
    accessToken: process.env.TWITTER_ACCESS_TOKEN,
    accessSecret: process.env.TWITTER_ACCESS_SECRET,
  });

  const rwClient = client.readWrite;

  try {
    const tweet = await rwClient.v2.tweet('Hello from GitHub Actions using Node.js!');
    console.log('Tweet posted successfully:', tweet);
  } catch (error) {
    console.error('❌ Error posting tweet:', error);
    process.exit(1);
  }
}

main();
