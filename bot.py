from collections import defaultdict
import time         # used when to delay the code from sending another file incase of timeout
import threading  # used to delay the deletion of bot message
import yt_dlp as youtube_dl
import os
from telebot import telebot, apihelper, types
import subprocess # just for checking the installation of ffmpeg

apihelper.RETRY_ON_TIMEOUT = True
apihelper.REQUEST_TIMEOUT = 30



try:
    result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("FFmpeg is installed:")
    print(result.stdout)
except FileNotFoundError:
    print("FFmpeg is not available.")


ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')  # Default to 'ffmpeg' if not set
print(f"Using ffmpeg at: {ffmpeg_path}")
bot = telebot.TeleBot('7605652395:AAEFXGuQrrM1FZLKRjJPD6JT0lQ-IgRDTGw')

FFMPEG_PATH = ffmpeg_path


current_page = defaultdict(lambda: 0)
search_title = defaultdict(str)
search_list = {}

commands = [
    types.BotCommand("start", "Start the bot"),
    types.BotCommand("help", "Show help information")
]

bot.set_my_commands(commands)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! 👋 I'm a Telegram bot for downloading songs from YouTube.")


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "/start - Start the bot\n/help - Show help\n/download <song name> - Download the requested song")


def download_from_youtube(song_name, message):

    markup = types.InlineKeyboardMarkup(row_width=1)

    chat_id = message.chat.id
    # artist_name = ""
    ydl_opts = {
        # 'cookiefile': 'cookies.txt',
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'ffmpeg_location': FFMPEG_PATH,
        'quiet': True,
        'noplaylist': True,
        'concurrent_fragment_downloads': 5,
    }

    search_query = f"ytsearch1:{song_name}"
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            video_info = info['entries'][0]

            file_path = ydl.prepare_filename(info['entries'][0])
            names = file_path.replace("downloads\\", " ").split("-")
            mp3_file_path = file_path.rsplit('.', 1)[0] + '.mp3'

            if "Official" in file_path:
                artist_name = video_info.get('artist', video_info.get('uploader', 'Unknown Artist'))
                print("artist_name(video_info) = ", artist_name)
            else:
                artist_name = names[0]
                print("\n\nartist_name(names[0]) = ", artist_name)
            print(mp3_file_path)
            if os.path.exists(mp3_file_path):
                with open(mp3_file_path, 'rb') as audio_file:
                    for i in range(3):  # Try up to 3 times
                        try:
                            artist_name_button = types.InlineKeyboardButton(f"artist_name: {artist_name}", callback_data=f"Artist {artist_name}")
                            markup.add(artist_name_button)
                            bot.send_audio(
                                chat_id=chat_id,
                                audio=audio_file,
                                timeout=180,
                                reply_markup=markup
                            )
                            # print(f"Audio: {mp3_file_path.replace('downloads\\', ' ')} -> Sent to user: {message.chat.username}")
                            break
                        except Exception as e:
                            print(f"Retry {i + 1}/3 failed: {e}")
                            time.sleep(5)
                os.remove(mp3_file_path)
            else:
                temp_text = bot.reply_to(message, f"Failed to find the audio file: {mp3_file_path}")
                threading.Timer(30.0, lambda: bot.delete_message(chat_id, temp_text.id)).start()

    except Exception as e:
        temp_text = bot.reply_to(message, f"An error occurred: {str(e)}")

        threading.Timer(30.0, lambda: bot.delete_message(chat_id, temp_text.id)).start()


@bot.callback_query_handler(func=lambda call: True)
def choice_handler(call):
    global search_title, current_page

    chat_id = call.message.chat.id
    message_id = call.message.id

    if chat_id not in current_page:
        current_page[chat_id] = 0
        print(f"declare current_page[{chat_id}] = {0}")
    if chat_id not in search_title:
        search_title[chat_id] = ""
        print(f"search_title[{chat_id}] = \"\"")

    if call.data == 'close':
        print('Close button clicked')
        bot.delete_message(chat_id, message_id)

    elif call.data == 'next':
        print('Next button clicked')
        if current_page[chat_id] == 4:
            temp_text = bot.send_message(chat_id, f"This is the last page!!")
            threading.Timer(15.0, lambda: bot.delete_message(chat_id, temp_text.id)).start()
        else:
            current_page[chat_id] += 1
            search_from_youtube(search_title[chat_id], call.message, current_page[chat_id])

    elif call.data == 'back':
        print('Back button clicked')
        if current_page[chat_id] == 0:
            temp_text = bot.send_message(chat_id, f"This is the first page!!")
            threading.Timer(15.0, lambda: bot.delete_message(chat_id, temp_text.id)).start()
        else:
            current_page[chat_id] -= 1
            search_from_youtube(search_title[chat_id], call.message, current_page[chat_id])

    elif "Artist" in call.data:
        artist_name = call.data.replace("Artist", " ")
        search_from_youtube(artist_name, call.message)

    else:
        temp_text = bot.send_message(chat_id, f"Downloading...")
        threading.Timer(5.0, lambda: download_from_youtube(call.data, call.message)).start()
        bot.delete_message(chat_id, temp_text.id)


def format_number(n):
    try:
        num = int(n)
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
    except Exception as e:
        print(f"Can`t change to integer: {e}")

    else:
        return str(n)


def search_from_youtube(song_name, message, page=0):
    global search_title, current_page, search_list

    chat_id = message.chat.id
    message_id = message.id
    page_items = []
    markup = types.InlineKeyboardMarkup(row_width=2)
    ydl_opts = {
        'format': 'bestaudio/best',
        'extract_flat': True,
    }

    search_query = f"ytsearch25:{song_name}"
    try:
        print(search_query)
        if song_name != search_title[chat_id]:
              with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info['entries']

                current_page[chat_id] = page
                search_title[chat_id] = song_name
                search_list[chat_id] = entries
                page_items = entries[0:5]
        else:
            page_items = search_list[chat_id][current_page[chat_id] * 5:(current_page[chat_id] + 1) * 5]

        for item in page_items:
            formated_view = format_number(item.get("view_count", "No data"))
            # formated_like = format_number(item.get("like_count", "No data"))
            button = types.InlineKeyboardButton(
                f"{item['title']}:  👀 {formated_view} ", callback_data=item['id'])
            markup.add(button)

        print(f"search_title: {search_title}")

        back_btn = types.InlineKeyboardButton('⬅️ Back', callback_data='back')
        next_btn = types.InlineKeyboardButton('➡️ Next', callback_data='next')
        close_btn = types.InlineKeyboardButton("❌ Close", callback_data='close')

        markup.add(back_btn, next_btn, close_btn)

           # help to clear the list of songs when next or back button clicked
        try:
            if not message.audio:
                bot.delete_message(chat_id, message_id)
        except Exception as e:
            print(f"I think message does not exist. Error: {e}")

        temp_text = bot.send_message(message.chat.id, f"Result of {song_name}: ", reply_markup=markup)
        threading.Timer(300.0, lambda: bot.delete_message(chat_id, temp_text.id)).start()   # waits 5 min before deletion
    except Exception as e:
        temp_text = bot.reply_to(message, f"An error occurred: {e}")

        threading.Timer(30.0, lambda: bot.delete_message(chat_id, temp_text.id)).start()


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    chat_id = message.chat.id
    song_name = message.text

    if not song_name:
        bot.reply_to(message, "Please provide the song name after the command, like /download despacito")
        return
    temp_text = bot.reply_to(message, f"Searching for '{song_name}' on YouTube...")
    search_from_youtube(song_name, message)

    bot.delete_message(chat_id, temp_text.id)
    # bot.delete_message(chat_id, message.id)


bot.polling()
