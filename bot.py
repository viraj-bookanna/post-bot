import os,logging,json,requests,urllib.parse
from telethon import TelegramClient, events
from telethon.tl.custom.button import Button
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta

load_dotenv(override=True)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URL = os.getenv('MONGODB_URL')
TIME_ZONE = os.getenv('TIME_ZONE')
CRONJOB_TOKEN = os.getenv('CRONJOB_TOKEN')
database = MongoClient(MONGODB_URL).post_bot
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
buttons_main = [
    [Button.text('📌 Create post', resize=True), Button.text('📝Edit Post', resize=True), ]
]

async def set_edit_kbd(msg):
    buttons_post_mgr = [
        [Button.text('👁‍🗨 Preview', resize=True), Button.text('⚙️ Options', resize=True), Button.text('Get Buttons', resize=True), Button.text('📝 Edit Content', resize=True), ],
        [Button.text('Cancel', resize=True), Button.text('☑️ Done', resize=True), ],
    ]
    await msg.reply('''This is a preview of how your message would look like.
you can edit parse_mode and webpage preview by clicking on Options
to add inline buttons, click on the ➕ key on the row you want to add a button.
to delete inline buttons click on the button you want to remove.
to preview the message (without the extra ➕ buttons) click on preview.
when you finished editing, press Done to receive the `post number`.''', buttons=buttons_post_mgr)
def timedelta_to_next_occurrence(target_time):
    target_hour, target_minute, target_second = map(int, target_time.split(':'))
    current_time = datetime.now().time()
    current_datetime = datetime.combine(datetime.now().date(), current_time)
    next_day_datetime = datetime.now() + timedelta(days=1)
    target_datetime_today = current_datetime.replace(hour=target_hour, minute=target_minute, second=target_second)
    target_datetime_tomorrow = datetime.combine(next_day_datetime.date(), datetime.min.time()).replace(hour=target_hour, minute=target_minute, second=target_second)
    if current_datetime > target_datetime_today:
        return target_datetime_tomorrow - current_datetime
    else:
        return target_datetime_today - current_datetime
def option_kbd(parse=0, web=0):
    if parse in [None, 'md', 'HTML']:
        parse = [None, 'md', 'HTML'].index(parse)
    if web in [True, False] and type(web)!=int:
        web = [True, False].index(web)
    parse = int(parse)
    web = int(web)
    t = ' ✅'
    return [
        [Button.inline('Parse Mode', 'ses'), ],
        [
            Button.inline('Normal'+(t if parse==0 else ''), 'options:'+json.dumps({'p': 0, 'w': web})),
            Button.inline('Markdown'+(t if parse==1 else ''), 'options:'+json.dumps({'p': 1, 'w': web})),
            Button.inline('HTML'+(t if parse==2 else ''), 'options:'+json.dumps({'p': 2, 'w': web})),
        ],
        [Button.inline('Web Page Preview', 'ses'), ],
        [
            Button.inline('Yes'+(t if web==0 else ''), 'options:'+json.dumps({'p': parse, 'w': 0})),
            Button.inline('No'+(t if web==1 else ''), 'options:'+json.dumps({'p': parse, 'w': 1})),
        ],
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

@bot.on(events.NewMessage(func=lambda e:e.is_private, outgoing=False))
async def handler(event):
    user = database.users.find_one({'chat_id': event.chat_id})
    if user is None:
        sender = await event.get_sender()
        database.users.insert_one({
            'chat_id': sender.id,
            'first_name': sender.first_name,
            'last_name': sender.last_name,
            'parse_mode': None,
            'link_preview': True
        })
    if event.message.text == '🔙':
        user['post_id'] = user['post_id_back']
        database.users.update_one({'_id': user['_id']}, {"$set": user})
    
    if event.message.text == '/start':
        await event.respond('''Welcome 🌺
using this bot you can create cool posts with buttons, markdown text, HTML text, and embedded links.
then you can send it anywhere you want using inline mode
if you want to send the post to your channel without inline mode you need to get your own instance of this bot.''', buttons=buttons_main)
    
    elif event.message.text == '/help':
        await event.respond('press /start', buttons=Button.clear())
    
    elif event.message.text in ['📌 Create post', '📌 Create another post']:
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
            data = {
                'chat_id': event.chat_id,
            }
        if event.message.media is not None:
            data['media'] = event.message.id
            media = event.message.media
        elif 'media' in data:
            media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
        else:
            media = None
        if event.message.text is not None or event.message.text!='':
            data['text'] = event.message.text
        if user.get('post_id', None) is not None:
            database.posts.update_one({'_id': data['_id']}, {"$set": data})
        else:
            user['post_id'] = database.posts.insert_one(data).inserted_id
            database.users.update_one({'_id': user['_id']}, {"$set": user})
        buttons = inlinefy([] if 'buttons' not in data else data['buttons'], user['post_id'])
        msg = await event.respond(data['text'], file=media, buttons=buttons, parse_mode=user['parse_mode'], link_preview=user['link_preview'])
        await set_edit_kbd(msg)

    elif user['next'] =='edit_post':
        data = database.posts.find_one({'_id': ObjectId(event.message.text), 'chat_id': event.chat_id})
        if data is not None:
            user['post_id'] = event.message.text
            user['next'] = None
            database.users.update_one({'_id': user['_id']}, {"$set": user})
            if 'media' in data:
                media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
            else:
                media = None
            buttons = inlinefy([] if 'buttons' not in data else data['buttons'], user['post_id'])
            msg = await event.respond(data['text'], file=media, buttons=buttons, parse_mode=user['parse_mode'], link_preview=user['link_preview'])
            await set_edit_kbd(msg)
        else:
            await event.respond("Post not found.", buttons=Button.clear())

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
            print(user)
            if type(user['btn_data']['address'][1])==int and 0 <= user['btn_data']['address'][1] < len(b_list[user['btn_data']['address'][0]]):
                b_list[user['btn_data']['address'][0]][user['btn_data']['address'][1]] = {'text': user['btn_data']['text'], 'url': event.message.text}
            else:
                b_list[user['btn_data']['address'][0]].append({'text': user['btn_data']['text'], 'url': event.message.text})
        data['buttons'] = b_list
        database.posts.update_one({'_id': data['_id']}, {"$set": data})
        if 'media' in data:
            media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
        else:
            media = None
        msg = await event.respond(data['text'],  file=media, buttons=inlinefy(b_list, user['post_id']), parse_mode=user['parse_mode'], link_preview=user['link_preview'])
        await set_edit_kbd(msg)
    
    elif user['next'] == 'del_btn':
        data = database.posts.find_one({'_id': ObjectId(user['post_id'])})
        b_list = [] if 'buttons' not in data else data['buttons']
        if event.message.text in ['Yes', 'No']:
            if 'media' in data:
                media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
            else:
                media = None
            if event.message.text == 'Yes':
                del b_list[user['btn_data']['address'][0]][user['btn_data']['address'][1]]
                data['buttons'] = b_list
                database.posts.update_one({'_id': data['_id']}, {"$set": data})
            msg = await event.respond(data['text'],  file=media, buttons=inlinefy(b_list, user['post_id']), parse_mode=user['parse_mode'], link_preview=user['link_preview'])
            await set_edit_kbd(msg)
        elif event.message.text == '📝 Edit':
            user['next'] = 'add_btn_text'
            database.users.update_one({'_id': user['_id']}, {"$set": user})
            await event.respond('Please send text for button:', buttons=Button.clear())

    elif event.message.text in ['🔙', '👁‍🗨 Preview','⚙️ Options','Get Buttons','📝 Edit Content','Cancel','☑️ Done'] and user.get('post_id', None) is not None:
        data = database.posts.find_one({'_id': ObjectId(user['post_id'])})
        b_list = [] if 'buttons' not in data else data['buttons']
        if event.message.text in ['🔙', '👁‍🗨 Preview']:
            if 'media' in data:
                media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
            else:
                media = None
            if event.message.text == '🔙':
                msg = await event.respond(data['text'],  file=media, buttons=inlinefy(b_list, user['post_id']), parse_mode=user['parse_mode'], link_preview=user['link_preview'])
                await set_edit_kbd(msg)
            else:
                await event.respond(data['text'],  file=media, buttons=urlfy(b_list), parse_mode=user['parse_mode'], link_preview=user['link_preview'])
        elif event.message.text == '⚙️ Options':
            await event.respond('Click on the desired option to select it.', buttons=option_kbd(user['parse_mode'], user['link_preview']))
        elif event.message.text == 'Get Buttons':
            await event.respond(json.dumps(b_list, indent=4))
        elif event.message.text == '📝 Edit Content':
            user['next'] = 'create_post'
            database.users.update_one({'_id': user['_id']}, {"$set": user})
            await event.respond('Enter new content for the post', buttons=Button.clear())
        elif event.message.text == 'Cancel':
            database.posts.delete_one({'_id': ObjectId(user['post_id'])})
            user['post_id'] = None
            database.users.update_one({'_id': user['_id']}, {"$set": user})
            await event.respond('''Welcome 🌺
using this bot you can create cool posts with buttons, markdown text, HTML text, and embedded links.
then you can send it anywhere you want using inline mode
if you want to send the post to your channel without inline mode you need to get your own instance of this bot.''', buttons=buttons_main)
        elif event.message.text == '☑️ Done':
            me = await bot.get_me()
            user['post_id_back'] = user['post_id']
            user['post_id'] = None
            database.users.update_one({'_id': user['_id']}, {"$set": user})
            buttons = [
                [Button.text('📌 Create another post', resize=True), Button.text('🔙', resize=True)]
            ]
            await event.respond(f'''☑️ Post has been saved. your post number is: {user['post_id_back']}
to send it via inline mode use:

`@{me.username} {user['post_id_back']}`''', buttons=buttons)
            
    elif event.message.text.startswith('/schedule'):
        inp = event.message.text.split(' ')
        if len(inp) != 4:
            await event.respond('Invalid syntax\nsyntax:\n`/schedule post_id chat_id HH:MM:SS`\nHH:MM:SS is in 24 hour format')
            return
        data = database.posts.find_one({'_id': ObjectId(inp[1])})
        if data is None:
            await event.respond('post not found')
            return
        try:
            await bot.send_message(int(inp[2]), event.message.text, schedule=timedelta_to_next_occurrence(inp[3]))
            result = database.schedules.insert_one({'chat_id': event.chat_id, 'post_id': inp[1], 'target_chat_id': inp[3], 'time': inp[3]})
            await event.respond(f'''schedule created successfully!
Schedule ID: `{result.inserted_id}`

to stop the schedule:
`/stop {result.inserted_id}`''', buttons=Button.clear())
        except KeyboardInterrupt as e:
            await event.respond(repr(e))

    elif event.message.text.startswith('/stop'):
        inp = event.message.text.split(' ', 1)
        if len(inp)!= 2:
            await event.respond('invalid syntax\n\nsyntax: `/stop schedule_id`')
            return
        schedule = database.schedules.find_one({'_id': ObjectId(inp[1]), 'chat_id': event.chat_id})
        if schedule is None:
            await event.respond('schedule not found')
            return
        user['next'] = 'stop_schedule'
        user['stop_schedule'] = inp[1]
        database.users.update_one({'_id': user['_id']}, {"$set": user})
        buttons = [
            [Button.text('Yes', resize=True), Button.text('No', resize=True)]
        ]
        await event.respond(f'Are you sure you want to delete schedule {inp[1]} ?', buttons=buttons)

    elif user['next'] == 'stop_schedule':
        if event.message.text == 'Yes':
            schedule = database.schedules.find_one({'_id': ObjectId(user['stop_schedule']), 'chat_id': event.chat_id})
            if schedule is None:
                await event.respond('schedule not found', buttons=Button.clear())
            else:
                database.schedules.delete_one({'_id': ObjectId(user['stop_schedule']), 'chat_id': event.chat_id})
                await event.respond('schedule deleted', buttons=Button.clear())
        elif event.message.text == 'No':
            await event.respond('cancelled', buttons=Button.clear())
        else:
            await event.respond('invalid option')
        user['next'] = None
        database.users.update_one({'_id': user['_id']}, {"$set": user})

@bot.on(events.NewMessage(outgoing=True))
async def handler(event):
    if event.message.text.startswith('/schedule'):
        inp = event.message.text.split(' ')
        if len(inp) != 4:
            return
        data = database.posts.find_one({'_id': ObjectId(inp[1])})
        if data is None:
            return
        b_list = [] if 'buttons' not in data else data['buttons']
        user = database.users.find_one({'chat_id': data['chat_id']})
        if 'media' in data:
            media = (await bot.get_messages(event.chat_id, ids=data['media'])).media
        else:
            media = None
        await event.delete()
        await event.respond(data['text'],  file=media, buttons=urlfy(b_list), parse_mode=user['parse_mode'], link_preview=user['link_preview'])
        await bot.send_message(event.chat_id, event.message.text, schedule=timedelta_to_next_occurrence(inp[3]))

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
    for i in range(len(query)):
        try:
            query[i] = int(query[i])
        except:
            pass
    if query[0].startswith('options:'):
        opts = json.loads(query[0].split(':', 1)[1])
        user = database.users.find_one({'chat_id': event.chat_id})
        user['parse_mode'] = [None, 'md', 'HTML'][opts['p']]
        user['link_preview'] = [True, False][opts['w']]
        database.users.update_one({'_id': user['_id']}, {"$set": user})
        await event.edit('Click on the desired option to select it.', buttons=option_kbd(opts['p'], opts['w']))
        return
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

    else:
        user['post_id'] = query[0]
        user['btn_data'] = {
            'address': query[1:]
        }
        user['next'] = 'del_btn'
        database.users.update_one({'_id': user['_id']}, {"$set": user})
        buttons = [
            [Button.text('Yes', resize=True), Button.text('No', resize=True), Button.text('📝 Edit', resize=True)]
        ]
        await event.respond(f'Are you sure you want to delete button in row {query[1]}, column {query[2]} with text {b_list[query[1]][query[2]]["text"]} and url {b_list[query[1]][query[2]]["url"]} ?', buttons=buttons)

@bot.on(events.InlineQuery)
async def handler(event):
    #print(await event.get_sender())
    if event.text is None or event.text == '':
        return
    data = database.posts.find_one({'_id': ObjectId(event.text)})
    user = database.users.find_one({'chat_id': data['chat_id']})
    if data is None:
        return
    if 'media' in data:
        media = (await bot.get_messages(data['chat_id'], ids=data['media'])).media
    else:
        media = None
    await event.answer([
        event.builder.article(
            f'send post: {event.text}',
            text=data['text'],
            #file=media,
            buttons=urlfy([] if 'buttons' not in data else data['buttons']),
            parse_mode=user['parse_mode'],
            link_preview=user['link_preview'],
        )
    ])

# Event handler for new members joining the group
@bot.on(events.ChatAction(func=lambda event: event.user_joined))
async def welcome(event):
    # Get the chat ID
    
    chat_id = event.chat_id
    new_member = event.user.first_name
    databasewl = database.welcome
    last_welcome_msg_id = databasewl.find_one({'chat_id': chat_id})
    if last_welcome_msg_id:
        try:
            await bot.delete_messages(chat_id, last_welcome_msg_id['message_id'])
            print("Last welcome message deleted.")
        except Exception as e:
            print("Error deleting message:", e)
    WELCOME_MESSAGE = f"Hello {new_member},\nWelcome to Setrade Asia Group! Click the button below to visit SETrade Asia."
    BUTTON_URL = "https://setrade.asia"
    welcome_msg = await event.respond(WELCOME_MESSAGE, buttons=[[Button.url("Visit SETrade Asia", BUTTON_URL)]])
    databasewl.update_one({'chat_id': chat_id}, {'$set': {'message_id': welcome_msg.id}}, upsert=True)

with bot:
    bot.run_until_disconnected()