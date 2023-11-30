import os
from openai import OpenAI
from tweepy import Client
from serpapi import GoogleSearch
import requests

oai = OpenAI(api_key=(os.environ.get("OPENAI_API_KEY")))

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


class SearchProcessor:
    def __init__(self):
        self.api_key = os.environ.get("SERP_API_KEY")
        self.base_url = "https://serpapi.com" 

    def get_search_results(self, query):
        """Method to interact with the API and get the search results."""
        params = {
            "q": query,
            "api_key": self.api_key
        }
        try:
            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def _process_response(self, res):
        """Process response from the API."""
        if "error" in res:
            raise ValueError(f"Got error from API: {res['error']}")

        toret = "No good search result found"

        if "answer_box" in res:
            answer_box = res["answer_box"][0] if isinstance(res["answer_box"], list) else res["answer_box"]
            if "answer" in answer_box:
                toret = answer_box["answer"]
            elif "snippet" in answer_box:
                toret = answer_box["snippet"]
            elif "snippet_highlighted_words" in answer_box:
                toret = answer_box["snippet_highlighted_words"][0]

        elif "sports_results" in res and "game_spotlight" in res["sports_results"]:
            toret = res["sports_results"]["game_spotlight"]

        elif "shopping_results" in res and res["shopping_results"]:
            toret = res["shopping_results"][:3]

        elif "knowledge_graph" in res and "description" in res["knowledge_graph"]:
            toret = res["knowledge_graph"]["description"]

        elif "organic_results" in res and res["organic_results"]:
            if "snippet" in res["organic_results"][0]:
                toret = res["organic_results"][0]["snippet"]
            elif "link" in res["organic_results"][0]:
                toret = res["organic_results"][0]["link"]

        elif "images_results" in res and res["images_results"]:
            thumbnails = [item["thumbnail"] for item in res["images_results"][:10]]
            toret = thumbnails

        return toret

    def run(self, query):
        """Run query through the API and parse result."""
        return self._process_response(self.get_search_results(query))


def create_image(description: str):
    '''this function should generate an image and return url'''
    res = oai.images.generate(
        prompt=description,
        model="dall-e-3",
        n=1,
        quality="standard",
        style="vivid",
        size="1024x1024",
        response_format="url"
        )
    try:
        url = res.data[0].url
        return url
    except Exception as e:
        return str(e)

def search(query):
    google = GoogleSearch(params_dict={'q': query, 'api_key': os.environ.get('SERP_API_KEY')})
    results = google.get_results()
    return results