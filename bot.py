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
# ... (Your logging configuration remains the same)

# --- Bot Initialization ---
# ... (Your bot initialization remains the same)

# --- Start Menu Text ---
# ... (Your START_MENU_TEXT remains the same)

# --- Helper Functions ---
# ... (get_uptime, search_youtube, send_animated_message remain the same)

# --- Progress Bar Functions ---
# ... (on_download_progress, on_upload_progress, update_progress_message remain the same)

# --- Error Handlers ---
# ... (handle_download_error remains the same)

# --- Message Handlers ---
# ... (send_welcome, ping_command, search handlers remain the same)

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
        os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)  # Corrected line

        logger.info("Bot is starting...")
        bot.infinity_polling(skip_pending=True, timeout=10)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 409:
            logger.error("Conflict: Another instance of the bot is running. Please stop it before starting this one.")
        else:
            logger.error(f"Telegram API Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

