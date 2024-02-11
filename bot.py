import os,logging,json
from telethon import TelegramClient, events
from telethon.tl.custom.button import Button
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

load_dotenv(override=True)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URL = os.getenv('MONGODB_URL')
database = MongoClient(MONGODB_URL).post_bot
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
buttons_post_mgr = [
    [Button.text('👁‍🗨 Preview', resize=True), Button.text('⚙️ Options', resize=True), Button.text('Get Buttons', resize=True), Button.text('📝 Edit Content', resize=True), ],
    [Button.text('Cancel', resize=True), Button.text('☑️ Done', resize=True), ],
]

def urlfy(data):
    if data==[]:
        return None
    elif type(data)==list:
        kbd = []
        for item in data:
            kbd.append(urlfy(item))
        return kbd
    elif type(data)==dict:
        return Button.url(data['text'], data['url'])
def inlinefy(data, prefix, level=0):
    if type(data)==list:
        kbd = []
        for i in range(len(data)):
            kbd.append(inlinefy(data[i], f'{prefix}-{i}', level+1))
        if level==0:
            kbd.append([Button.inline('➕', f'{prefix}-+')])
        else:
            kbd.append(Button.inline('➕', f'{prefix}-+'))
        return kbd
    elif type(data)==dict:
        return Button.inline(data['text'], prefix)

@bot.on(events.NewMessage(func=lambda e:e.is_private))
async def handler(event):
    user = database.users.find_one({'chat_id': event.chat_id})
    if user is None:
        sender = await event.get_sender()
        database.users.insert_one({
            'chat_id': sender.id,
            'first_name': sender.first_name,
            'last_name': sender.last_name
        })
    if event.message.text == '/start':
        buttons = [
            [Button.text('📌 Create post', resize=True), Button.text('📝Edit Post', resize=True), ]
        ]
        await event.respond('''Welcome 🌺
using this bot you can create cool posts with buttons, markdown text, HTML text, and embedded links.
then you can send it anywhere you want using inline mode
if you want to send the post to your channel without inline mode you need to get your own instance of this bot.''', buttons=buttons)
    
    elif event.message.text == '/help':
        await event.respond('press /start', buttons=Button.clear())
    
    elif event.message.text == '📌 Create post':
        user['next'] = 'create_post'
        user['post_id'] = None
        database.users.update_one({'_id': user['_id']}, {"$set": user})
        await event.respond("Send your post's content it can be anything. (text, 🖼photo, 🎙audio, ...)", buttons=Button.clear())
    
    elif event.message.text == '📝Edit Post':
        user['next'] = 'edit_post'
        database.users.update_one({'_id': user['_id']}, {"$set": user})
        await event.respond("Enter the post number that you want to edit. Ex: 1", buttons=Button.clear())

    elif user['next'] == 'create_post':
        if user.get('post_id', None) is not None:
            data = database.posts.find_one({'_id': ObjectId(user['post_id'])})
        else:
            data = {'chat_id': event.chat_id}
        print('1 -->', data)
        if event.message.media is not None:
            data['media'] = event.message.id
            media = event.message.media
        elif 'media' in data:
            media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
        else:
            media = None
        if event.message.text!='' or event.message.text is not None:
            data['text'] = event.message.text
        if user.get('post_id', None) is not None:
            database.posts.update_one({'_id': data['_id']}, {"$set": data})
        else:
            user['post_id'] = database.posts.insert_one(data).inserted_id
            database.users.update_one({'_id': user['_id']}, {"$set": user})
        print('2 -->', data)
        buttons = inlinefy([] if 'buttons' not in data else data['buttons'], user['post_id'])
        msg = await event.respond(data['text'], file=media, buttons=buttons)
        await msg.reply('''This is a preview of how your message would look like.
you can edit parse_mode and webpage preview by clicking on Options
to add inline buttons, click on the ➕ key on the row you want to add a button.
to delete inline buttons click on the button you want to remove.
to preview the message (without the extra ➕ buttons) click on preview.
when you finished editing, press Done to receive the `post number`.''', buttons=buttons_post_mgr)

    elif user['next'] == 'add_btn_text':
        user['btn_data']['text'] = event.message.text
        user['next'] = 'add_btn_url'
        database.users.update_one({'_id': user['_id']}, {"$set": user})
        await event.respond("Please send url for button:", buttons=Button.clear())
    
    elif user['next'] == 'add_btn_url':
        user['next'] = None
        database.users.update_one({'_id': user['_id']}, {"$set": user})
        data = database.posts.find_one({'_id': ObjectId(user['post_id'])})
        b_list = [] if 'buttons' not in data else data['buttons']
        if len(user['btn_data']['address'])==1:
            b_list.append([{'text': user['btn_data']['text'], 'url': event.message.text}])
        else:
            b_list[int(user['btn_data']['address'][0])].append({'text': user['btn_data']['text'], 'url': event.message.text})
        data['buttons'] = b_list
        database.posts.update_one({'_id': data['_id']}, {"$set": data})
        if 'media' in data:
            media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
        else:
            media = None
        msg = await event.respond(data['text'],  file=media, buttons=inlinefy(b_list, user['post_id']))
        await msg.reply('''This is a preview of how your message would look like.
you can edit parse_mode and webpage preview by clicking on Options
to add inline buttons, click on the ➕ key on the row you want to add a button.
to delete inline buttons click on the button you want to remove.
to preview the message (without the extra ➕ buttons) click on preview.
when you finished editing, press Done to receive the `post number`.''', buttons=buttons_post_mgr)
    
    elif event.message.text in ['👁‍🗨 Preview','⚙️ Options','Get Buttons','📝 Edit Content','Cancel','☑️ Done'] and user.get('post_id', None) is not None:
        data = database.posts.find_one({'_id': ObjectId(user['post_id'])})
        b_list = [] if 'buttons' not in data else data['buttons']
        if event.message.text == '👁‍🗨 Preview':
            if 'media' in data:
                media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
            else:
                media = None
            await event.respond(data['text'],  file=media, buttons=urlfy(b_list))
        elif event.message.text == '⚙️ Options':
            pass
        elif event.message.text == 'Get Buttons':
            await event.respond(json.dumps(b_list, indent=4))
        elif event.message.text == '📝 Edit Content':
            pass
        elif event.message.text == 'Cancel':
            pass
        elif event.message.text == '☑️ Done':
            pass

@bot.on(events.CallbackQuery(func=lambda e:e.is_private))
async def handler(event):
    user = database.users.find_one({'chat_id': event.chat_id})
    if user is None:
        sender = await event.get_sender()
        database.users.insert_one({
            'chat_id': sender.id,
            'first_name': sender.first_name,
            'last_name': sender.last_name
        })
    query = event.data.decode().split('-')
    print(query)
    data = database.posts.find_one({'_id': ObjectId(query[0])})
    b_list = [] if 'buttons' not in data else data['buttons']
    if query[-1] == '+':
        user['post_id'] = query[0]
        user['btn_data'] = {
            'address': query[1:]
        }
        user['next'] = 'add_btn_text'
        database.users.update_one({'_id': user['_id']}, {"$set": user})
        await event.respond('Please send text for button:', buttons=Button.clear())

with bot:
    bot.run_until_disconnected()