import os,logging,re
from telethon import TelegramClient, events
from telethon.tl.custom.button import Button
from dotenv import load_dotenv
from strings import strings,direct_reply
from pymongo import MongoClient

load_dotenv(override=True)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URL = os.getenv('MONGODB_URL')
SUPER_ADMINS = [int(i) for i in os.getenv('SUPER_ADMINS', '0').split(',')]
database = MongoClient(MONGODB_URL).post_bot
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

 
'''
==  Non processed handling  ==
this section contain the direct responses and access checking part
see strings.py for default string values
'''
@bot.on(events.NewMessage(func=lambda e:e.is_private))
async def handler(event):
    if event.chat_id not in SUPER_ADMINS and database.admins.find_one({'chat_id': event.chat_id}) is None:
        await event.respond(strings['no_access'])
    elif event.message.text in direct_reply.keys():
        await event.respond(direct_reply[event.message.text])
    else:
        return
    raise events.StopPropagation

'''
==  Processed handling  ==
'''
# === COMMAND HANDLING (SUPER ADMINS ONLY) ===
@bot.on(events.NewMessage(func=lambda e:e.is_private))
async def handler(event):
    if event.chat_id not in SUPER_ADMINS and database.admins.find_one({'chat_id': event.chat_id}) is None:
        await event.respond(strings['no_access'])
        return
    command = event.message.text.split(' ')
    if command[0]=='/add_admin':
        if database.admins.find_one({'chat_id': int(command[1])}) is not None:
            await event.respond(strings['admin_exists'])
        elif len(command)==3:
            database.admins.insert_one({'chat_id': int(command[1]),'nick': command[2]})
            await event.respond(strings['new_admin_added'])
        else:
            await event.respond(strings['invalid_syntax'])
    
    elif command[0]=='/remove_admin':
        if database.admins.find_one({'chat_id': int(command[1])}) is not None:
            database.admins.delete_one({'chat_id': int(command[1])})
            await event.respond(strings['admin_removed'])
        else:
            await event.respond(strings['admin_404'])
    
    elif command[0]=='/admins':
        admin_list = [f"{a['nick']}: `{a['chat_id']}`" for a in database.admins.find()]
        await event.respond(strings['admin_list_title']+"\n".join(admin_list))
    
    elif command[0]=='/add_chat':
        if database.my_chats.find_one({'chat_id': command[1]}) is not None:
            await event.respond(strings['chat_already_added'])
        elif len(command)==3:
            database.my_chats.insert_one({'chat_id': int(command[1]),'nick': command[2]})
            await event.respond(strings['new_chat_added'])
        else:
            await event.respond(strings['invalid_syntax'])

    elif command[0]=='/remove_chat':
        if database.my_chats.find_one({'chat_id': int(command[1])}) is not None:
            database.my_chats.delete_one({'chat_id': int(command[1])})
            database.chat_posts.delete_many({'chat_id': int(command[1])})
            await event.respond(strings['chat_removed'])
        else:
            await event.respond(strings['chat_404'])
    
    elif command[0]=='/chats':
        chat_list = [f"{a['nick']}: `{a['chat_id']}`" for a in database.my_chats.find()]
        await event.respond(strings['chat_list_title']+"\n".join(chat_list))

    else:
        return
    raise events.StopPropagation

# === COMMAND HANDLING (ALL) ===
@bot.on(events.NewMessage(func=lambda e:e.is_private))
async def handler(event):
    m = re.search(r"^https?://t\.me/c/(\d+)/(\d+)$", event.message.text)
    if m:
        chatId = int('-100'+m[1])
        messageId = int(m[2])
        post = database.chat_posts.find_one({
            'chat_id': chatId,
            'message_id': messageId
        })
        if post is None:
            await event.respond(strings['post_404'])
        else:
            buttons = [Button.inline(strings['add_btn'], f'+btn.{chatId}.{messageId}')]
            await event.respond(post['text'], buttons=buttons)

with bot:
    bot.run_until_disconnected()