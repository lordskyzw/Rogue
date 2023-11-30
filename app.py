import os
import re
import requests
import uuid
import openai
from PIL import Image
from utilities.tools import recipients_database, check_id_database, add_id_to_database, save_thread_id, get_thread_id, language_check
from admin import Rogue, Kim
from fastapi import FastAPI, Request, Response
import logging
from pygwan import WhatsApp

openai_api_key = os.environ.get("OPENAI_API_KEY")
oai = openai.OpenAI(api_key=openai_api_key)
rogue = Rogue()

recipients_db = recipients_database()
messenger = WhatsApp(
    token=os.environ.get("WHATSAPP_ACCESS_TOKEN"),
    phone_number_id=os.environ.get("PHONE_NUMBER_ID"),
)
VERIFY_TOKEN = "30cca545-3838-48b2-80a7-9e43b1ae8ce4"
TARMICA = "263779281345"
whitelist = [
    TARMICA,
    "263783560007"
    "263779293593",
    "263771229658",
    "263774882645",
    "263783429801",
    "263712933306",
    "263712463290"
]

image_pattern = r"https?://(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,6}(?:/[^/#?]+)+\.(?:png|jpe?g|gif|webp|bmp|tiff|svg)"

app = FastAPI()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

@app.get("/")
async def welcome():
    return {"message": "Welcome to my FastAPI application!"}

@app.get("/rogue")
async def verify_token(request: Request):
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")
    if hub_verify_token == VERIFY_TOKEN:
        logging.info("Verified webhook")
        return Response(content=hub_challenge, media_type="text/plain")
    logging.error("Webhook Verification failed")
    return "Invalid verification token"


@app.post("/rogue")
async def hook(request: Request):
    logging.info("Received webhook")
    data = await request.json()
    logging.info("Received webhook data: %s", data)
    changed_field = messenger.changed_field(data)
    if changed_field == "messages":
        new_message = messenger.is_message(data)
        if new_message:
            mobile = messenger.get_mobile(data)
            recipient = "".join(filter(str.isdigit, mobile))
            name = messenger.get_name(data)
            message_type = messenger.get_message_type(data)
            message_id = messenger.get_message_id(data=data)
            message_exists = check_id_database(message_id)
            #handling the echoes from Meta
            if message_exists:
                logging.error(f"=============================================================== MESSAGE ALREADY IN DATABASE")
                return "OK", 200
            elif not message_exists:
                add_id_to_database(message_id)
                if recipient not in whitelist:
                    messenger.send_template(template='heralding_rogue', recipient_id=recipient, lang='en')
                    return "OK", 200
                recipient_obj = {"id": recipient, "phone_number": recipient}
                if recipients_db.find_one(recipient_obj) is None:
                    try:
                        thread_response = oai.beta.threads.create()
                        thread_id = thread_response.id
                        save_thread_id(thread_id=thread_id, recipient=recipient)
                        recipients_db.insert_one(recipient_obj)
                    except Exception as e:
                        logging.error(f'================================================= THE FOLLOWING ERROR OCCURED: {e}')   
                logging.info(
                    f"======================================= NEW MESSAGE FROM:{name}, THREAD_ID:{get_thread_id(recipient=recipient)}"
                )
                ############################################### Text Message Handling ##########################################################
                if message_type == "text":
                    messenger.mark_as_read(message_id=message_id)
                    message = messenger.get_message(data)
                    if recipient == TARMICA:
                        response = rogue.create_message_and_get_response(content=message)
                        logging.info("RAW RESPONSE=================================================%s", response)
                        reply_contains_image = re.findall(image_pattern, response)
                        reply_without_links = re.sub(image_pattern, "", response)
                        colon_index = reply_without_links.find(":")
                        if colon_index != -1:
                            # Extract the substring before the colon (excluding the colon)
                            reply_without_links = reply_without_links[:colon_index]
                            # Remove leading and trailing spaces
                            reply_without_links = reply_without_links.strip()
                        if reply_contains_image:
                            logging.info("============================================================= :::CONTAINS IMAGE")
                            for image_url in reply_contains_image:
                                r = requests.get(image_url, allow_redirects=True)
                                image_name = f'{uuid.uuid4()}.png'
                                with open(image_name, 'wb') as f:
                                    f.write(r.content)
                                    f.close()
                                    logging.info(f"==================================================== SAVED IMAGE AS: {image_name}")
                                try:
                                    new_image_name = f'{uuid.uuid4()}.jpeg'
                                    with Image.open((os.path.realpath(image_name))) as img:
                                        rgb_im = img.convert('RGB')  # Convert to RGB
                                        rgb_im.save(new_image_name, 'JPEG', quality=90)  # Save as JPEG with quality 90
                                    image_id_dict = messenger.upload_media(media=(os.path.realpath(new_image_name)))
                                    messenger.send_image(
                                    image=image_id_dict["id"],
                                    recipient_id=TARMICA,
                                    caption=reply_without_links,
                                    link=False,)
                                    os.remove(path=(os.path.realpath(image_name)))
                                    os.remove(path=(os.path.realpath(new_image_name)))
                                except IOError as e:
                                    logging.error(f"==================================================== ERROR OCCURED: {e}")
                                    messenger.send_message(message=f"Error occured: {e}", recipient_id=TARMICA)
                                except Exception as e:
                                    logging.error(f"==================================================== ERROR OCCURED: {e}")
                                    messenger.send_message(message=f"Error occured: {e}", recipient_id=TARMICA)  
                        else:
                            messenger.reply_to_message(message_id=message_id, recipient_id=TARMICA, message=response)
                        
                    else:
                        #retrieve the user's thread object
                        thread_id = get_thread_id(recipient=recipient)
                        if thread_id == "no thread found":
                            logging.error(f"===============================ERROR: DATABASE OPERATION GONE WRONG LINE 94 in app.py")
                            return "OK", 200
                        kim = Kim(thread_id=thread_id)
                        response = kim.create_message_and_get_response(content=message)
                        messenger.reply_to_message(
                                message_id=message_id, message=response, recipient_id=mobile
                            )
                ############################## END TEXT MESSAGE HANDLING ###################################################
                ######################## Audio Message Handling ###########################################
                elif message_type == "audio":
                    audio = messenger.get_audio(data=data)
                    audio_id = audio["id"]
                    messenger.mark_as_read_by_winter(message_id=message_id)
                    audio_url = messenger.query_media_url(audio_id)
                    audio_uri = messenger.download_media(
                        media_url=audio_url, mime_type="audio/ogg"
                    )
                    audio_file = open(audio_uri, "rb")
                    try:
                        transcript = openai.audio.transcriptions.create(
                        model="whisper-1",
                        language="en", 
                        response_format="text",
                        file=audio_file
                        )
                        logging.info(f"====================================================== TRANSCRIPT: {transcript}")
                        if recipient == TARMICA:
                            if language_check(transcript=transcript):
                                reply = rogue.create_message_and_get_response(content=transcript)
                                reply_contains_image = re.findall(image_pattern, response)
                                reply_without_links = re.sub(image_pattern, "", response)
                                colon_index = reply_without_links.find(":")
                                if colon_index != -1:
                                    # Extract the substring before the colon (excluding the colon)
                                    reply_without_links = reply_without_links[:colon_index]
                                    # Remove leading and trailing spaces
                                    reply_without_links = reply_without_links.strip()
                                if reply_contains_image:
                                    logging.info("============================================================= ::: CONTAINS IMAGE")
                                    for image_url in reply_contains_image:
                                        r = requests.get(image_url, allow_redirects=True)
                                        open('image.png', 'wb').write(r.content)
                                        image_id_dict = messenger.upload_media(media=(os.path.realpath('image.png')))
                                        messenger.send_image(
                                            image=image_id_dict["id"],
                                            recipient_id=TARMICA,
                                            caption=reply_without_links,
                                            link=False,
                                        )
                                else:
                                    audio = rogue.create_audio(script=reply)
                                    audio_id_dict = messenger.upload_media(media=(os.path.realpath(audio)))
                                    messenger.send_audio(audio=audio_id_dict["id"], recipient_id=TARMICA, link=False)
                            elif language_check(transcript=transcript)==False:
                                messenger.reply_to_message(message_id=message_id, message="Sorry Tarmica, I didnt quite get that, may you please be clearer?", recipient_id=TARMICA)
                            else:
                                messenger.reply_to_message(message_id=message_id, message=f"In trying to determine if your english is correct or not, an error occured.", recipient_id=TARMICA)
                        else:
                            thread_id = get_thread_id(recipient=recipient)
                            if thread_id == "no thread found":
                                logging.error(f"===============================ERROR: DATABASE OPERATION GONE WRONG LINE 94 in app.py")
                                return "OK", 200
                            kim = Kim(thread_id=thread_id)
                            if language_check(transcript=transcript):
                                reply = kim.create_message_and_get_response(content=transcript)
                                audio = kim.create_audio(script=reply)
                                audio_id_dict = messenger.upload_media(media=(os.path.realpath(audio)))
                                messenger.send_audio(audio=audio_id_dict["id"], recipient_id=recipient, link=False)
                            elif language_check(transcript=transcript)==False:
                                messenger.reply_to_message(message_id=message_id, message="I didnt quite get that, may you please be clearer?", recipient_id=recipient)
                            else:
                                messenger.reply_to_message(message_id=message_id, message=f"In trying to determine if your english is correct or not, an error occured. This is a special case. Please show Tarmica Chiwara (0779281345) this:\n {language_check(transcript=transcript)}", recipient_id=recipient) 
                    except Exception as e:
                        messenger.reply_to_message(message_id=message_id, message=f"error occured {e.with_traceback()}", recipient_id=recipient)           
                ############################# End Audio Message Handling ######################################
                elif message_type == "image":
                    image = messenger.get_image(data=data)
                    image_id = image["id"]
                    messenger.mark_as_read_by_winter(message_id=message_id)
                    image_url = messenger.query_media_url(image_id)
                    image_uri = messenger.download_media(
                        media_url=image_url, mime_type="image/jpeg"
                    )
                    image_file = open(image_uri, "rb")
                elif message_type == "document":
                    messenger.send_message(
                        "I don't know how to handle documents yet", mobile
                    )
            else:
                delivery = messenger.get_delivery(data)
                if delivery:
                    logging.info(f"Message : {delivery}")
                else:
                    logging.info("No new message")
        return "OK", 200

