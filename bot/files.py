import time
import requests
import tempfile
import logging
import convertapi
import config
from requests.auth import HTTPBasicAuth
from telegram import ParseMode
from telegram.ext import ConversationHandler
from telegram.utils import helpers
from general import print_sender_info, print_sender_choice_and_info,FILES_TYPING_CHOICE, FILES_TYPING_REPLY

convertapi.api_secret = config.CONVERTAPI_SECRET
_zamzar_api_key = config.ZAMZAR_API_KEY
_zamzar_base_url = {"zamzar-sb": "https://api.zamzar.com/v1", "zamzar-live": "https://sandbox.zamzar.com/v1"}
_preferred_converter = {"pdf-to-docx": "zamzar-live", "pdf-to-csv": "zamzar-live"}

def check_api_credits():
    user_info = convertapi.user()
    logging.info(f"CONVERTAPI SecondsLeft:{user_info['SecondsLeft']}")
    if user_info['SecondsLeft'] < 5:
        resp_sb = requests.get(f"{_zamzar_base_url['zamzar-live']}/account", auth=HTTPBasicAuth(_zamzar_api_key, ''))
        logging.info(f"ZAMZAR Test Credits:{resp_sb.json()['test_credits_remaining']}")
        logging.info(f"ZAMZAR Live Credits:{resp_sb.json()['credits_remaining']}")
        if resp_sb.json()["credits_remaining"] > 1:
            return "zamzar-live"
        elif resp_sb.json()["test_credits_remaining"] > 1:
            return "zamzar-sb"
        else:
            return None
    else:
        return "convertapi"

def decide_api(converter_chosen):
    api_chosen = check_api_credits()
    if api_chosen:
        if converter_chosen in _preferred_converter:
            if api_chosen.startswith("zamzar"):
                return api_chosen
            return _preferred_converter[converter_chosen]
        else:
            return api_chosen
    else:
        return "credits-over"
    
def chosen_file_converter(update, context):
    query = update.callback_query
    context.user_data['choice'] = query.data
    query.answer()
    if query.data == "docx-to-pdf":
        reply_text = "Okie dokie. Send me the word file (.doc/.docx) to convert it to PDF.\n"
    elif query.data == "odt-to-pdf":
        reply_text = "No problem. Send me an ODT file (.odt) to convert it to PDF.\n"
    elif query.data == "pdf-to-txt":
        reply_text = "Sure thing. Send me the PDF file (.pdf) to convert it to a text file.\n"
    elif query.data == "pdf-to-docx":
        reply_text = "You got it. Just send me the PDF file (.pdf) to convert it to a word file (.docx).\n"
    elif query.data == "pdf-to-csv":
        reply_text = "Ok then. Send me the PDF file (.pdf) to extract tables and save them as comma-separated values in CSV files.\n"
    elif query.data == "pdf-to-jpg":
        reply_text = "Sure. Send me the PDF file (.pdf) to convert it to a JPG file.\n"
    else:
        return ConversationHandler.END
    query.edit_message_text(text=reply_text, parse_mode="Markdown")
    return FILES_TYPING_REPLY

def convert_using_convertapi(context, update, source_fmt, target_fmt):
    bot = context.bot
    source_file = bot.getFile(update.message.document.file_id)
    target_files = convertapi.convert(target_fmt, { 'File': source_file.file_path }).save_files(tempfile.gettempdir())
    return target_files

def get_zamzar_file_conversion_status(base_url, file_conv_id):
    msg = None
    target_files = list()
    job_endpoint = f"{base_url}/jobs"
    res = requests.get(f"{job_endpoint}/{file_conv_id}", auth=HTTPBasicAuth(_zamzar_api_key, ''))
    if "status" in res.json() and res.json()["status"] == "failed":
        msg = res.json()["failure"]["message"]
        if res.json()["failure"]["code"] == 3:
            msg += res.json()["import"]["failure"]["message"]
    else:
        if res.json()["status"] == "successful":
            for file_info in res.json()["target_files"]:
                tgt_file_id = file_info["id"]
                tgt_file_name = file_info["name"]
                file_content_endpoint = f"{base_url}/files/{tgt_file_id}/content"
                res = requests.get(file_content_endpoint, stream=True, auth=HTTPBasicAuth(_zamzar_api_key, ''))
                local_filename = f"{tempfile.gettempdir()}/{tgt_file_name}"
                try:
                    with open(local_filename, 'wb') as f:
                        for chunk in res.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                                f.flush()
                except IOError as e:
                    logging.error(f"Failed to perform IO Operation: {e}")
                target_files.append(local_filename)
        else:
            time.sleep(2)
            target_files, msg = get_zamzar_file_conversion_status(base_url, file_conv_id)
    return target_files, msg

def convert_using_zamzar(context, update, base_url, source_fmt, target_fmt):
    bot = context.bot
    job_endpoint = f"{base_url}/jobs"
    source_file = bot.getFile(update.message.document.file_id)
    data_content = {'source_file': source_file.file_path, 'target_format': target_fmt}
    res = requests.post(job_endpoint, data=data_content, auth=HTTPBasicAuth(_zamzar_api_key, ''))
    file_conv_id = res.json()["id"]
    target_files, msg = get_zamzar_file_conversion_status(base_url, file_conv_id)
    return target_files, msg

def invoke_files(update, context):
    bot = context.bot
    chat_id = update.message.chat.id
    user_data = context.user_data
    converter_chosen = user_data['choice']
    print_sender_choice_and_info(update, converter_chosen)
    user_data[converter_chosen] = update.message.text
    source_fmt, target_fmt = converter_chosen.split("-to-")
    api_to_use = decide_api(converter_chosen)
    if api_to_use == "convertapi":
        target_files = convert_using_convertapi(context, update, source_fmt, target_fmt)
        for idx,filepath in enumerate(target_files):
            bot.send_document(chat_id = chat_id, document=open(filepath, 'rb'), filename = update.message.document.file_name.rsplit('.', 1)[0] + f"_{idx}" + f".{target_fmt}", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    elif api_to_use.startswith("zamzar"):
        base_url = _zamzar_base_url[api_to_use]
        target_files, msg = convert_using_zamzar(context, update, base_url, source_fmt, target_fmt)
        if msg and not target_files:
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        elif target_files and not msg:
            for idx,filepath in enumerate(target_files):
                bot.send_document(chat_id = chat_id, document=open(filepath, 'rb'), filename = update.message.document.file_name.rsplit('.', 1)[0] + f"_{idx}" + f".{target_fmt}", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    else:
        update.message.reply_text(f"Sorry, we are running low on resources to process the file conversion. Please try again later.", parse_mode="Markdown")
        return ConversationHandler.END