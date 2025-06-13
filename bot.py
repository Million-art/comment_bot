from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask, request
import os
from dotenv import load_dotenv
import asyncio
import logging

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
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://comment-bot-6n4i.onrender.com")
PORT = int(os.getenv("PORT", "10000"))

# Track muted users
muted_users = set()

# Create Flask app
app = Flask(__name__)

# Create Telegram bot application
telegram_app = None
webhook_setup_done = False

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all messages for debugging and comment detection."""
    
    # Log all incoming messages for debugging
    if update.message:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
        chat_type = update.effective_chat.type if update.effective_chat else "Unknown"
        username = update.effective_user.username if update.effective_user else "No username"
        first_name = update.effective_user.first_name if update.effective_user else "Unknown"
        is_bot = update.effective_user.is_bot if update.effective_user else False
        
        logger.info(f"📨 Message received: User {first_name} (@{username}, ID: {user_id}) in chat {chat_id} (type: {chat_type})")
        
        # Check if it's a reply
        if update.message.reply_to_message:
            logger.info(f"🔄 REPLY detected from {first_name} (@{username}, ID: {user_id})")
        else:
            logger.info(f"💭 Regular message (not a reply) from {first_name}")
        
        # Check if user is a bot
        if is_bot:
            logger.info(f"🤖 Message from bot, ignoring")
            return
        
        # Check chat type
        if chat_type not in ['group', 'supergroup']:
            logger.info(f"📱 Message from {chat_type}, not a group - ignoring")
            return
        
        # Only process replies in groups
        if not update.message.reply_to_message:
            logger.info(f"💬 Not a reply message, ignoring")
            return
        
        # This is a reply in a group from a non-bot user
        user_key = (user_id, chat_id)
        
        logger.info(f"✅ Valid comment detected from user {first_name} (@{username}, ID: {user_id}) in chat {chat_id}")
        
        # Skip if already muted
        if user_key in muted_users:
            logger.info(f"⚠️ User {user_id} already muted in chat {chat_id}, skipping")
            return
        
        try:
            # Mute user permanently
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            
            # Track muted user
            muted_users.add(user_key)
            
            logger.info(f"🔇 Successfully muted user {first_name} (@{username}, ID: {user_id}) in chat {chat_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to mute user {user_id} in chat {chat_id}: {e}")
    else:
        logger.info(f"📭 Update received but no message found")

async def setup_webhook():
    """Set webhook URL with Telegram."""
    global telegram_app, webhook_setup_done
    
    if webhook_setup_done:
        return
    
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    
    # Use ALL filter to catch all messages for debugging
    telegram_app.add_handler(MessageHandler(filters.ALL, handle_all_messages))
    
    await telegram_app.initialize()
    
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await telegram_app.bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook set to: {webhook_url}")
    webhook_setup_done = True

def ensure_bot_initialized():
    """Ensure bot is initialized before processing requests."""
    global telegram_app, webhook_setup_done
    
    if not webhook_setup_done and BOT_TOKEN:
        try:
            asyncio.run(setup_webhook())
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests."""
    try:
        # Ensure bot is initialized
        ensure_bot_initialized()
        
        if telegram_app is None:
            logger.error("Bot not initialized")
            return "Bot not initialized", 500
        
        # Get update from request
        update_data = request.get_json()
        logger.info(f"🔗 Webhook received update: {update_data}")
        
        update = Update.de_json(update_data, telegram_app.bot)
        
        # Process update
        asyncio.run(telegram_app.process_update(update))
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return "Error", 500

@app.route('/health')
def health():
    """Health check endpoint."""
    return "Bot is running", 200

@app.route('/')
def home():
    """Home page."""
    return "Telegram Comment Ban Bot is running!", 200

# Initialize webhook when module is imported (for Gunicorn)
if BOT_TOKEN:
    ensure_bot_initialized()

if __name__ == "__main__":
    # For development only
    app.run(host="0.0.0.0", port=PORT, debug=False) 