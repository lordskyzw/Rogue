# Description: This is the main file for the AI SYSTEM. It handles all the incoming messages and sends them to the appropriate AI for processing.
import openai
from utilities.toolbox import *
from utilities.agents import Rogue, Agent
from utilities.generics import *
from fastapi import FastAPI, Request, Response
import logging
from utilities.generics import get_recipient_chat_history

rogue = Rogue()
recipients_db = recipients_database()


VERIFY_TOKEN = "30cca545-3838-48b2-80a7-9e43b1ae8ce4"
TARMICA = "263779281345"
beta = [
        "263784037241",# ~Ck
        "265982659389",
        "263774694160",
        "263787902521",
        "263777213597",
        "48504298321",
        "263786913190",
        "263716065423",
        "263784908771",
        "263771229658",
        "263786936685",
        "263712699365",
        "263786990464",
        "263783525762",
        "263778923849",
        "263788667111",
        "263782314894",
        "263713965702",
        "263777859397",
        "263786072641",
        "263776555142",
        "263783525762",
        "263718178416",
        #TARMICA,
    ]
whitelist = beta + [TARMICA]

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
    data = await request.json()
    logging.info("Received webhook data: %s", data)
    changed_field = messenger.changed_field(data)
    if changed_field == "messages":
        new_message = messenger.is_message(data)
        if new_message:
            recipient = "".join(filter(str.isdigit, (messenger.get_mobile(data))))
            name = messenger.get_name(data)
            message_type = messenger.get_message_type(data)
            message_id = messenger.get_message_id(data=data)
            message_exists = check_id_database(message_id)
            #handling the echoes from Meta
            if message_exists:
                logging.info(f"=============================================================== MESSAGE ALREADY IN DATABASE")
                return "OK", 200
            elif not message_exists:
                add_id_to_database(message_id)
                if recipient not in whitelist:
                    messenger.reply_to_message(message="umm...this is awkward but you don't have access. Ask Tarmica nicely (wa.me/263779281345)", recipient_id=recipient, message_id=message_id)
                    return "OK", 200
                
                history = get_recipient_chat_history(recipient=recipient)
                recipient_obj = {"id": recipient, "phone_number": recipient}
                if recipients_db.find_one(recipient_obj) is None:
                    try:
                        thread_response = oai.beta.threads.create()
                        thread_id = thread_response.id
                        save_thread_id(thread_id=thread_id, recipient=recipient)
                        recipients_db.insert_one(recipient_obj)
                        logging.info(f"++++++++++++++++++++++++++++++++++++++++++++ NEW USER ADDED TO DATABASE: {recipient}")
                    except Exception as e:
                        logging.error(f'================================================= THE FOLLOWING ERROR OCCURED: {e}')   
                logging.info(f"======================================= NEW MESSAGE FROM:{name}, THREAD_ID:{get_thread_id(recipient=recipient)}")
                ############################################### Text Message Handling ##########################################################
                if message_type == "text":
                    messenger.mark_as_read(message_id=message_id)
                    message = messenger.get_message(data)
                    if recipient == TARMICA:
                        response = rogue.create_message_and_get_response(content=message)
                        logging.info("RAW RESPONSE=================================================%s", response)
                        response_handler(response=response, recipient_id=TARMICA, message_id=message_id) 
                    elif (recipient != TARMICA) and (recipient in beta):
                        ghost = Chipoko(recipient=recipient, name=name)
                        response = ghost.create_message_and_get_response(message=message)
                        logging.info("RAW RESPONSE=================================================%s", response)
                        response_handler(response=response, recipient_id=recipient, message_id=message_id)
                    else:
                        #retrieve the user's thread object
                        thread_id = get_thread_id(recipient=recipient)
                        if thread_id == "no thread found":
                            messenger.reply_to_message(message_id=message_id, message="Sorry, an error occured. Couldnt find a thread for you.\n\nPlease show this message to Tarmica (https://wa.me/263779281345)", recipient_id=recipient)
                            logging.error(f"===============================ERROR: DATABASE OPERATION GONE WRONG LINE 94 in app.py")
                            return "OK", 200
                        kim = Agent(thread_id=thread_id)
                        response = kim.create_message_and_get_response(content=message)
                        response_handler(response=response, recipient_id=recipient, message_id=message_id)
                ############################## END TEXT MESSAGE HANDLING ################################################################################
                ######################## Audio Message Handling #########################################################################################
                elif message_type == "audio":
                    audio = messenger.get_audio(data=data)
                    audio_url = messenger.query_media_url(audio["id"])
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
                        is_audio_sensible_english = language_check(transcript=transcript)
                        history.add_user_message(transcript)
                        if recipient == TARMICA:
                            if is_audio_sensible_english == True:
                                messenger.mark_as_read(message_id=message_id)
                                reply = rogue.create_message_and_get_response(content=transcript)
                                audio_response_handler(response=reply, recipient_id=TARMICA, message_id=message_id, ai=rogue)
                                logging.info("===================================== : AUDIO RESPONSE HANDLER CALLED AND RUN SUCCESSFULLY")
                            elif is_audio_sensible_english == False:
                                logging.info("=====================================: Language check returned false")
                                messenger.reply_to_message(message_id=message_id, message="Sorry Tarmica, I didnt quite get that, may you please be clearer?", recipient_id=TARMICA)
                            else:
                                logging.info(f"=====================================: Language check returned an error {is_audio_sensible_english}")
                                messenger.reply_to_message(message_id=message_id, message=f"In trying to determine if your english is correct or not, an error occured:{is_audio_sensible_english}", recipient_id=TARMICA)
                        
                        elif recipient in beta:
                            ghost = Chipoko(recipient=recipient, name=name)
                            if is_audio_sensible_english == True:
                                messenger.mark_as_read(message_id=message_id)
                                reply = ghost.create_message_and_get_response(message=transcript)
                                audio_response_handler(response=reply, recipient_id=recipient, message_id=message_id, ai=ghost)
                                logging.info("===================================== : AUDIO RESPONSE HANDLER CALLED AND RUN SUCCESSFULLY")
                            elif is_audio_sensible_english == False:
                                logging.info("=====================================: Language check returned false")
                                messenger.reply_to_message(message_id=message_id, message="I didnt quite get that, may you please be clearer?", recipient_id=recipient)
                            else:
                                logging.info(f"=====================================: Language check returned an error {is_audio_sensible_english}")
                                messenger.reply_to_message(message_id=message_id, message=f"In trying to determine if your english is correct or not, an error occured:{is_audio_sensible_english}", recipient_id=recipient)
                        
                        else:
                            thread_id = get_thread_id(recipient=recipient)
                            if thread_id == "no thread found":
                                logging.error(f"===============================ERROR: THREAD DATABASE OPERATION GONE WRONG")
                                messenger.reply_to_message(message_id=message_id, message="Sorry, an error occured. Couldnt find a thread for you.\n\nPlease show this message to Tarmica (https://wa.me/263779281345)", recipient_id=recipient)
                                return "OK", 200
                            kim = Agent(thread_id=thread_id)
                            if is_audio_sensible_english == True:
                                messenger.mark_as_read(message_id=message_id)
                                reply = kim.create_message_and_get_response(content=transcript)
                                audio_response_handler(response=reply, recipient_id=recipient, message_id=message_id, ai=kim)
                            elif is_audio_sensible_english == False:
                                logging.info("=====================================: Language check returned false")
                                messenger.reply_to_message(message_id=message_id, message="I didnt quite get that, may you please be clearer?", recipient_id=recipient)
                            else:
                                logging.info(f"=====================================: Language check returned an error {is_audio_sensible_english}")
                                messenger.reply_to_message(message_id=message_id, message=f"In trying to determine if your english is correct or not, an error occured:{is_audio_sensible_english}", recipient_id=recipient) 
                    except Exception as e:
                        messenger.reply_to_message(message_id=message_id, message=f"error occured {e.with_traceback()}", recipient_id=recipient)           
                ############################# End Audio Message Handling ################################################################################
                ############################# Image Message Handling ####################################################################################
                elif message_type == "image":
                    image = messenger.get_image(data=data)
                    image_url = messenger.query_media_url(image["id"])
                    logging.info("IMAGE URL: =====================================================================  %s", image_url)
                    caption = messenger.extract_caption(data=data)
                    logging.info("CAPTION: =====================================================================  %s", caption)
                    messenger.mark_as_read(message_id=message_id)
                    history.add_user_message(caption)
                    if recipient == TARMICA:
                        # base64_image = encode_image(image_uri)
                        prompt = f"image_url: {image_url}\n\nCaption:{caption}\n\nPS: even if the url links to an image that seems to be hosted on a private server, use the analyze_images_with_captions tool as it has access to it."
                        response = rogue.create_message_and_get_response(content=prompt)
                        logging.info("RAW RESPONSE ================================================= %s", response)
                        response_handler(response=response, recipient_id=TARMICA, message_id=message_id)
                    else:
                        thread_id = get_thread_id(recipient=recipient)
                        if thread_id == "no thread found":
                            logging.error(f"===============================ERROR: DATABASE OPERATION GONE WRONG LINE 94 in app.py")
                            return "OK", 200
                        kim = Agent(thread_id=thread_id)
                        prompt = f"image_url: {image_url}\n\nCaption:{caption}\n\nDont worry about the link being a private server link, the image analysis tools has access to it."
                        response = kim.create_message_and_get_response(content=prompt)
                        logging.info("RAW RESPONSE ================================================= %s", response)
                        response_handler(response=response, recipient_id=recipient, message_id=message_id)
                ############################# End Image Message Handling ###################################################################################
                ############################# Document Message Handling ####################################################################################         
                elif message_type == "document":
                    messenger.mark_as_read(message_id=message_id)
                    messenger.send_message(message="I don't know how to handle documents yet, but coming soon", recipient_id=recipient)
                ############################# End Document Message Handling ################################################################################
            else:
                delivery = messenger.get_delivery(data)
                if delivery:
                    logging.info(f"Message : {delivery}")
                else:
                    logging.info("No new message")
        else:
            logging.info("===========================================================================: No new message")
    return "OK", 200

