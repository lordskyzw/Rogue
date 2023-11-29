import os
import logging
from pymongo import MongoClient
from openai import OpenAI

token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
phone_number_id = os.environ.get("PHONE_NUMBER_ID")
v15_base_url = "https://graph.facebook.com/v17.0"
openai_api_key = str(os.environ.get("OPENAI_API_KEY"))
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
oai = OpenAI(api_key=(os.environ.get("OPENAI_API_KEY")))

######################################## users database functions ########################################
def recipients_database():
    """users' database connection object"""
    client = MongoClient(
        "mongodb://mongo:xQxzXZEzUilnKKhrbELE@containers-us-west-114.railway.app:6200"
    )
    database = client["users"]
    collection = database["recipients"]
    return collection

def check_id_database(message_stamp: str):
    """Check if a message_stamp(combination of conersation_id+message_id) is in the database or not."""
    # users' database connection object
    client = MongoClient(
        "mongodb://mongo:xQxzXZEzUilnKKhrbELE@containers-us-west-114.railway.app:6200"
    )
    database = client["Readit"]
    collection = database["messageids"]

    # Query the collection to check if the message_id exists
    query = {"message_stamp": message_stamp}
    result = collection.find_one(query)

    # Close the database connection
    client.close()

    # If the result is not None, the message_id exists in the database
    return result is not None

def add_id_to_database(message_stamp: str):
    """Add a message_stamp to the database."""
    # users' database connection object
    client = MongoClient(
        "mongodb://mongo:xQxzXZEzUilnKKhrbELE@containers-us-west-114.railway.app:6200"
    )
    database = client["Readit"]
    collection = database["messageids"]
    document = {"message_stamp": message_stamp}
    collection.insert_one(document)
    client.close()  
    
def save_thread_id(thread_id : str, recipient):
    """saves a user's thread id in the MongoDB database."""
    try:
        client = MongoClient("mongodb://mongo:xQxzXZEzUilnKKhrbELE@containers-us-west-114.railway.app:6200")
        database = client["users"]
        collection = database["threads"]
        query = {"key": recipient}
        new_values = {"$set": {"thread_id": thread_id}}
        result = collection.update_one(query, new_values, upsert=True)
        client.close()
        if result.modified_count > 0 or result.upserted_id is not None:
            logging.info("===================================SAVED THREAD_ID: %s", thread_id)
            return "success"
        else:
            return "failed"
    except Exception as e:
        print(f"An error occurred: {e}")
        return "failed"

def get_thread_id(recipient):
    """Fetches the recipient's thread id from the MongoDB database."""
    client = MongoClient("mongodb://mongo:xQxzXZEzUilnKKhrbELE@containers-us-west-114.railway.app:6200")
    database = client["users"]
    collection = database["threads"]
    query = {"key": recipient}
    result = collection.find_one(query)
    if result and 'thread_id' in result:
        logging.info("===================================FETCHED THREAD_ID: %s", result['thread_id'])
        return str(result['thread_id'])
    else:
        return "no thread found" # Or a default rate if not found
    
def language_check(transcript: str):
    '''This function checks if the argument is english which makes sense or not'''
    content = f"""Classes: [`sensible`, `non-sensible`]
    Text: {transcript}
    classify the text into one of the above classes.
    If you think the text is sensible, type `sensible` otherwise type `non-sensible`. ONLY TYPE THE WORDS IN THE QUOTES."""
    completion = oai.chat.completions.create(
    model="gpt-3.5-turbo",
    temperature=0.6,
    messages=[
        {"role": "user", "content": content},
    ]
    )
    if completion.choices[0].message.content == 'sensible':
        return True
    elif completion.choices[0].message.content == 'non-sensible':
        return False
    else:
        logging.error(f"===================================ERROR IN DETERMINING LEGIBILITY OF THE ENGLISH: {completion.choices[0].message.content}")
        return completion.choices[0].message.content
    