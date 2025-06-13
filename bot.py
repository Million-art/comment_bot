from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask, request
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://comment-bot-6n4i.onrender.com")
PORT = int(os.getenv("PORT", "10000"))  # Render uses PORT env variable

# Track muted users
muted_users = set()

# Create Flask app
app = Flask(__name__)

# Create Telegram bot application
telegram_app = None

async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mute users who comment (reply to messages)."""
    
    # Only process replies in groups
    if (not update.message or 
        not update.message.reply_to_message or 
        update.effective_chat.type not in ['group', 'supergroup'] or
        update.effective_user.is_bot):
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    user_key = (user_id, chat_id)
    
    # Skip if already muted
    if user_key in muted_users:
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
        
        # Send notification
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔇 {update.effective_user.mention_html()} muted for commenting.",
            parse_mode="HTML"
        )
        
    except Exception:
        pass

async def setup_webhook():
    """Set webhook URL with Telegram."""
    global telegram_app
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    telegram_app.add_handler(MessageHandler(filters.REPLY, handle_comment))
    
    await telegram_app.initialize()
    
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await telegram_app.bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests."""
    try:
        # Get update from request
        update_data = request.get_json()
        update = Update.de_json(update_data, telegram_app.bot)
        
        # Process update
        asyncio.run(telegram_app.process_update(update))
        
        return "OK", 200
    except Exception as e:
        print(f"Error processing update: {e}")
        return "Error", 500

@app.route('/health')
def health():
    """Health check endpoint."""
    return "Bot is running", 200

@app.route('/')
def home():
    """Home page."""
    return "Telegram Comment Ban Bot is running!", 200

if __name__ == "__main__":
    # Set up webhook first
    asyncio.run(setup_webhook())
    
    # Start Flask server
    print(f"Starting server on port {PORT}...")
    app.run(host="0.0.0.0", port=PORT, debug=False) 