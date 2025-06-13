# Telegram Comment Ban Bot

A focused Telegram bot that automatically and permanently mutes users who comment (reply to messages) in group chats.

## Features

- **Automatic Detection**: Monitors all reply messages (comments) in groups
- **Permanent Muting**: Restricts users permanently after their first comment
- **Clean Operation**: Shows a brief notification (comments are preserved)
- **Group Focus**: Only works in groups and supergroups
- **Dual Mode**: Supports both polling and webhook modes
- **Admin Permissions**: Requires proper bot admin permissions

## How It Works

1. Bot monitors all messages in the group
2. When someone replies to a message (comments), the bot:
   - Permanently mutes the user (removes all messaging permissions)
   - Shows a notification for 5 seconds, then deletes it
   - Logs the action
   - **Preserves the original comment**

## Setup

1. **Create a Bot**:
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Get your bot token

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Bot**:
   Create a `.env` file with your preferred mode:

   ### **Polling Mode (Default - Recommended for Development)**:
   ```env
   BOT_TOKEN=your_bot_token_here
   USE_WEBHOOK=false
   ```

   ### **Webhook Mode (Recommended for Production)**:
   ```env
   BOT_TOKEN=your_bot_token_here
   USE_WEBHOOK=true
   WEBHOOK_URL=https://yourdomain.com
   WEBHOOK_PORT=8443
   WEBHOOK_LISTEN=0.0.0.0
   WEBHOOK_PATH=/webhook/your_bot_token_here
   
   # Optional SSL certificates (for HTTPS)
   CERT_FILE=path/to/cert.pem
   KEY_FILE=path/to/private.key
   ```

4. **Add Bot to Group**:
   - Add your bot to the target group
   - Make it an admin with these permissions:
     - ✅ Restrict members
     - ❌ Other permissions (not needed)

5. **Run the Bot**:
   ```bash
   python bot.py
   ```

## Configuration Options

### **Environment Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | *required* | Your Telegram bot token |
| `USE_WEBHOOK` | `false` | Enable webhook mode (`true`/`false`) |
| `WEBHOOK_URL` | - | Your domain URL (required for webhook) |
| `WEBHOOK_PORT` | `8443` | Port for webhook server |
| `WEBHOOK_LISTEN` | `0.0.0.0` | Interface to listen on |
| `WEBHOOK_PATH` | `/webhook/{token}` | Webhook endpoint path |
| `CERT_FILE` | - | SSL certificate file (optional) |
| `KEY_FILE` | - | SSL private key file (optional) |

## Polling vs Webhook

### **Polling Mode** (Default):
- ✅ **Simple setup** - no server configuration needed
- ✅ **Works behind NAT/firewalls**
- ✅ **Good for development and testing**
- ❌ Less efficient for high-traffic bots
- ❌ Bot polls Telegram servers continuously

### **Webhook Mode**:
- ✅ **More efficient** - Telegram pushes updates to your server
- ✅ **Better for production** - lower latency and resource usage
- ✅ **Scalable** for high-traffic scenarios
- ❌ **Requires public HTTPS server**
- ❌ More complex setup (domain, SSL certificates)

## Webhook Setup Guide

For webhook mode, you need:

1. **Public Domain**: A domain pointing to your server
2. **HTTPS**: SSL certificate (Let's Encrypt recommended)
3. **Open Port**: Port 8443 (or custom) accessible from internet
4. **Reverse Proxy** (optional): Nginx/Apache for SSL termination

### **Example Nginx Configuration**:
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/private.key;
    
    location /webhook/ {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Bot Permissions Required

The bot must be an admin with:
- **Restrict members**: To mute users

## Technical Details

- **Framework**: python-telegram-bot 21.0.1
- **Python**: Compatible with Python 3.8+
- **Logging**: Detailed logs stored in `logs/` directory
- **Memory**: Tracks muted users in memory (resets on restart)

## Troubleshooting

1. **Bot not responding**: Check if bot token is correct
2. **Can't mute users**: Ensure bot has "Restrict members" permission
3. **Webhook not working**: Check domain, SSL, and port accessibility
4. **Bot mutes admins**: Bot will attempt to mute anyone who comments

## Logs

Check `logs/bot_*.log` files for detailed operation logs including:
- User muting events
- Webhook/polling status
- Permission errors
- Bot startup/shutdown events 