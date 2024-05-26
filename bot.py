import logging
import os
import time
import requests
import telebot
import threading
from pytube import YouTube, exceptions
from urllib.error import HTTPError
from urllib3.exceptions import MaxRetryError

# --- Configuration ---
TOKEN = '6459647682:AAHaDcMlNKfoc2jNQ1j-tVYMdEYvyHM0Gws'  # Your bot token
YOUTUBE_API_KEY = 'AIzaSyATjDFifmrmn5vwTRLVcLtNM3q_9_kJ6yk'
START_IMAGE_LINK = 'https://telegra.ph/file/82e3f9434e48d348fa223.jpg'
DOWNLOAD_DIRECTORY = 'downloads'  # Directory to save downloads
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Bot Initialization ---
bot = telebot.TeleBot(TOKEN, parse_mode=None)
start_time = time.time()  # Track bot start time

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
    uptime = current_time - start_time
    uptime_str = time.strftime("%jd %Hh %Mm %Ss", time.gmtime(uptime))
    return uptime_str

def search_youtube(query):
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&part=snippet&type=video&q={query}"
        response = requests.get(url)
        data = response.json()
        if data['items']:  # Check if search results exist
            video_id = data['items'][0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"
        else:
            return None
    except Exception as e:
        logger.error(f"Error searching for YouTube video: {e}")
        return None


def send_animated_message(chat_id, message_id, task, dots=['.', '..', '...']):
    dot_index = 0
    while not bot.is_message_deleted(chat_id, message_id):  # Check if message is deleted
        try:
            bot.edit_message_text(f"{task}{''.join(dots[dot_index])}", chat_id, message_id)
            dot_index = (dot_index + 1) % len(dots)
            time.sleep(0.5)
        except telebot.apihelper.ApiException as e:
            logger.error(f"Error sending animated message: {e}")
            break


# --- Progress Bar Functions ---

def on_download_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percent = int(100.0 * bytes_downloaded / total_size)
    update_progress_message(stream.message, f"Downloading... {percent}%")

def update_progress_message(message, text):
    try:
        bot.edit_message_text(text, message.chat.id, message.message_id)
    except telebot.apihelper.ApiException:
        pass 

# --- Error Handlers ---

def handle_download_error(message, error_type, details=""):
    error_message = f"❌ An error occurred while {error_type}. Please try again later."
    if details:
        error_message += f"\nDetails: {details}"
    bot.reply_to(message, error_message)
    logger.error(error_message)


# --- Message Handlers ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_photo(message.chat.id, START_IMAGE_LINK, caption=START_MENU_TEXT)


@bot.message_handler(commands=['ping'])
def ping_command(message):
    start_time_ping = time.monotonic()
    response = bot.reply_to(message, "Pinging...")
    end_time_ping = time.monotonic()
    latency = end_time_ping - start_time_ping
    bot.edit_message_text(
        f"Pong! 🏓\nLatency: {latency:.2f} seconds\nUptime: {get_uptime()}",
        message.chat.id,
        response.message_id
    )


@bot.message_handler(commands=['search'])
def search(message):
    try:
        query = message.text.strip().split(' ', 1)[1]
        search_results = search_youtube(query)
        if search_results:
            bot.reply_to(message, search_results)
        else:
            bot.reply_to(message, "No results found.")
    except IndexError:  # Handle invalid command format
        bot.reply_to(message, "Invalid command. Please use /search <query>")
    except Exception as e:  # Catch other errors
        handle_download_error(message, "searching", str(e))



@bot.message_handler(commands=['audio', 'video'])
def handle_download(message):
    command = message.text.split()[0]
    is_audio = command == '/audio'
    
    try:
        youtube_link = message.text.strip().split(' ', 1)[1]  
        yt = YouTube(youtube_link, on_progress_callback=on_download_progress)  

        # Choose stream based on format
        stream = (
            yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if is_audio
            else yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        )

        if not stream:
            bot.reply_to(message, "❌ No suitable stream found.")
            return

        # Start download animation
        msg = bot.send_message(message.chat.id, "Downloading...")
        stream.message = msg  # Attach message to stream for progress updates

        file_path = stream.download(output_path=DOWNLOAD_DIRECTORY)
        file_name = os.path.basename(file_path)

        if not is_audio and os.path.getsize(file_path) > MAX_VIDEO_SIZE:
            # Send video as file if it's too large
            with open(file_path, 'rb') as file:
                bot.edit_message_text(f"Uploading {file_name}...", message.chat.id, msg.message_id)
                bot.send_chat_action(message.chat.id, 'upload_document')  
                bot.send_document(message.chat.id, file) 
        else:
            # Send audio or smaller video as media
            with open(file_path, 'rb') as file:
                bot.edit_message_text(f"Uploading {file_name}...", message.chat.id, msg.message_id)
                bot.send_chat_action(message.chat.id, 'upload_video' if not is_audio else 'upload_audio')
                if is_audio:
                    bot.send_audio(message.chat.id, file, caption=yt.title)
                else:
                    bot.send_video(message.chat.id, file) 

        os.remove(file_path)
        bot.delete_message(message.chat.id, msg.message_id)  # Delete progress message
    except (IndexError, exceptions.RegexMatchError):
        bot.reply_to(message, f"Invalid command. Use: {command} <YouTube link>")
    except Exception as e:
        handle_download_error(message, "downloading", str(e))


# --- Main ---
if __name__ == '__main__':
    try:
        # Create download directory if it doesn't exist
        os.makedirs(DOWNLOAD_
