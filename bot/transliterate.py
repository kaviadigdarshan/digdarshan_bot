import os
import re
import ast
import http.client
import detectlanguage
from telegram.ext import ConversationHandler
from general import print_sender_info, TRANS_TYPING_REPLY, PUNCTUATION_LITERALS
 
detectlanguage.configuration.api_key = os.getenv("DETECTLANGUAGE_API_KEY")
detectlanguage.configuration.secure = True

lang = 'hi-t-i0-und'
TRANS_CHOOSING, TRANS_TYPING_REPLY, TRANS_TYPING_CHOICE = range(3, 6)

def perform_transliteration(en_literal):
    conn = http.client.HTTPSConnection('inputtools.google.com')
    conn.request('GET', '/request?text=' + en_literal + '&itc=' + lang + '&num=1&cp=0&cs=1&ie=utf-8&oe=utf-8&app=test')
    resp = conn.getresponse()
    output = ast.literal_eval(resp.read().decode("utf-8"))[1][0][1][0]
    return output.strip()

def get_hindi_literals(en_text):
    hi_literals = ''
    for i in range(len(en_text)):
        lit = ''
        words = en_text[i][:-1].split(' ')
        for word in words:
            word_punc_split = re.findall(r"\w+|[^\w\s]", word, re.UNICODE)
            for word_part in word_punc_split:
                if isinstance(word_part, int):
                    lit = word_part
                elif word_part in PUNCTUATION_LITERALS:
                    if word_part == ".":
                        lit = "|"
                    else:
                        lit = word_part
                else:
                    lit = perform_transliteration(word_part)
                if word_part in PUNCTUATION_LITERALS:
                    hi_literals = hi_literals[:-1]
                hi_literals += lit + " "
        return hi_literals

def detect_hindi_in_msg(text):
    resp = detectlanguage.detect(text)
    detected_languages = [d['language'] for d in resp if d['isReliable']]
    if 'hi' in detected_languages:
        return True
    return False

def invoke_transliterate(update, context):
    print_sender_info(update)
    user_data = context.user_data
    msg_text = update.message.text
    if detect_hindi_in_msg(msg_text):
        reply_text = "Now, why would you want to transliterate hindi to hindi?\n"
        reply_text += "Please send me your text written in English which you want to convert to Hindi.\n\n"
        reply_text += "*Example* - _aapke kya haal chaal hain_"
        update.message.reply_text(reply_text, parse_mode="Markdown")
        return TRANS_TYPING_REPLY
    else:
        reply_text = get_hindi_literals([msg_text + "\n"])
        update.message.reply_text(reply_text, parse_mode="Markdown")
        user_data.clear()
        return ConversationHandler.END