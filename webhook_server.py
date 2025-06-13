from flask import Flask, request
from telegram import Update
import asyncio
import json
from bot import create_app

# Create Flask app
flask_app = Flask(__name__)

# Create Telegram bot application
telegram_app = create_app()

@flask_app.route('/webhook', methods=['POST'])
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

@flask_app.route('/health')
def health():
    """Health check endpoint."""
    return "Bot is running", 200

if __name__ == "__main__":
    print("Starting webhook server...")
    flask_app.run(host="0.0.0.0", port=8443, debug=False) 