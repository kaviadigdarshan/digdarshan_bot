import os
import re
import requests
import detectlanguage
from transliterate import get_hindi_literals
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from telegram.utils import helpers
from general import print_sender_info, print_sender_choice_and_info, NUMBER_EMOJI_MAP, DICT_TYPING_REPLY, DICT_TYPING_CHOICE, DICT_SELECTING_DEF, PUNCTUATION_LITERALS, MEDIC_DICT_TAGS

MEDICAL_DICT_KEY = os.getenv("MEDICAL_DICT_API_KEY")

def detect_hindi_in_msg(word):
    resp = detectlanguage.detect(word)
    detected_languages = [d['language'] for d in resp if d['isReliable']]
    if 'hi' in detected_languages:
        return True
    return False

def process_stems(bot, word_str, meaning_str, meta_dict):
    if 'stems' in meta_dict:
        stems_list = [stem for stem in meta_dict['stems'] if stem != word_str]
        if stems_list:
            meaning_str += "Variants and Inflections: "
            for idx, stem in enumerate(stems_list):
                if "'" in stem or '"' in stem:
                    continue
                url = helpers.create_deep_linked_url(bot.username, "MEDIC_DICT_CALLBACK" + stem.replace(" ", "_"))
                stem_url = f"[{stem}]({url})"
                if idx == len(stems_list) - 1:
                    meaning_str += stem_url
                else:
                    meaning_str += stem_url + ", "
            meaning_str += f"\n\n"
    return meaning_str

def prepare_meaning_str(context, resp):
    bot = context.bot
    definition_list = list()
    meaning_str = ""
    for entry in resp:
        meaning_list = entry["meanings"]
        word_intro = f"📖 Word: *{entry['word']}*\n"
        meaning_str += word_intro
        meaning_str += "-"*2*len(word_intro)
        meaning_str += f"\n\n"
        counter = 1
        for meaning_dict in meaning_list:
            for definition_dict in meaning_dict["definitions"]:
                definition_str = ''
                definition_str += meaning_str
                definition_str += f"📢 *Part of Speech*: _{meaning_dict['partOfSpeech']}_\n\n"
                num_emoji_str = NUMBER_EMOJI_MAP[str(counter)] if counter < 10 else NUMBER_EMOJI_MAP[str(counter)[0]] + NUMBER_EMOJI_MAP[str(counter)[1]]
                definition_str += f"{num_emoji_str}\n\n📜*Definition*: _{definition_dict['definition']}_\n\n"
                if "synonyms" in definition_dict:
                    if len(definition_dict["synonyms"]) > 0:
                        definition_str += f"🔄 *Synonyms*: "
                        for idx, synonym in enumerate(definition_dict["synonyms"]):
                            if "'" in synonym or '"' in synonym:
                                continue
                            url = helpers.create_deep_linked_url(bot.username, "SYNANT" + synonym.replace(" ", "_"))
                            synonym_url = f"[{synonym}]({url})"
                            if idx == len(definition_dict["synonyms"]) - 1:
                                definition_str += synonym_url
                            else:
                                definition_str += synonym_url + ", "
                        definition_str += "\n\n"
                if "antonyms" in definition_dict:
                    if len(definition_dict["antonyms"]) > 0:
                        definition_str += f"↔ *Antonyms*: "
                        for idx, antonym in enumerate(definition_dict["antonyms"]):
                            if "'" in antonym or '"' in antonym:
                                continue
                            url = helpers.create_deep_linked_url(bot.username, "SYNANT" + antonym.replace(" ", "_"))
                            antonym_url = f"[{antonym}]({url})"
                            if idx == len(definition_dict["antonyms"]) - 1:
                                definition_str += antonym_url
                            else:
                                definition_str += antonym_url + ", "
                        definition_str += "\n\n"
                if "example" in definition_dict:
                    if len(definition_dict["example"]) > 0:
                        definition_str += f"💬 *Example* : _{definition_dict['example']}_\n"
                counter += 1
                definition_str += "\n"
                definition_list.append(definition_str)
    return definition_list

def prepare_medical_meaning_str(context, resp):
    bot = context.bot
    definition_list = list()
    for entry in resp:
        meaning_str = ""
        word_str = entry['meta']['id'].split(":")[0]
        word_intro = f"📖 Word: *{word_str}*\n"
        meaning_str += word_intro
        meaning_str += "-"*2*len(word_intro)
        meaning_str += f"\n\n"
        meaning_str = process_stems(bot, word_str, meaning_str, entry["meta"])
        meaning_str += f"📢 *Part of Speech*: _{entry['fl']}_\n\n"
        meaning_str += "📜*Definitions*:\n"
        counter = 1
        for meaning in entry["shortdef"]:
            meaning_str += f"{NUMBER_EMOJI_MAP[str(counter)]} _{meaning}_\n\n"
            counter += 1
        counter = 1
        if "quotes" in entry and entry["quotes"]:
            meaning_str += "✒*Quotations from Cited Sources*:\n"
            for quote_dict in entry["quotes"]:
                quote = quote_dict["t"]
                author = quote_dict["aq"]["auth"]
                source = quote_dict["aq"]["source"]
                aqdate = quote_dict["aq"]["aqdate"]
                for tag, sub in MEDIC_DICT_TAGS.items():
                    quote.replace(tag, sub)
                    source.replace(tag, sub)
                deep_link_words = re.findall(r"{a_link\|(\w+)}", quote)
                for word in deep_link_words:
                    word_url = helpers.create_deep_linked_url(bot.username, "MEDIC_DICT_CALLBACK" + word.replace(" ", "_"))
                    quote.replace("{" + f"a_link|{word}" + "}", word_url)
                meaning_str += f"{NUMBER_EMOJI_MAP[str(counter)]} {quote}\n-- {author}, {source}, {aqdate}\n\n"
        definition_list.append(meaning_str)
    return definition_list

def get_meaning_from_eng_dict(context, text):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en_US/{text}"
    resp = requests.get(url).json()
    if isinstance(resp, dict) and resp['title'] == "No Definitions Found":
        return f"Sorry, could not find any meaning for the word _{text}_"
    elif isinstance(resp, list) and not resp[0]['meanings']:
        return f"Sorry, could not find any meaning for the word _{text}_"
    else:
        definition_list = prepare_meaning_str(context, resp)
        return definition_list

def get_meaning_from_hi_dict(context, text):
    if not detect_hindi_in_msg(text):
        text = get_hindi_literals([text + "\n"])
    url = f"https://api.dictionaryapi.dev/api/v2/entries/hi/{text}"
    resp = requests.get(url)
    resp = resp.json()
    if isinstance(resp, dict) and resp["title"] == "No Definitions Found":
        return f"Sorry, could not find any meaning for the word _{text}_."
    else:
        definition_list = prepare_meaning_str(context, resp)
        return definition_list

def get_meaning_from_medical_dict(context, text):
    url = f"https://dictionaryapi.com/api/v3/references/medical/json/{text}?key={MEDICAL_DICT_KEY}"
    resp = requests.get(url)
    resp = resp.json()
    if resp:
        if isinstance(resp, list):
            if all([True if isinstance(word, str) else False for word in resp]):
                reply_text = f"Sorry, could not find any meaning for the word _{text}_.\n\n"
                reply_text += "However, here are some vaguely similar words if they help: "
                for idx, word in enumerate(resp):
                    if "'" in word or '"' in word:
                        continue
                    url = helpers.create_deep_linked_url(context.bot.username, "MEDIC_DICT_CALLBACK" + word.replace(" ", "_"))
                    word_url = f"[{word}]({url})"
                    if idx == len(resp) - 1:
                        reply_text += word_url
                    else:
                        reply_text += word_url + ", "
                return reply_text
            else:
                definition_list = prepare_medical_meaning_str(context, resp)
                return definition_list
    else:
        return f"Sorry, could not find any meaning for the word _{text}_."

def get_meaning(context, dict_chosen, user_data):
    word = user_data[dict_chosen]
    if dict_chosen == "eng-to-eng-dict":
        definition_list = get_meaning_from_eng_dict(context, word)
    elif dict_chosen == "hi-to-hi-dict":
        definition_list = get_meaning_from_hi_dict(context, word)
    elif dict_chosen == "medical-dict":
        definition_list = get_meaning_from_medical_dict(context, word)
    return definition_list

def chosen_dict(update, context):
    query = update.callback_query
    context.user_data['choice'] = query.data
    query.answer()
    if query.data == "eng-to-eng-dict":
        reply_text = "Please enter any English word to see its meaning.\n\n"
        reply_text += "*Example*: _resource_ OR _phonetics_"
    elif query.data == "hi-to-hi-dict":
        reply_text = "Please enter any Hindi word or English representation of Hindi word to see its meaning in Hindi.\n\n"
        reply_text += "*Example*: _naam_ OR _नाम_"
    elif query.data == "medical-dict":
        reply_text = "Please enter any medical term to see its definition.\n\n"
        reply_text += "*Example*: _disease_ OR _photalgia_"
    else:
        return ConversationHandler.END
    query.edit_message_text(text=reply_text, parse_mode="Markdown")
    return DICT_TYPING_REPLY

def get_keyboard_markup(def_num, def_list_len):
    if def_num == 0:
        buttons = [
            [
                InlineKeyboardButton(text='Next ⏩', callback_data='show_next_def')
            ]
        ]
    elif def_num == def_list_len - 1:
        buttons = [
            [
                InlineKeyboardButton(text='⏪ Previous', callback_data='show_prev_def')
            ]
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text='⏪ Previous', callback_data='show_prev_def'),
                InlineKeyboardButton(text='Next ⏩', callback_data='show_next_def')
            ]
        ]
    keyboard = InlineKeyboardMarkup(buttons)
    return keyboard

def show_next_prev_definition(update, context):
    query = update.callback_query
    context.user_data['whichdef'] = query.data
    query.answer()
    user_data = context.user_data
    definition_list = user_data['definition_list']
    current_def = user_data['current_def']
    if query.data == "show_prev_def":
        if current_def != 0:
            current_def -= 1
            user_data['current_def'] = current_def
        show_meaning = definition_list[current_def]
    elif query.data == "show_next_def":
        if current_def != len(definition_list) - 1:
            current_def += 1
            user_data['current_def'] = current_def
        show_meaning = definition_list[current_def]
    else:
        return ConversationHandler.END
    keyboard = get_keyboard_markup(user_data['current_def'], len(definition_list))
    query.edit_message_text(text=show_meaning, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=keyboard)
    return DICT_SELECTING_DEF

def invoke_dictionary(update, context):
    chat_id = update.message.chat.id
    bot = context.bot
    user_data = context.user_data
    dict_chosen = user_data['choice']
    print_sender_choice_and_info(update, dict_chosen)
    user_data[dict_chosen] = update.message.text
    definition_list = get_meaning(context, dict_chosen, user_data)
    if isinstance(definition_list, list):
        user_data['definition_list'] = definition_list
        user_data['current_def'] = 0
        show_meaning = definition_list[0]
        definition_list_len = len(definition_list)
    else:
        show_meaning = definition_list
        update.message.reply_text(show_meaning, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return ConversationHandler.END
    if definition_list_len > 1:
        keyboard = get_keyboard_markup(user_data['current_def'], definition_list_len)
        update.message.reply_text(show_meaning, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=keyboard)
        return DICT_SELECTING_DEF
    else:
        update.message.reply_text(show_meaning, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return ConversationHandler.END

def invoke_syn_ant_callback(update, context):
    word = context.args[0].split("SYNANT")[1].replace("_", " ") if "SYNANT" in context.args[0] else context.args[0].split("MEDIC_DICT_CALLBACK")[1].replace("_", " ")
    print_sender_info(update, word)
    user_data = context.user_data
    dict_chosen = user_data['choice']
    user_data[dict_chosen] = word
    definition_list = get_meaning(context, dict_chosen, user_data)
    if isinstance(definition_list, list):
        user_data['definition_list'] = definition_list
        user_data['current_def'] = 0
        show_meaning = definition_list[0]
        definition_list_len = len(definition_list)
    else:
        show_meaning = definition_list
        update.message.reply_text(show_meaning, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return ConversationHandler.END
    if definition_list_len > 1:
        keyboard = get_keyboard_markup(user_data['current_def'], len(definition_list))
        update.message.reply_text(show_meaning, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=keyboard)
        return DICT_SELECTING_DEF
    else:
        update.message.reply_text(show_meaning, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return ConversationHandler.END