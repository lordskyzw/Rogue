import os
from tweepy import Client
import requests

class ChiefTwit(Client):
    def __init__(self):
        self.consumer_key = os.environ.get("twitter_consumer_key")
        self.consumer_secret = os.environ.get("twitter_consumer_secret")
        self.access_token = os.environ.get("twitter_access_token")
        self.access_token_secret = os.environ.get("twitter_access_token_secret")
        self.client = Client(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
        )

    def write_tweet(self, text):
        """use when you need to write/send/make a tweet"""
        response = self.client.create_tweet(text=text)
        if response.errors == []:
            return "Successful" 
        else:
            return "Something went wrong"

    def get_tweets(self, username):
        self.client.get_user(username)

    def get_followers(self, username):
        self.client.get_followers(username)

    def get_following(self, username):
        self.client.get_following(username)

    def get_user(self, username):
        self.client.get_user(username)

class WebGallery:
    def __init__(self):
        self.api_key = os.environ.get("SERP_API_KEY")
        self.base_url = "https://serpapi.com/search?engine=google_images"

    def search(self, query):
        parameters = {"q": query, "engine": "google_images", "api_key": self.api_key}
        response = requests.get(self.base_url, params=parameters)
        response = response.json()
        return response["images_results"][0]["original"]

def set_rate():
    pass