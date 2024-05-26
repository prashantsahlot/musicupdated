import logging
import os
import time
import requests
import telebot
from pytube import YouTube
from pytube.exceptions import RegexMatchError

# --- Configuration ---
TOKEN = '6459647682:AAFmuOlwiUCWhDz1X6-6p6QG9u-YH6qexZ8'
YOUTUBE_API_KEY = 'AIzaSyATjDFifmrmn5vwTRLVcLtNM3q_9_kJ6yk'  
START_IMAGE_LINK = 'https://telegra.ph/file/82e3f9434e48d348fa223.jpg'
DOWNLOAD_DIRECTORY = 'downloads'
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DOWNLOAD_RETRIES = 3

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Bot Initialization ---
bot = telebot.TeleBot(TOKEN)
start_time = time.time()

# --- Start Menu Text ---
START_MENU_TEXT = (
    "Hello! I'm a YouTube downloader bot. Use these commands:\n\n"
    "🎵 /audio <YouTube link> : Download audio\n"
    "🎥 /video <YouTube link> : Download video\n"
    "🔍 /search <query> : Search for YouTube videos\n"
    "🏓 /ping : Check my status"
)


# --- Helper Functions ---
def get_uptime():
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)
    uptime_minutes = uptime_seconds // 60
    uptime_seconds %= 60
    return f"{uptime_minutes} minutes, {uptime_seconds} seconds"


def search_youtube(query):
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=10&q={query}&key={YOUTUBE_API_KEY}"
    response = requests.get(search_url)
    response_data = response.json()

    if response_data['items']:
        video_ids = [item['id']['videoId'] for item in response_data['items']]
        video_urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]
        return "\n".join(video_urls)
    else:
        return "No results found."


# --- Download Function ---
def download_and_send(message, youtube_link, is_audio=False):
    try:
        yt = YouTube(youtube_link)

        # Choose stream based on format
        stream = (
            yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if is_audio
            else yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        )

        if not stream:
            raise Exception("No suitable stream found.")

        file_name = stream.default_filename
        file_path = os.path.join(DOWNLOAD_DIRECTORY, file_name)

        # Download the file (add retry logic if needed)
        stream.download(output_path=DOWNLOAD_DIRECTORY)

        # Send the file
        with open(file_path, 'rb') as file:
            bot.send_chat_action(message.chat.id, 'upload_video' if not is_audio else 'upload_audio')
            if is_audio:
                bot.send_audio(message.chat.id, file, caption=yt.title)
            else:
                bot.send_video(message.chat.id, file)
        os.remove(file_path)

    except RegexMatchError:
        bot.reply_to(message, "Invalid YouTube link.")
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        bot.reply_to(message, "An error occurred while downloading. Please try again later.")



# --- Bot Handlers ---
@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    bot.send_photo(message.chat.id, START_IMAGE_LINK, caption=START_MENU_TEXT)

@bot.message_handler(commands=['ping'])
def handle_ping(message):
    bot.reply_to(message, f"Pong! 🏓 Uptime: {get_uptime()}")


@bot.message_handler(commands=['search'])
def handle_search(message):
    try:
        query = message.text.split(maxsplit=1)[1]
        search_results = search_youtube(query)
        bot.reply_to(message, search_results)
    except IndexError:
        bot.reply_to(message, "Please provide a search query. Usage: /search <query>")

@bot.message_handler(commands=['audio'])
def handle_audio(message):
    try:
        youtube_link = message.text.split(maxsplit=1)[1]
        download_and_send(message, youtube_link, is_audio=True) 
    except IndexError:
        bot.reply_to(message, "Please provide a YouTube link. Usage: /audio <link>")


@bot.message_handler(commands=['video'])
def handle_video(message):
    try:
        youtube_link = message.text.split(maxsplit=1)[1]
        download_and_send(message, youtube_link)  # Default is video download
    except IndexError:
        bot.reply_to(message, "Please provide a YouTube link. Usage: /video <link>")




# --- Main Loop ---
if __name__ == '__main__':
    os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)
    logger.info("Bot is starting...")
    bot.infinity_polling() 


