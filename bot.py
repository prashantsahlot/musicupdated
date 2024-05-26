import logging
import os
import time
import requests
import telebot
from pytube import YouTube, exceptions
from urllib.error import HTTPError
from urllib3.exceptions import MaxRetryError

# --- Configuration ---
TOKEN = '6459647682:AAFmuOlwiUCWhDz1X6-6p6QG9u-YH6qexZ8'
YOUTUBE_API_KEY = 'AIzaSyATjDFifmrmn5vwTRLVcLtNM3q_9_kJ6yk'  # Ensure this is valid
START_IMAGE_LINK = 'https://telegra.ph/file/82e3f9434e48d348fa223.jpg'
DOWNLOAD_DIRECTORY = 'downloads'
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DOWNLOAD_RETRIES = 3

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Bot Initialization ---
bot = telebot.TeleBot(TOKEN, parse_mode=None)
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
# ... (Your get_uptime and search_youtube functions)

# --- Download with Retries ---
def download_with_retries(stream, file_path):
    for attempt in range(MAX_DOWNLOAD_RETRIES):
        try:
            stream.download(output_path=DOWNLOAD_DIRECTORY, filename=file_path)
            return True  # Download successful
        except (HTTPError, MaxRetryError) as e:
            logger.warning(f"Download attempt {attempt + 1} failed: {e}")
            time.sleep(2)  # Wait before retrying
    return False  # All retries failed


# --- Message Handlers ---
# ... (Your send_welcome, ping_command, and search handlers)

@bot.message_handler(commands=['audio', 'video'])
def handle_download(message):
    command = message.text.split()[0]
    is_audio = command == '/audio'

    try:
        youtube_link = message.text.strip().split(' ', 1)[1]
        yt = YouTube(youtube_link)

        # Choose stream based on format
        stream = (
            yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if is_audio
            else yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        )

        if not stream:
            bot.reply_to(message, "❌ No suitable stream found.")
            return

        file_name = stream.default_filename
        file_path = os.path.join(DOWNLOAD_DIRECTORY, file_name)

        # Download with retries
        if download_with_retries(stream, file_name):
            # Send video/audio
            with open(file_path, 'rb') as file:
                bot.send_chat_action(message.chat.id, 'upload_video' if not is_audio else 'upload_audio')
                if is_audio:
                    bot.send_audio(message.chat.id, file, caption=yt.title)
                else:
                    bot.send_video(message.chat.id, file)
            os.remove(file_path)  # Remove the file after sending

        else:
            handle_download_error(message, "downloading", "Maximum download retries exceeded.")

    except (IndexError, exceptions.RegexMatchError):
        bot.reply_to(message, f"Invalid command. Use: {command} <YouTube link>")
    except Exception as e:
        handle_download_error(message, "downloading", str(e))


# --- Error Handling ---
# ... (Your handle_download_error function)


# --- Main ---
if __name__ == '__main__':
    try:
        os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)
        logger.info("Bot is starting...")
        bot.infinity_polling(skip_pending=True, timeout=10)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409:
            logger.error("Conflict: Another instance of the bot is running. Please stop it before starting this one.")
        else:
            logger.error(f"Telegram API Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

