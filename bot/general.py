import os
import logging

DEV_CHAT_ID  = os.getenv("DEVELOPER_CHAT_ID")
PUNCTUATION_LITERALS  = ['?', '!', '&', '>', '|', '\\', '$', '+', '@', '-', '`', '/', ':', '_', '%', ';', '{', ')', '^', '.', '[', '"', '}', '~', ']', '<', '#', '(', '=', '*', ',', "'"]
NUMBER_EMOJI_MAP = {"0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣","5": "5️⃣", "6": "6️⃣","7": "7️⃣","8": "8️⃣","9": "9️⃣"}
DICT_TYPING_REPLY, DICT_TYPING_CHOICE, DICT_SELECTING_DEF = range(3)
TRANS_TYPING_REPLY = range(3, 4)
FILES_TYPING_CHOICE, FILES_TYPING_REPLY = range(4, 6)
COMMANDS = {
    '/start': 'Start the conversation with the bot',
    '/quote': 'Get a random quote rendered in form of beautiful image',
    '/files': 'Convert files from one format to another',
    '/dictionary': 'Get benefit of using all dictionaries from a single place',
    '/transliterate': 'Write a Hindi meesage to bot using English literals and get its Hindi transliteration'
}
MEDIC_DICT_TAGS = {"{b}": "*", "{\/b}": "*", "{bc}": "*:* ", "{inf}": "", "{\/inf}": "", "{it}": "_", "{\/it}": "_", "{\/it}": "_", "{ldquo}": "'", "{rdquo}": "'", "{sc}": "", "{\/sc}": "", "{sup}": "", "{\/sup}": "", }


def print_sender_info(update, sender_text=None):
    sender_user = update.message.chat.username
    sender_name = update.message.chat.first_name + " " + update.message.chat.last_name if update.message.chat.last_name else update.message.chat.first_name
    if not sender_text:
        sender_text = update.message.text
    logging.info(f"{sender_user} [{sender_name}] sent: {sender_text}")

def print_sender_choice_and_info(update, choice, sender_text=None):
    sender_user = update.message.chat.username
    sender_name = update.message.chat.first_name + " " + update.message.chat.last_name if update.message.chat.last_name else update.message.chat.first_name
    if not sender_text:
        sender_text = update.message.text
    logging.info(f"{sender_user} [{sender_name}] chose: {choice}")
    logging.info(f"{sender_user} [{sender_name}] sent: {sender_text}")