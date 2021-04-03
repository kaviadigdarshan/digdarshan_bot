import os
import re
import sys
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler

from quotes import cmd_quote
from error_handler import error_handler
from transliterate import invoke_transliterate
from files import chosen_file_converter, invoke_files
from dictionary import chosen_dict, invoke_dictionary, invoke_syn_ant_callback, show_next_prev_definition
from general import print_sender_info, DEV_CHAT_ID, DICT_TYPING_REPLY, DICT_TYPING_CHOICE, DICT_SELECTING_DEF, TRANS_TYPING_REPLY, FILES_TYPING_CHOICE, FILES_TYPING_REPLY, COMMANDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

mode = os.getenv("MODE").lower()
if mode == "dev":
    def run(updater):
        updater.start_polling()
        updater.idle()
elif mode == "prod":
    def run(updater):
        PORT = int(os.environ.get("PORT", "8443"))
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=os.getenv("TG_BOT_TOKEN"),
                              webhook_url = f"https://{os.getenv('HEROKU_APP_NAME')}.herokuapp.com/{os.getenv('TG_BOT_TOKEN')}")
else:
    logging.error("No MODE Specified. Please specify mode as one of ['dev', 'prod']")
    sys.exit(1)

def cancel(bot, update):
	update.message.reply_text('')
	return ConversationHandler.END

def cmd_start(update, context):
    print_sender_info(update)
    deeplink_call = re.findall(r"(?:/start )(.+)", update.message.text)
    if len(deeplink_call) > 0:
        for call in deeplink_call:
            if call.startswith('SYNANT') or call.startswith("MEDIC_DICT_CALLBACK"):
                invoke_syn_ant_callback(update, context)
    else:
        command_intro = "\n".join([f"{cmd}: {func}" for cmd, func in COMMANDS.items()])
        reply_text = "Hi 👋🏻, My name is *Digdarshan* 👨🏻‍💻 \nI am here to help you with your queries.\n"
        reply_text += "You can use below commands:\n\n"
        reply_text += command_intro
        context.bot.send_message(chat_id=update.effective_chat.id, text=reply_text, parse_mode="Markdown")

def cmd_transliterate(update, context):
    print_sender_info(update)
    reply_text = "Send me your text written in English which you want to transliterate to Hindi.\n\n"
    reply_text += "*Example* - _aap kaise hain_"
    update.message.reply_text(reply_text, parse_mode="Markdown")
    return TRANS_TYPING_REPLY

def cmd_dictionary(update, context):
    print_sender_info(update)
    keyboard = [
        [InlineKeyboardButton("English to English", callback_data='eng-to-eng-dict'),
         InlineKeyboardButton("Hindi to Hindi", callback_data='hi-to-hi-dict')],
        [InlineKeyboardButton("Medical Dictionary", callback_data='medical-dict')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return DICT_TYPING_CHOICE

def cmd_files(update, context):
    print_sender_info(update)
    keyboard = [
        [InlineKeyboardButton("Word to PDF", callback_data='docx-to-pdf'),
         InlineKeyboardButton("ODT to PDF", callback_data='odt-to-pdf')],
        [InlineKeyboardButton("PDF to Text", callback_data='pdf-to-txt'),
         InlineKeyboardButton("PDF to Word", callback_data='pdf-to-docx')],
        [InlineKeyboardButton("PDF to CSV", callback_data='pdf-to-csv'),
         InlineKeyboardButton("PDF to JPG", callback_data='pdf-to-jpg')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return FILES_TYPING_CHOICE

handler_list = [CommandHandler(cmd.strip('/'), globals()["cmd_" + cmd.strip('/')]) for cmd in COMMANDS]
handler_list.append(CommandHandler('cancel', cancel))

start_handler = CommandHandler('start', cmd_start, pass_args=True)
quote_handler = CommandHandler('quote', cmd_quote)
transliterate_handler = ConversationHandler(
    entry_points = [CommandHandler('transliterate', cmd_transliterate)],
    states = {
        TRANS_TYPING_REPLY: [
                MessageHandler(
                    Filters.text & ~(Filters.command),
                    invoke_transliterate,
                )
            ],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    allow_reentry=True
)
dictionary_handler = ConversationHandler(
    entry_points = [CommandHandler('dictionary', cmd_dictionary)],
    states = {
        DICT_TYPING_CHOICE: [
                CallbackQueryHandler(chosen_dict)
            ],
        DICT_TYPING_REPLY: [
                MessageHandler(
                    Filters.text & ~(Filters.command),
                    invoke_dictionary,
                )
            ],
        DICT_SELECTING_DEF: [
                CallbackQueryHandler(show_next_prev_definition, pattern='^show_prev_def|show_next_def$')
            ],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    allow_reentry=True
)
files_handler = ConversationHandler(
    entry_points = [CommandHandler('files', cmd_files)],
    states = {
        FILES_TYPING_CHOICE: [
                CallbackQueryHandler(chosen_file_converter)
            ],
        FILES_TYPING_REPLY: [
                MessageHandler(
                    Filters.document & ~(Filters.command | Filters.text),
                    invoke_files,
                )
            ],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    allow_reentry=True
)

if __name__ == '__main__':
    updater = Updater(os.getenv("TG_BOT_TOKEN"))
    dispatcher = updater.dispatcher

    dispatcher.add_handler(quote_handler)
    dispatcher.add_handler(dictionary_handler)
    dispatcher.add_handler(transliterate_handler)
    dispatcher.add_handler(files_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_error_handler(error_handler)

    run(updater)