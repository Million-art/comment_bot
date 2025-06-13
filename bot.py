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
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://comment-bot-6n4i.onrender.com")
PORT = int(os.getenv("PORT", "10000"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "your-secret-admin-token")

# Persistent storage files
MUTED_USERS_FILE = "muted_users.json"
ADMIN_CACHE_FILE = "admin_cache.json"

# Track muted users and admin cache
muted_users = set()
admin_cache = {}  # {(user_id, chat_id): {"is_admin": bool, "expires": timestamp}}

def load_persistent_data():
    """Load muted users and admin cache from files."""
    global muted_users, admin_cache
    
    # Load muted users
    try:
        if os.path.exists(MUTED_USERS_FILE):
            with open(MUTED_USERS_FILE, 'r') as f:
                data = json.load(f)
                muted_users = set(tuple(item) for item in data)
                logger.info(f"📂 Loaded {len(muted_users)} muted users from storage")
    except Exception as e:
        logger.error(f"❌ Failed to load muted users: {e}")
        muted_users = set()
    
    # Load admin cache
    try:
        if os.path.exists(ADMIN_CACHE_FILE):
            with open(ADMIN_CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Convert string keys back to tuples and filter expired entries
                current_time = datetime.now().timestamp()
                admin_cache = {}
                for key_str, value in data.items():
                    if value["expires"] > current_time:
                        key = tuple(map(int, key_str.strip("()").split(", ")))
                        admin_cache[key] = value
                logger.info(f"📂 Loaded {len(admin_cache)} admin cache entries")
    except Exception as e:
        logger.error(f"❌ Failed to load admin cache: {e}")
        admin_cache = {}

def save_muted_users():
    """Save muted users to file."""
    try:
        with open(MUTED_USERS_FILE, 'w') as f:
            json.dump(list(muted_users), f)
        logger.debug(f"💾 Saved {len(muted_users)} muted users to storage")
    except Exception as e:
        logger.error(f"❌ Failed to save muted users: {e}")

def save_admin_cache():
    """Save admin cache to file."""
    try:
        # Convert tuple keys to strings for JSON serialization
        data = {str(key): value for key, value in admin_cache.items()}
        with open(ADMIN_CACHE_FILE, 'w') as f:
            json.dump(data, f)
        logger.debug(f"💾 Saved {len(admin_cache)} admin cache entries")
    except Exception as e:
        logger.error(f"❌ Failed to save admin cache: {e}")

async def is_user_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> bool:
    """Check if user is admin with caching (24 hour cache)."""
    cache_key = (user_id, chat_id)
    current_time = datetime.now().timestamp()
    
    # Check cache first
    if cache_key in admin_cache:
        cache_entry = admin_cache[cache_key]
        if cache_entry["expires"] > current_time:
            logger.debug(f"🗂️ Admin status from cache for user {user_id}: {cache_entry['is_admin']}")
            return cache_entry["is_admin"]
    
    # Cache miss or expired, check with Telegram
    try:
        chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        is_admin = chat_member.status in ['administrator', 'creator']
        
        # Cache for 24 hours
        expires = current_time + (24 * 60 * 60)
        admin_cache[cache_key] = {"is_admin": is_admin, "expires": expires}
        save_admin_cache()
        
        logger.debug(f"🔍 Checked admin status for user {user_id}: {is_admin}")
        return is_admin
        
    except Exception as e:
        logger.warning(f"⚠️ Could not check admin status for user {user_id}: {e}")
        return False  # Default to non-admin if check fails

# Create Flask app
app = Flask(__name__)

# Create Telegram bot application
telegram_app = None
webhook_setup_done = False

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        user = update.effective_user
        chat = update.effective_chat
        user_id = user.id if user else "Unknown"
        chat_id = chat.id if chat else "Unknown"
        username = user.username or "No username"
        first_name = user.first_name or "Unknown"
        is_bot = user.is_bot if user else False
        chat_type = chat.type

        if is_bot:
            logger.debug(f"🤖 Bot message, skipping")
            return

        if chat_type not in ['group', 'supergroup']:
            logger.debug(f"📱 Not a group chat, skipping")
            return

        # Check if user is admin (with caching)
        if await is_user_admin(context, user_id, chat_id):
            logger.debug(f"👑 User {first_name} (@{username}) is admin, skipping")
            return

        user_key = (user_id, chat_id)

        if user_key in muted_users:
            logger.debug(f"⚠️ User {user_id} already muted, skipping")
            return

        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            muted_users.add(user_key)
            save_muted_users()  # Persist immediately
            logger.info(f"🔇 Muted user {first_name} (@{username}) ID: {user_id} in chat {chat_id}")
        except Exception as e:
            logger.error(f"❌ Error muting user {user_id}: {e}")

async def setup_webhook():
    """Set webhook URL with Telegram."""
    global telegram_app, webhook_setup_done
    
    if webhook_setup_done:
        logger.debug("🔄 Webhook already setup, skipping")
        return
    
    logger.info("🚀 Starting webhook setup...")
    
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    
    # Use TEXT filter to avoid service messages, exclude commands
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    
    logger.info("📱 Initializing Telegram application...")
    await telegram_app.initialize()
    
    webhook_url = f"{WEBHOOK_URL}/webhook"
    logger.info(f"🔗 Setting webhook URL: {webhook_url}")
    
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook successfully set to: {webhook_url}")
        
        # Get webhook info to verify
        webhook_info = await telegram_app.bot.get_webhook_info()
        logger.info(f"📊 Webhook info - URL: {webhook_info.url}, Pending updates: {webhook_info.pending_update_count}")
        if webhook_info.last_error_message:
            logger.warning(f"⚠️ Last webhook error: {webhook_info.last_error_message}")
        
        webhook_setup_done = True
        
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
        raise

def ensure_bot_initialized():
    """Ensure bot is initialized before processing requests."""
    global telegram_app, webhook_setup_done
    
    if webhook_setup_done:
        logger.debug("✅ Bot already initialized")
        return
        
    if not BOT_TOKEN:
        logger.error("❌ No BOT_TOKEN provided")
        return
        
    logger.info("🔧 Bot not initialized, starting setup...")
    try:
        # Load persistent data first
        load_persistent_data()
        
        # Setup webhook using new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(setup_webhook())
            logger.info("✅ Bot initialization completed successfully")
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"❌ Failed to setup webhook: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests."""
    try:
        if telegram_app is None:
            logger.error("Bot not initialized")
            return "Bot not initialized", 500
        
        # Get update from request
        update_data = request.get_json()
        logger.debug(f"🔗 Webhook received update")
        
        update = Update.de_json(update_data, telegram_app.bot)
        
        # Use new event loop to avoid "Event loop is closed" error
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(telegram_app.process_update(update))
        finally:
            loop.close()
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return "Error", 500

@app.route('/webhook-info')
def webhook_info():
    """Get webhook info from Telegram."""
    # Security check
    if request.args.get("token") != ADMIN_TOKEN:
        return {"error": "Unauthorized"}, 403
        
    try:
        if telegram_app and telegram_app.bot:
            # Use new event loop to avoid "Event loop is closed" error
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                webhook_info = loop.run_until_complete(telegram_app.bot.get_webhook_info())
                return {
                    "url": webhook_info.url,
                    "has_custom_certificate": webhook_info.has_custom_certificate,
                    "pending_update_count": webhook_info.pending_update_count,
                    "last_error_date": webhook_info.last_error_date,
                    "last_error_message": webhook_info.last_error_message,
                    "max_connections": webhook_info.max_connections,
                    "allowed_updates": webhook_info.allowed_updates
                }, 200
            finally:
                loop.close()
        else:
            return {"error": "Bot not initialized"}, 500
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/reset-webhook')
def reset_webhook():
    """Reset webhook and clear pending updates."""
    # Security check
    if request.args.get("token") != ADMIN_TOKEN:
        return {"error": "Unauthorized"}, 403
        
    try:
        if telegram_app and telegram_app.bot:
            # Use new event loop to avoid "Event loop is closed" error
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Delete webhook first to clear pending updates
                loop.run_until_complete(telegram_app.bot.delete_webhook(drop_pending_updates=True))
                logger.info("🗑️ Deleted webhook and cleared pending updates")
                
                # Set webhook again
                webhook_url = f"{WEBHOOK_URL}/webhook"
                loop.run_until_complete(telegram_app.bot.set_webhook(url=webhook_url))
                logger.info(f"✅ Webhook reset to: {webhook_url}")
                
                # Get new webhook info
                webhook_info = loop.run_until_complete(telegram_app.bot.get_webhook_info())
                return {
                    "message": "Webhook reset successfully",
                    "url": webhook_info.url,
                    "pending_update_count": webhook_info.pending_update_count,
                    "last_error_message": webhook_info.last_error_message
                }, 200
            finally:
                loop.close()
        else:
            return {"error": "Bot not initialized"}, 500
    except Exception as e:
        logger.error(f"❌ Failed to reset webhook: {e}")
        return {"error": str(e)}, 500

@app.route('/stats')
def stats():
    """Get bot statistics."""
    # Security check
    if request.args.get("token") != ADMIN_TOKEN:
        return {"error": "Unauthorized"}, 403
        
    return {
        "muted_users_count": len(muted_users),
        "admin_cache_count": len(admin_cache),
        "webhook_setup": webhook_setup_done
    }, 200

@app.route('/health')
def health():
    """Health check endpoint."""
    return "Bot is running", 200

@app.route('/test-async')
def test_async():
    """Test async functionality."""
    # Security check
    if request.args.get("token") != ADMIN_TOKEN:
        return {"error": "Unauthorized"}, 403
    
    try:
        if telegram_app and telegram_app.bot:
            # Test async call
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                me = loop.run_until_complete(telegram_app.bot.get_me())
                return {
                    "status": "success",
                    "bot_username": me.username,
                    "bot_id": me.id
                }, 200
            finally:
                loop.close()
        else:
            return {"error": "Bot not initialized"}, 500
    except Exception as e:
        return {"error": f"Test failed: {str(e)}"}, 500

@app.route('/')
def home():
    """Home page."""
    return "Telegram Comment Ban Bot is running!", 200

# Initialize webhook when module is imported (for Gunicorn)
if BOT_TOKEN:
    logger.info("🚀 Starting bot initialization on module import...")
    ensure_bot_initialized()
    logger.info("📡 Bot module loaded and ready")
else:
    logger.error("❌ BOT_TOKEN not found in environment variables")

if __name__ == "__main__":
    # For development only
    app.run(host="0.0.0.0", port=PORT, debug=False) 