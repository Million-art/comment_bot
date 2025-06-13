from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://domain.com")

# Track muted users
muted_users = set()

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
    app = Application.builder().token(BOT_TOKEN).build()
    await app.initialize()
    
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await app.bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")
    print("Now deploy this bot to your server and handle POST requests to /webhook")
    
    await app.shutdown()

def create_app():
    """Create the application for deployment."""
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.REPLY, handle_comment))
    return app

if __name__ == "__main__":
    print("Setting up webhook...")
    asyncio.run(setup_webhook()) 