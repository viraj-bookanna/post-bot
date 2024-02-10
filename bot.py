import os,logging,sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv
from strings import strings,direct_reply

load_dotenv(override=True)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
SUPER_ADMINS = os.getenv('SUPER_ADMINS', '').split(',')
ADMINS = []
CONN = sqlite3.connect('database.db')
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def db_get(key, default=None):
    try:
        cursor = CONN.cursor()
        cursor.execute('SELECT value FROM key_values WHERE key=?', (key,))
        return cursor.fetchone()[0]
    except:
        return default
def db_put(key, value):
    cursor = CONN.cursor()
    cursor.execute('''
CREATE TABLE IF NOT EXISTS key_values (
    key INT PRIMARY KEY,
    value TEXT
)
''')
    cursor.execute('INSERT OR REPLACE INTO key_values (key, value) VALUES (?, ?)', (key, value))
    CONN.commit()
 
'''
==  Non processed handling  ==
this section contain the direct responses and access checking part
see strings.py for default string values
'''
@bot.on(events.NewMessage(func=lambda e:e.is_private))
async def handler(event):
    if event.chat_id not in SUPER_ADMINS+ADMINS:
        event.respond(strings['no_access'])
    elif event.message.text in direct_reply.keys():
        event.respond(direct_reply[event.message.text])
    raise events.StopPropagation

'''
==  Processed handling  ==
'''