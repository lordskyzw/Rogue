import os
from tweepy import Client
from serpapi import GoogleSearch
import requests
import base64
from openai import OpenAI
from pygwan import WhatsApp
from utilities.toolbox import fetch_from_phonebook
import logging


token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
phone_number_id = os.environ.get("PHONE_NUMBER_ID")
openai_api_key = str(os.environ.get("OPENAI_API_KEY"))
messenger = WhatsApp(token=token, phone_number_id=phone_number_id)
oai = OpenAI(api_key=openai_api_key)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

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


def encode_image(image_path):
    '''This function encodes an image into base64'''
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

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

def analyze_images_with_captions(image_url: str, caption: str):
    """
    Analyzes images using OpenAI's GPT-4-Vision model and returns the analysis.

    :param image_urls: A list of image URLs to be analyzed.
    :param captions: A list of captions corresponding to the images.
    :return: The response from the OpenAI API.
    """
    if not image_url or not caption:
        raise ValueError("Image and captions cannot be empty")
    
    image_uri = messenger.download_media(media_url=image_url, mime_type="image/jpeg")
    base64_image = encode_image(image_uri)
    
    # Construct the messages payload
    messages = []
    message = {
        "role": "user",
        "content": [
            {"type": "text", "text": caption},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",}
            }
        ]
    }
    messages.append(message)

    # Send the request to OpenAI
    response = oai.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=messages,
        max_tokens=300
    )

    return response.choices[0].message.content

def search(query):
    google = GoogleSearch(params_dict={'q': query, 'api_key': os.environ.get('SERP_API_KEY')})
    results = google.get_results()
    return results

def get_drug_info(drug: str):
    '''This function should check for drug interactions between two drugs'''
    base_url = "https://www.britelink.io/api/v1/drug_names"
    headers = {"Authorization": f"Bearer {os.environ.get('BRITELINK_API_KEY')}"}
    params =  {"q": drug,
               "f": True}
    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        # Return the first element of the list (assuming there's only one result)
        if data:
            return data[0]
        else:
            return None
    else:
        # Handle errors gracefully

        return str(response.status_code)
    
def get_drug_interaction(*drugs):
    '''This function checks for drug interactions between two or more drugs'''
    # Base URL for the drug interactions API endpoint
    base_url = "https://www.britelink.io/api/v1/ddi"

    # Authorization header with API key
    headers = {
        "Authorization": f"Bearer {os.environ.get('BRITELINK_API_KEY')}"
    }
    drug_ids = []
    for drug in drugs:
        # Get drug information
        drug_info = get_drug_info(drug)
        if not drug_info:
            return f"Failed to retrieve drug information for {drug}"

        # Add the drug ID to the list
        drug_ids.append(drug_info["id"])
    # Parameters for the request
    drug_ids_str = ','.join(drug_ids)
    params = {
        "drug_Ids": ','.join(drug_ids_str)  # Convert drugs to a comma-separated string
    }

    try:
        # Make the HTTP GET request
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for any HTTP errors

        # Parse the JSON response
        data = response.json()

        # Extract drug interaction details
        interactions = data.get("interactions", [])
        if interactions:
            interaction_details = []
            for interaction in interactions:
                ingredient = interaction.get("ingredient", {}).get("name", "Unknown")
                affected_ingredients = [affected.get("name", "Unknown") for affected in interaction.get("affected_ingredient", [])]
                description = interaction.get("description", "No description available")
                severity = interaction.get("severity", "Unknown")
                management = interaction.get("management", "No management information available")

                interaction_details.append({
                    "Ingredient": ingredient,
                    "Affected Ingredients": affected_ingredients,
                    "Description": description,
                    "Severity": severity,
                    "Management": management
                })

            return interaction_details
        else:
            return "No drug interactions found."


    except requests.exceptions.RequestException as e:
        # Handle HTTP request errors
        return f"HTTP Request Error: {e}"
        
def contact(person: str, message: str):
    '''This function should send a message to a person'''
    contact_details = str(fetch_from_phonebook(person))
    logging.info("Contact details===================== %s", contact_details)

    logging.info("Contact details===================== %s", contact_details)
    try:
        messenger.send_payload_template_with_header(template_name="apollo", recipient_id=contact_details, header_variables=[person], payload_variables=[message])
        return "Message sent successfully"
    except Exception as e:
        return str(e)
    