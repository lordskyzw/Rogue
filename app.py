import os
import uvicorn
import openai
from utilities.tools import recipients_database, check_id_database, add_id_to_database, save_thread_id, get_thread_id
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

app = FastAPI()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logging.info("Started FastAPI server")


@app.get("/")
async def welcome():
    return {"message": "Welcome to my FastAPI application!"}

@app.get("/rogue")
async def verify_token(request: Request):
    # Access query parameters
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    if hub_verify_token == VERIFY_TOKEN:
        logging.info("Verified webhook")
        # Create a plain text response
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
                
                ## genuinely didnt  know i had this
                elif message_type == "audio":
                    audio = messenger.get_audio(data=data)
                    audio_id, mime_type = audio["id"], audio["mime_type"]
                    messenger.mark_as_read_by_winter(message_id=message_id)
                    audio_url = messenger.query_media_url(audio_id)
                    audio_uri = messenger.download_media(
                        media_url=audio_url, mime_type="audio/ogg"
                    )
                    audio_file = open(audio_uri, "rb")
                    try:
                        transcript = openai.audio.transcriptions.create(
                        model="whisper-1", 
                        response_format="text",
                        file=audio_file
                        )
                        logging.info(f"====================================================== TRANSCRIPT: {transcript}")
                        if recipient == TARMICA:
                            reply = rogue.create_message_and_get_response(content=transcript)
                            logging.info(f"====================================================== REPLY: {reply}")
                            # need to create an audio of the reply
                            audio = rogue.create_audio(response=reply)
                            logging.info("============================================================= AUDIO: %s", audio)
                            audio_id_dict = messenger.upload_media(media=(os.path.realpath(audio)))
                            logging.info("============================================================= ID_DICT: %s", audio_id_dict)
                            messenger.send_audio(audio=audio_id_dict["id"], recipient_id=TARMICA, link=False)
                        else:
                            kim = Kim(thread_id=thread_id)
                            reply = kim.create_message_and_get_response(content=transcript)
                            audio = kim.create_audio(response=reply)
                            audio_id_dict = messenger.upload_media(media=(os.path.realpath(audio)))
                            messenger.send_audio(audio=audio_id_dict["id"], recipient_id=recipient, link=False)
                    except Exception as e:
                        messenger.reply_to_message(message_id=message_id, message=f"error occured {e.with_traceback()}", recipient_id=recipient)
                    
                        
                ############################# End Audio Message Handling ######################################

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

