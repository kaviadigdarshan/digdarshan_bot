import os
import string
from random import randrange
from cloudinary import config as cloudinary_config
from cloudinary import Search

cloudinary_config(
  cloud_name = os.getenv("CLOUDINARY_USER"),  
  api_key = os.getenv("CLOUDINARY_API_KEY"),  
  api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

def get_quote_image():
    result = Search()\
            .expression('folder:quotes')\
            .execute()
    img_url = result["resources"][randrange(len(result["resources"]))]["url"]
    return img_url


def cmd_quote(update, context):
    img_url = get_quote_image()
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_url, parse_mode="Markdown")