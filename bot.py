from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask, request
import os
from dotenv import load_dotenv
import asyncio
import logging
import json
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8443"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"

if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN provided in environment variables")

# Initialize Flask
app = Flask(__name__)

# Initialize Telegram bot
application = Application.builder().token(BOT_TOKEN).build()

# Track muted users
muted_users = set()

def load_muted_users():
    global muted_users
    try:
        if os.path.exists("muted_users.json"):
            with open("muted_users.json", "r") as f:
                muted_users = set(tuple(item) for item in json.load(f))
                logger.info(f"Loaded {len(muted_users)} muted users from storage")
    except Exception as e:
        logger.error(f"Failed to load muted users: {e}")

def save_muted_users():
    try:
        with open("muted_users.json", "w") as f:
            json.dump(list(muted_users), f)
            logger.info(f"Saved {len(muted_users)} muted users to storage")
    except Exception as e:
        logger.error(f"Failed to save muted users: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received update: {update}")
    try:
        user = update.effective_user
        chat = update.effective_chat
        
        if not user or not chat:
            logger.warning("No user or chat found in update")
            return
        
        # Skip if not in a group
        if chat.type not in ["group", "supergroup"]:
            return
        
        # Skip if user is admin
        try:
            member = await chat.get_member(user.id)
            if member.status in ["administrator", "creator"]:
                logger.debug(f"Skipping admin user {user.id} in chat {chat.id}")
                return
        except Exception as e:
            logger.error(f"Error checking admin status for user {user.id} in chat {chat.id}: {e}")
            return
        
        # Skip if already muted
        user_key = (user.id, chat.id)
        if user_key in muted_users:
            logger.debug(f"User {user.id} already muted in chat {chat.id}")
            return
        
        # Mute the user
        try:
            await chat.restrict_member(
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_audios=False,
                    can_send_documents=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_video_notes=False,
                    can_send_voice_notes=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
            )
            muted_users.add(user_key)
            save_muted_users()
            logger.info(f"Successfully muted user {user.id} in chat {chat.id}")
        except Exception as e:
            logger.error(f"Error muting user {user.id} in chat {chat.id}: {e}")
            
    except Exception as e:
        logger.error(f"Unexpected error in mute_user handler: {e}")

# Add handler for all message types
application.add_handler(MessageHandler(
    filters.ChatType.GROUPS & ~filters.COMMAND,
    mute_user
))

# Add a fallback handler to log any missed messages
def log_unhandled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Unhandled update: {update}")
application.add_handler(MessageHandler(filters.ALL, log_unhandled))

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(), application.bot)
            await application.process_update(update)
            return "ok", 200
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            return "error", 500
    return "Method not allowed", 405

@app.route('/test-async')
async def test_async():
    """Test async functionality."""
    if request.args.get("token") != ADMIN_TOKEN:
        return {"error": "Unauthorized"}, 403
    
    try:
        if application and application.bot:
            me = await application.bot.get_me()
            return {
                "status": "success",
                "bot_username": me.username,
                "bot_id": me.id,
                "webhook_enabled": USE_WEBHOOK
            }, 200
        else:
            return {"error": "Bot not initialized"}, 500
    except Exception as e:
        logger.error(f"Test async endpoint error: {e}")
        return {"error": f"Test failed: {str(e)}"}, 500

async def setup_webhook():
    """Set up webhook if enabled."""
    if USE_WEBHOOK and WEBHOOK_URL:
        try:
            await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
            logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            raise

async def remove_webhook():
    """Remove webhook if using polling."""
    if not USE_WEBHOOK:
        try:
            await application.bot.delete_webhook()
            logger.info("Webhook removed, using polling")
        except Exception as e:
            logger.error(f"Failed to remove webhook: {e}")
            raise

def run_webhook():
    """Run the bot with webhook."""
    load_muted_users()
    
    # Set up webhook
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(setup_webhook())
        logger.info(f"Starting bot with webhook on port {PORT}")
        app.run(host="0.0.0.0", port=PORT)
    finally:
        loop.close()

def run_polling():
    """Run the bot with polling."""
    load_muted_users()
    
    # Remove webhook and start polling
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(remove_webhook())
        logger.info("Starting bot with polling")
        application.run_polling()
    finally:
        loop.close()

def run():
    """Run the bot in the appropriate mode."""
    try:
        if USE_WEBHOOK:
            run_webhook()
        else:
            run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")
        raise

if __name__ == "__main__":
    run()