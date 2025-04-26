import argparse
import json
import datetime
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

# Load cookies from a file to authenticate Twitter
def load_cookies(context, cookies_file):
    try:
        with open(cookies_file, 'r') as file:
            cookies = json.load(file)
            for cookie in cookies:
                if 'sameSite' not in cookie or cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                    cookie['sameSite'] = 'Lax'
            context.add_cookies(cookies)
        print(f"✅ Cookies loaded from {cookies_file}")
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")

# Function to scrape user tweets from a specific period
def scrape_user_tweets(username: str, start_date: datetime.date, end_date: datetime.date):
    tweets_data = []

    def capture_user_tweets(response):
        if "UserTweets" in response.url:
            try:
                json_data = response.json()
                instructions = json_data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
                for instruction in instructions:
                    if instruction.get("type") in ["TimelinePinEntry", "TimelineAddEntries"]:
                        entries = instruction.get("entries", [])
                        if instruction.get("type") == "TimelinePinEntry":
                            entries = [instruction.get("entry", {})]
                        for entry in entries:
                            if entry.get("entryId", "").startswith("tweet-"):
                                content = entry.get("content", {})
                                item = content.get("itemContent", {})
                                tweet = item.get("tweet_results", {}).get("result", {})
                                legacy = tweet.get("legacy", {})
                                if legacy:
                                    tweet_id = tweet.get("rest_id")
                                    tweet_text = legacy.get("full_text")
                                    tweet_created_at = legacy.get("created_at")
                                    
                                    # Check for missing data
                                    if not tweet_text or not tweet_created_at:
                                        print(f"❌ Missing text or created_at for tweet ID: {tweet_id}")
                                        continue
                                    
                                    tweet_date = datetime.strptime(tweet_created_at, "%a %b %d %H:%M:%S +0000 %Y")
                                    
                                    # Extract user data with improved logic
                                    tweet_user = tweet.get("core", {}).get("user_results", {}).get("result", {})
                                    tweet_user_screen_name = tweet_user.get("screen_name", "Unknown")
                                    tweet_user_id = tweet_user.get("rest_id")
                                    tweet_user_verified = tweet_user.get("verified", False)
                                    tweet_user_followers_count = tweet_user.get("followers_count", 0)
                                    tweet_user_following_count = tweet_user.get("following_count", 0)
                                    
                                    # If it's a retweet, get the original user's details
                                    if 'retweeted_status' in legacy:
                                        retweeted_user = legacy['retweeted_status'].get('user', {})
                                        tweet_user_screen_name = retweeted_user.get('screen_name', tweet_user_screen_name)
                                        tweet_user_id = retweeted_user.get('rest_id', tweet_user_id)
                                        tweet_user_verified = retweeted_user.get('verified', tweet_user_verified)
                                        tweet_user_followers_count = retweeted_user.get('followers_count', tweet_user_followers_count)
                                        tweet_user_following_count = retweeted_user.get('following_count', tweet_user_following_count)
                                    
                                    tweet_likes_count = legacy.get("favorite_count", 0)
                                    tweet_retweets_count = legacy.get("retweet_count", 0)
                                    tweet_quote_count = legacy.get("quote_count", 0)
                                    tweet_reply_count = legacy.get("reply_count", 0)
                                    tweet_is_retweet = 'retweeted_status' in legacy
                                    tweet_retweeted_from_user = legacy.get('retweeted_status', {}).get('user', {}).get('screen_name', None)
                                    tweet_source = legacy.get("source")
                                    tweet_language = legacy.get("lang")
                                    
                                    # Hashtags & Mentions
                                    tweet_hashtags = [hashtag['text'] for hashtag in legacy.get('entities', {}).get('hashtags', [])]
                                    tweet_mentions = [mention['screen_name'] for mention in legacy.get('entities', {}).get('user_mentions', [])]
                                    
                                    # Media URLs (Improved URL parsing)
                                    tweet_media_urls = []
                                    tweet_media_type = None
                                    tweet_media_alt_text = None
                                    if 'extended_entities' in legacy:
                                        media = legacy['extended_entities'].get('media', [])
                                        for m in media:
                                            tweet_media_urls.append(m.get('media_url_https'))
                                            tweet_media_type = m.get('type')
                                            tweet_media_alt_text = m.get('alt_text')
                                    
                                    # Geolocation and User's location
                                    tweet_location = tweet_user.get('location', None)
                                    tweet_geo_enabled = tweet_user.get('geo_enabled', False)

                                    # URLs in tweet text (Handle missing expanded_url)
                                    tweet_urls = []
                                    for url in legacy.get('entities', {}).get('urls', []):
                                        expanded_url = url.get('expanded_url')
                                        if expanded_url:
                                            tweet_urls.append(expanded_url)
                                        else:
                                            print(f"❌ Missing expanded_url for tweet ID: {tweet_id}")
                                    
                                    # Create the tweet object
                                    tweet_obj = {
                                        "id": tweet_id,
                                        "text": tweet_text,
                                        "created_at": tweet_created_at,
                                        "created_at_timestamp": int(time.mktime(tweet_date.timetuple())),
                                        "username": tweet_user_screen_name,
                                        "user_id": tweet_user_id,
                                        "user_screen_name": tweet_user_screen_name,
                                        "user_verified": tweet_user_verified,
                                        "user_followers_count": tweet_user_followers_count,
                                        "user_following_count": tweet_user_following_count,
                                        "likes_count": tweet_likes_count,
                                        "retweets_count": tweet_retweets_count,
                                        "quote_count": tweet_quote_count,
                                        "reply_count": tweet_reply_count,
                                        "is_retweet": tweet_is_retweet,
                                        "retweeted_from_user": tweet_retweeted_from_user,
                                        "tweet_source": tweet_source,
                                        "hashtags": tweet_hashtags,
                                        "mentions": tweet_mentions,
                                        "media_urls": tweet_media_urls,
                                        "media_type": tweet_media_type,
                                        "media_alt_text": tweet_media_alt_text,
                                        "location": tweet_location,
                                        "geo_enabled": tweet_geo_enabled,
                                        "language": tweet_language,
                                        "tweet_url": f"https://twitter.com/{tweet_user_screen_name}/status/{tweet_id}",
                                        "urls": tweet_urls,
                                    }
                                    
                                    tweets_data.append(tweet_obj)
                                    print(f"🧠 Fetched {len(tweets_data)} tweets within the specified period.")
                                else:
                                    print(f"❌ Missing legacy data for tweet ID: {tweet.get('rest_id')}")
            except Exception as e:
                print(f"❌ Failed to parse UserTweets: {e}")

    # Main scraping logic
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)  # Set to True for headless mode
        context = browser.new_context()
        load_cookies(context, 'twitter_cookies.json')  # Replace with your actual cookie file
        page = context.new_page()

        # Set up network response listeners
        page.on("response", capture_user_tweets)

        # Navigate to the user's profile
        print(f"🌐 Navigating to https://x.com/{username}")
        page.goto(f"https://x.com/{username}")
        page.wait_for_selector("article")
        print("✅ Timeline loaded.")

        # Scroll and fetch tweets until all are loaded
        max_scrolls = 10
        last_height = page.evaluate("document.body.scrollHeight")
        scroll_count = 0

        while scroll_count < max_scrolls:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)  # Wait for tweets to load
            new_height = page.evaluate("document.body.scrollHeight")

            # Stop scrolling if the height hasn't changed (end of the timeline)
            if new_height == last_height:
                break

            last_height = new_height
            scroll_count += 1
            print(f"🔄 Scrolled {scroll_count}/{max_scrolls}")

        # Close the browser only after scraping is complete
        browser.close()

    # Save the tweets to a file
    with open(f"{username}_tweets.json", "w") as f:
        json.dump(tweets_data, f, indent=2)
    print(f"📁 Saved tweets to {username}_tweets.json")

# Command line argument setup
def main():
    parser = argparse.ArgumentParser(description="Scrape tweets from a user within a period.")
    parser.add_argument("username", type=str, help="The username of the Twitter user")
    parser.add_argument("start_date", type=str, help="The start date (YYYY-MM-DD) of the period")
    parser.add_argument("end_date", type=str, help="The end date (YYYY-MM-DD) of the period")

    args = parser.parse_args()

    # Parse the dates
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    scrape_user_tweets(args.username, start_date, end_date)

if __name__ == "__main__":
    main()
