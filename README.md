# Telegram Comment Ban Bot

A production-ready Telegram bot that automatically mutes users who send messages in groups.

## Features

- 🔇 **Auto-mute**: Mutes any user who sends a message in groups
- 👑 **Admin protection**: Never mutes administrators or group creators
- 💾 **Persistent storage**: Remembers muted users across restarts
- ⚡ **Admin caching**: Efficient admin status checking with 24-hour cache
- 🔒 **Secure endpoints**: Protected admin endpoints with token authentication
- 📊 **Statistics**: Track muted users and cache performance
- 🚀 **Production ready**: Optimized logging and error handling

## Environment Variables

Create a `.env` file with:

```env
BOT_TOKEN=your_telegram_bot_token
WEBHOOK_URL=https://your-app.onrender.com
PORT=10000
ADMIN_TOKEN=your-secret-admin-token-change-this
```

## Deployment

1. Deploy to Render using Gunicorn
2. Set environment variables in Render dashboard
3. Reset webhook: `GET /reset-webhook?token=your-admin-token`

## Admin Endpoints

All admin endpoints require `?token=your-admin-token`:

- `/webhook-info?token=xxx` - View webhook status
- `/reset-webhook?token=xxx` - Reset webhook and clear pending updates
- `/stats?token=xxx` - View bot statistics

## Files Created

- `muted_users.json` - Persistent storage of muted users
- `admin_cache.json` - Cache of admin status checks

## Security Features

- Admin endpoints protected with token authentication
- Admin status cached to reduce API calls
- Only processes text messages (ignores service messages)
- Excludes bot commands from processing

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